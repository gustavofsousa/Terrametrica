"""Ingestão de Unidades de Conservação (UC) como camada de restrição — Fatia 5.

Fonte verificada por acesso real (2026-09-04, ver `docs/research/fontes-de-dados-rj.md` §3): a
camada consolidada "Unidades de Conservação ERJ" do FeatureServer ArcGIS do MPRJ (deriva do CNUC
federal + UCs estaduais/municipais), **455 feições, 0 inválidas/vazias, EPSG:4326**, cobrindo as
três esferas (Federal/Estadual/Municipal) dentro do RJ. Diferente de SIGEF/CAR, é download público
sem login/captcha — mas, como as demais ingestões, esta lê de um arquivo local já baixado (AD-004:
base própria; mantém a ingestão testável e offline). O download fica a cargo de quem orquestra.

Mapeia direto na tabela genérica `restricao` (mesma de APP/Reserva Legal): `tipo` =
`unidade_conservacao`, `nome` = nome da UC (`uc`), `categoria` = categoria SNUC (`REBIO`/`APA`/…).
Não há `grau_suscetibilidade` (isso é das camadas de suscetibilidade — inundação/deslizamento,
fatias futuras). Reprojeta de EPSG:4326 para o canônico EPSG:4674 (AD-008) antes de gravar.
"""

from datetime import date, datetime
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import psycopg

from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.tipos import RelatorioCamada
from terrametrica.ingestao.validacao_geometria import corrigir_geometria, para_multipolygon

CRS_CANONICO = "EPSG:4674"
FONTE_UC = "INEA/MPRJ — Unidades de Conservação ERJ (CNUC)"
LINK_OFICIAL_UC = (
    "https://geo.mprj.mp.br/portal/home/item.html?id=330049c4d719405fb2e750484beea97a"
)

_INSERIR_RESTRICAO = """
    INSERT INTO restricao (id, tipo, nome, categoria, geom, versao_base_id)
    VALUES (%(id)s, %(tipo)s, %(nome)s, %(categoria)s, ST_GeomFromText(%(wkt)s, 4674), %(versao)s)
"""

_INSERIR_PROVENIENCIA = """
    INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao, link_oficial)
    VALUES (%(camada)s, %(versao)s, %(fonte)s, %(data_extracao)s, %(link)s)
"""


def _data_extracao_de(caminho: Path) -> date:
    """Mesma heurística de `sigef.py`/`restricao_car.py`: o mtime do arquivo baixado aproxima a
    data real da extração do serviço melhor do que a data em que a ingestão rodou."""
    return datetime.fromtimestamp(caminho.stat().st_mtime).date()


def ingerir_uc(
    caminho: Path,
    versao: VersaoBase,
    conexao: psycopg.Connection,
    *,
    data_extracao: date | None = None,
) -> RelatorioCamada:
    """Lê o GeoJSON de UC (camada consolidada ERJ), reprojeta para EPSG:4674 e grava cada UC em
    `restricao` com `tipo='unidade_conservacao'`, mais a proveniência da camada."""
    feicoes = gpd.read_file(caminho)
    if feicoes.crs is None:
        raise ValueError(f"arquivo de UC sem CRS definido: {caminho}")
    feicoes = feicoes.to_crs(CRS_CANONICO)

    total_corrigidas = 0
    with conexao.cursor() as cursor:
        for indice, (_, linha) in enumerate(feicoes.iterrows()):
            geom_corrigida, foi_corrigida = corrigir_geometria(linha.geometry)
            geom_final = para_multipolygon(geom_corrigida)
            if foi_corrigida:
                total_corrigidas += 1

            cursor.execute(
                _INSERIR_RESTRICAO,
                {
                    "id": f"unidade_conservacao-{indice}",
                    "tipo": Camada.UNIDADE_CONSERVACAO.value,
                    "nome": str(linha["uc"]),
                    "categoria": str(linha["categoria"]),
                    "wkt": geom_final.wkt,
                    "versao": versao.id,
                },
            )

        cursor.execute(
            _INSERIR_PROVENIENCIA,
            {
                "camada": Camada.UNIDADE_CONSERVACAO.value,
                "versao": versao.id,
                "fonte": FONTE_UC,
                "data_extracao": data_extracao or _data_extracao_de(caminho),
                "link": LINK_OFICIAL_UC,
            },
        )

    return RelatorioCamada(
        camada=Camada.UNIDADE_CONSERVACAO.value,
        versao_base_id=versao.id,
        feicoes_gravadas=len(feicoes),
        feicoes_corrigidas=total_corrigidas,
    )
