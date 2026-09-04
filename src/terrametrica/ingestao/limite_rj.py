"""Ingestão do limite estadual do RJ — busca real via `geobr` (S3/GitHub releases do IBGE
espelhado pelo geobr, sem login — AD-004), valida/corrige geometria e reprojeta para o CRS
canônico (AD-008) antes de gravar em `limite_estado`.

Não comita: quem orquestra a pipeline decide o limite da transação (ver `publicar.py`, que
comita o swap e, transitivamente, todo staging feito na mesma transação, só quando a guarda de
90% passa — DOS-25/28).
"""

import geobr  # type: ignore[import-untyped]
import psycopg

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.tipos import RelatorioCamada
from terrametrica.ingestao.validacao_geometria import corrigir_geometria, para_multipolygon

CRS_CANONICO = "EPSG:4674"
UF_RJ = "RJ"
CODIGO_ESTADO_RJ = 33
CAMADA_LIMITE_ESTADO = "limite_estado"

# `geobr.read_state` exige `year` explícito (a API instalada difere do trecho de design.md, que
# chamava `read_state(code_state=33)` sem ano) — 2025 é o ano mais recente disponível na malha
# estadual do IBGE servida pelo geobr no momento desta implementação.
ANO_MALHA_ESTADUAL = 2025

_INSERIR_LIMITE = """
    INSERT INTO limite_estado (uf, geom, versao_base_id)
    VALUES (%(uf)s, ST_GeomFromText(%(wkt)s, 4674), %(versao)s)
"""


def ingerir_limite_rj(versao: VersaoBase, conexao: psycopg.Connection) -> RelatorioCamada:
    """Busca o polígono do RJ via geobr, corrige/reprojeta e grava em `limite_estado`."""
    try:
        malha = geobr.read_state(year=ANO_MALHA_ESTADUAL, code_state=CODIGO_ESTADO_RJ)
    except Exception as erro:  # geobr pode levantar erro de rede via requests ou via duckdb
        raise RuntimeError(
            "ingerir_limite_rj precisa de rede para buscar a malha do RJ via geobr — "
            f"falha de conectividade (dependência de rede, não um bug de código): {erro}"
        ) from erro

    malha = malha.to_crs(CRS_CANONICO)
    geom_bruta = malha.geometry.iloc[0]

    geom_corrigida, foi_corrigida = corrigir_geometria(geom_bruta)
    geom_final = para_multipolygon(geom_corrigida)

    with conexao.cursor() as cursor:
        cursor.execute(
            _INSERIR_LIMITE,
            {"uf": UF_RJ, "wkt": geom_final.wkt, "versao": versao.id},
        )

    return RelatorioCamada(
        camada=CAMADA_LIMITE_ESTADO,
        versao_base_id=versao.id,
        feicoes_gravadas=1,
        feicoes_corrigidas=1 if foi_corrigida else 0,
    )
