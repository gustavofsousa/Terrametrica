"""Ingestão do SIGEF a partir de um export local (shapefile) — sem download programático.

SIGEF/CAR não têm download automatizável (exigem login GOV.BR humano — ver Fase 0,
`docs/research/fontes-de-dados-rj.md`), então `ingerir_sigef` recebe um caminho de arquivo já
exportado, não busca da rede. Valida/corrige geometria, garante EPSG:4674 (AD-008) e grava cada
feição em `lote_rural.geom_sigef` (`geom_car` fica NULL nesta fatia — AD-003, dupla geometria
nunca "final"), carimbando `proveniencia`.

Não comita: mesma decisão de `limite_rj.py` — quem orquestra a pipeline decide o limite da
transação (ver `publicar.py`).
"""

from datetime import date, datetime
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import psycopg

from terrametrica.dominio.modelos import Camada, SituacaoCertificacao, VersaoBase
from terrametrica.ingestao.tipos import RelatorioCamada
from terrametrica.ingestao.validacao_geometria import corrigir_geometria, para_multipolygon

CRS_CANONICO = "EPSG:4674"
UF_RJ = "RJ"
FONTE_SIGEF = "SIGEF"
LINK_OFICIAL_SIGEF = "https://sigef.incra.gov.br/"

# Único valor bruto do campo `status` confirmado nos dados reais da Fase 0 (ver
# docs/research/fontes-de-dados-rj.md). Não há enumeração fechada documentada de todos os
# valores possíveis do SIGEF, então o mapeamento abaixo é deliberadamente conservador.
STATUS_BRUTO_CERTIFICADA = "CERTIFICADA"

_INSERIR_LOTE = """
    INSERT INTO lote_rural
        (id, uf, municipios, codigo_sigef, denominacao, situacao_certificacao,
         geom_sigef, geometria_corrigida, versao_base_id)
    VALUES (%(id)s, %(uf)s, %(municipios)s, %(codigo_sigef)s, %(denominacao)s,
            %(situacao)s, ST_GeomFromText(%(wkt)s, 4674), %(corrigida)s, %(versao)s)
"""

_INSERIR_PROVENIENCIA = """
    INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao, link_oficial)
    VALUES (%(camada)s, %(versao)s, %(fonte)s, %(data_extracao)s, %(link)s)
"""


def _mapear_situacao(status_bruto: str) -> str:
    """Mapeia o campo livre `status` do SIGEF para o vocabulário fechado do domínio
    (`SituacaoCertificacao`). Só `CERTIFICADA` mapeia para `certificado`; qualquer outro texto
    cai em `em_analise` — leitura conservadora na ausência de uma enumeração fechada
    documentada dos valores brutos do SIGEF.
    """
    if status_bruto.strip().upper() == STATUS_BRUTO_CERTIFICADA:
        return SituacaoCertificacao.CERTIFICADO.value
    return SituacaoCertificacao.EM_ANALISE.value


def _data_extracao_de(caminho: Path) -> date:
    """Data de extração inferida do mtime do arquivo exportado — aproxima o momento real do
    export GOV.BR melhor do que a data em que a ingestão rodou (o mesmo arquivo pode ser
    reingerido depois). Sobrescrita explícita via `data_extracao` quando o operador souber a
    data real do export.
    """
    return datetime.fromtimestamp(caminho.stat().st_mtime).date()


def ingerir_sigef(
    caminho: Path,
    versao: VersaoBase,
    conexao: psycopg.Connection,
    *,
    data_extracao: date | None = None,
) -> RelatorioCamada:
    """Lê o shapefile SIGEF, valida/corrige geometria e grava cada feição em `lote_rural`."""
    feicoes = gpd.read_file(caminho, engine="pyogrio")
    if feicoes.crs is None:
        raise ValueError(f"shapefile SIGEF sem CRS definido: {caminho}")
    feicoes = feicoes.to_crs(CRS_CANONICO)

    total_corrigidas = 0
    with conexao.cursor() as cursor:
        for _, linha in feicoes.iterrows():
            geom_corrigida, foi_corrigida = corrigir_geometria(linha.geometry)
            geom_final = para_multipolygon(geom_corrigida)
            if foi_corrigida:
                total_corrigidas += 1

            cursor.execute(
                _INSERIR_LOTE,
                {
                    "id": str(linha["codigo_imo"]),
                    "uf": UF_RJ,
                    "municipios": [str(linha["municipio_"])],
                    "codigo_sigef": str(linha["codigo_imo"]),
                    "denominacao": linha.get("nome_area") or None,
                    "situacao": _mapear_situacao(str(linha["status"])),
                    "wkt": geom_final.wkt,
                    "corrigida": foi_corrigida,
                    "versao": versao.id,
                },
            )

        cursor.execute(
            _INSERIR_PROVENIENCIA,
            {
                "camada": Camada.LOTE_RURAL.value,
                "versao": versao.id,
                "fonte": FONTE_SIGEF,
                "data_extracao": data_extracao or _data_extracao_de(caminho),
                "link": LINK_OFICIAL_SIGEF,
            },
        )

    return RelatorioCamada(
        camada=Camada.LOTE_RURAL.value,
        versao_base_id=versao.id,
        feicoes_gravadas=len(feicoes),
        feicoes_corrigidas=total_corrigidas,
    )
