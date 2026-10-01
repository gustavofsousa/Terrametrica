"""Ingestão dos lotes urbanos de Niterói (SIGeo, AD-006) — F1.9.

Recebe o GeoJSON já baixado da camada `Lotes` do FeatureServer público do SIGeo (EPSG:31983,
82.375 feições em 2026-09-30) — mesma postura de `sigef.py`: a ingestão lê arquivo local, o
download fica fora do caminho de carga. Reprojeta para EPSG:4674 (AD-008), corrige geometria
inválida e grava em `lote_urbano`, carimbando a proveniência com a atribuição que a licença do
SIGeo exige.

Não comita: quem orquestra decide o limite da transação (ver `publicar.py`).
"""

from datetime import date, datetime
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import psycopg

from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.tipos import RelatorioCamada
from terrametrica.ingestao.validacao_geometria import corrigir_geometria, para_multipolygon

CRS_CANONICO = "EPSG:4674"
CODIGO_IBGE_NITEROI = "3303302"
PREFIXO_ID = "niteroi:"
# COMPAT: a licença do SIGeo libera redistribuição com atribuição obrigatória — o nome da fonte
# aparece em todo dossiê via proveniência (AD-005).
FONTE_SIGEO = "SIGeo Niterói (Prefeitura de Niterói)"
LINK_OFICIAL_SIGEO = (
    "https://sig.niteroi.rj.gov.br/server/rest/services/Hosted/"
    "NGP_SMF_SEREC_A_LOTES_PUBLICO/FeatureServer/30"
)
# O SIGeo usa "0" e vazio como "sem inscrição" — não são inscrições de verdade.
_INSCRICOES_VAZIAS = {"", "0"}

_INSERIR_LOTE = """
    INSERT INTO lote_urbano
        (id, municipio, inscricao_cadastral, logradouro, bairro, geom, geometria_corrigida,
         versao_base_id)
    VALUES (%(id)s, %(municipio)s, %(inscricao)s, %(logradouro)s, %(bairro)s,
            ST_GeomFromText(%(wkt)s, 4674), %(corrigida)s, %(versao)s)
"""

_INSERIR_PROVENIENCIA = """
    INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao, link_oficial)
    VALUES (%(camada)s, %(versao)s, %(fonte)s, %(data_extracao)s, %(link)s)
"""


def normalizar_inscricao(bruta: object) -> str | None:
    """Inscrição cadastral limpa, ou `None` quando o SIGeo não tem uma de verdade."""
    if bruta is None or (isinstance(bruta, float) and bruta != bruta):  # NaN do pandas
        return None
    texto = str(bruta).strip()
    return None if texto in _INSCRICOES_VAZIAS else texto


def _texto_ou_none(bruto: object) -> str | None:
    if bruto is None or (isinstance(bruto, float) and bruto != bruto):
        return None
    texto = str(bruto).strip()
    return texto or None


def _data_extracao_de(caminho: Path) -> date:
    """Mesma heurística das demais ingestões: mtime do arquivo baixado."""
    return datetime.fromtimestamp(caminho.stat().st_mtime).date()


def ingerir_lotes_niteroi(
    caminho: Path,
    versao: VersaoBase,
    conexao: psycopg.Connection,
    *,
    data_extracao: date | None = None,
) -> RelatorioCamada:
    """Lê o GeoJSON do SIGeo e grava cada lote com geometria em `lote_urbano`."""
    feicoes = gpd.read_file(caminho)
    if feicoes.crs is None:
        raise ValueError(f"GeoJSON do SIGeo sem CRS definido: {caminho}")
    sem_geometria = int(feicoes.geometry.isna().sum() + feicoes.geometry.is_empty.sum())
    feicoes = feicoes[feicoes.geometry.notna() & ~feicoes.geometry.is_empty]
    feicoes = feicoes.to_crs(CRS_CANONICO)

    total_corrigidas = 0
    with conexao.cursor() as cursor:
        for _, linha in feicoes.iterrows():
            geom_corrigida, foi_corrigida = corrigir_geometria(linha.geometry)
            if foi_corrigida:
                total_corrigidas += 1
            cursor.execute(
                _INSERIR_LOTE,
                {
                    "id": f"{PREFIXO_ID}{int(linha['objectid'])}",
                    "municipio": CODIGO_IBGE_NITEROI,
                    "inscricao": normalizar_inscricao(linha.get("tx_insct")),
                    "logradouro": _logradouro(linha.get("tx_logrado"), linha.get("tx_nroport")),
                    "bairro": _texto_ou_none(linha.get("tx_bairro")),
                    "wkt": para_multipolygon(geom_corrigida).wkt,
                    "corrigida": foi_corrigida,
                    "versao": versao.id,
                },
            )

        cursor.execute(
            _INSERIR_PROVENIENCIA,
            {
                "camada": Camada.LOTE_URBANO.value,
                "versao": versao.id,
                "fonte": FONTE_SIGEO,
                "data_extracao": data_extracao or _data_extracao_de(caminho),
                "link": LINK_OFICIAL_SIGEO,
            },
        )

    return RelatorioCamada(
        camada=Camada.LOTE_URBANO.value,
        versao_base_id=versao.id,
        feicoes_gravadas=len(feicoes),
        feicoes_corrigidas=total_corrigidas,
        feicoes_sem_geometria=sem_geometria,
    )


def _logradouro(logradouro: object, numero: object) -> str | None:
    """`"CARAMUJO,DO"` + `"12"` → `"CARAMUJO,DO, 12"`; número `0`/vazio é omitido."""
    nome = _texto_ou_none(logradouro)
    if nome is None:
        return None
    numero_texto = _texto_ou_none(numero)
    if numero_texto in (None, "0"):
        return nome
    return f"{nome}, {numero_texto}"
