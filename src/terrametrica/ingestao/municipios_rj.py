"""Ingestão da malha municipal do RJ — busca real via `geobr` (IBGE, sem login — AD-004).

A malha é camada versionada da base (AD-016): define o conjunto de municípios do RJ (92) que a
cobertura e o `municipio_em` usam. Resolução completa, no mesmo ano e CRS do `limite_estado`,
para que a união dos municípios coincida com o estado.

Não comita: quem orquestra decide o limite da transação (ver `publicar.py`).
"""

import hashlib
import json
from collections.abc import Callable
from datetime import date

import geobr  # type: ignore[import-untyped]
import geopandas as gpd  # type: ignore[import-untyped]
import psycopg
from shapely.geometry import mapping  # type: ignore[import-untyped]

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.tipos import RelatorioCamada
from terrametrica.ingestao.validacao_geometria import corrigir_geometria, para_multipolygon

CRS_CANONICO = "EPSG:4674"
CAMADA_MUNICIPIO = "municipio"
CODIGO_UF_RJ = "33"
TOTAL_MUNICIPIOS_RJ = 92
ANO_MALHA_MUNICIPAL = 2025
FONTE_MALHA = f"IBGE — Malha Municipal {ANO_MALHA_MUNICIPAL}"
LINK_OFICIAL_MALHA = (
    "https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/"
    "15774-malhas.html"
)

_APAGAR_MUNICIPIOS = "DELETE FROM municipio WHERE versao_base_id = %s"
_APAGAR_PROVENIENCIA = "DELETE FROM proveniencia WHERE camada = %s AND versao_base_id = %s"
_INSERIR_MUNICIPIO = """
    INSERT INTO municipio (codigo, nome, uf, geom, versao_base_id)
    VALUES (%(codigo)s, %(nome)s, %(uf)s, ST_GeomFromText(%(wkt)s, 4674), %(versao)s)
"""
_INSERIR_PROVENIENCIA = """
    INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao, link_oficial, sha256)
    VALUES (%(camada)s, %(versao)s, %(fonte)s, %(data_extracao)s, %(link)s, %(sha256)s)
"""


class MalhaIncompleta(Exception):
    """A malha baixada não tem exatamente os 92 municípios do RJ com geometria (MUN-04)."""


def _ler_geobr() -> gpd.GeoDataFrame:
    try:
        return geobr.read_municipality(
            year=ANO_MALHA_MUNICIPAL, code_muni=int(CODIGO_UF_RJ), simplified=False
        )
    except Exception as erro:  # geobr pode levantar erro de rede via requests ou via duckdb
        raise RuntimeError(
            "ingerir_municipios_rj precisa de rede para buscar a malha municipal via geobr — "
            f"falha de conectividade (dependência de rede, não um bug de código): {erro}"
        ) from erro


def _codigo(bruto: object) -> str:
    """Código IBGE de 7 dígitos; o geobr o entrega como float (`3300100.0`)."""
    return str(int(float(str(bruto))))


def sha256_canonico(malha: gpd.GeoDataFrame) -> str:
    """SHA-256 do GeoJSON canônico: feições ordenadas por código, chaves ordenadas (MUN-05)."""
    feicoes = sorted(
        (
            {
                "codigo": _codigo(linha["code_muni"]),
                "nome": str(linha["name_muni"]),
                "geometry": mapping(linha.geometry),
            }
            for _, linha in malha.iterrows()
        ),
        key=lambda feicao: feicao["codigo"],
    )
    canonico = json.dumps(feicoes, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _validar_malha(malha: gpd.GeoDataFrame) -> None:
    """Levanta `MalhaIncompleta` se a malha não tem exatamente os 92 municípios do RJ (MUN-04)."""
    codigos = [_codigo(c) for c in malha["code_muni"]]
    fora_do_rj = [c for c in codigos if not c.startswith(CODIGO_UF_RJ)]
    sem_geometria = int(malha.geometry.isna().sum() + malha.geometry.is_empty.sum())
    if (
        len(codigos) != TOTAL_MUNICIPIOS_RJ
        or len(set(codigos)) != TOTAL_MUNICIPIOS_RJ
        or fora_do_rj
        or sem_geometria
    ):
        raise MalhaIncompleta(
            f"malha municipal inválida: {len(codigos)} feições ({len(set(codigos))} códigos "
            f"distintos), esperado {TOTAL_MUNICIPIOS_RJ}; {len(fora_do_rj)} fora de "
            f"{CODIGO_UF_RJ}xxxxx; {sem_geometria} sem geometria"
        )


def ingerir_municipios_rj(
    versao: VersaoBase,
    conexao: psycopg.Connection,
    *,
    ler: Callable[[], gpd.GeoDataFrame] = _ler_geobr,
    data_extracao: date | None = None,
) -> RelatorioCamada:
    """Grava os 92 municípios do RJ na versão. Reingerir a mesma versão substitui as linhas."""
    malha = ler()
    _validar_malha(malha)
    malha = malha.to_crs(CRS_CANONICO)
    sha256 = sha256_canonico(malha)

    total_corrigidas = 0
    with conexao.cursor() as cursor:
        cursor.execute(_APAGAR_MUNICIPIOS, (versao.id,))
        cursor.execute(_APAGAR_PROVENIENCIA, (CAMADA_MUNICIPIO, versao.id))
        for _, linha in malha.iterrows():
            geom_corrigida, foi_corrigida = corrigir_geometria(linha.geometry)
            total_corrigidas += int(foi_corrigida)
            cursor.execute(
                _INSERIR_MUNICIPIO,
                {
                    "codigo": _codigo(linha["code_muni"]),
                    "nome": str(linha["name_muni"]),
                    "uf": CODIGO_UF_RJ,
                    "wkt": para_multipolygon(geom_corrigida).wkt,
                    "versao": versao.id,
                },
            )
        cursor.execute(
            _INSERIR_PROVENIENCIA,
            {
                "camada": CAMADA_MUNICIPIO,
                "versao": versao.id,
                "fonte": FONTE_MALHA,
                "data_extracao": data_extracao or date.today(),
                "link": LINK_OFICIAL_MALHA,
                "sha256": sha256,
            },
        )

    return RelatorioCamada(
        camada=CAMADA_MUNICIPIO,
        versao_base_id=versao.id,
        feicoes_gravadas=len(malha),
        feicoes_corrigidas=total_corrigidas,
    )
