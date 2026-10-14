"""Base semeada dos testes de navegador (AD-017): fixtures pequenas, sem rede.

Pontos conhecidos para os testes clicarem, todos em `[lat, lon]`.
"""

from datetime import date
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import psycopg
from shapely.geometry import box  # type: ignore[import-untyped]

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.cobertura import semear_cobertura
from terrametrica.ingestao.intersecoes import materializar_intersecoes
from terrametrica.ingestao.limite_rj import ingerir_limite_rj
from terrametrica.ingestao.municipios_rj import ingerir_municipios_rj
from terrametrica.ingestao.publicar import publicar_versao
from terrametrica.ingestao.restricao_car import ingerir_app_car, ingerir_reserva_legal_car
from terrametrica.ingestao.restricao_uc import ingerir_uc
from terrametrica.ingestao.sigef import ingerir_sigef
from terrametrica.persistencia.migrar import aplicar_migracoes
from tests.fakes.malha_municipal_fake import malha_sintetica

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
VERSAO_ID = "nav-v1"
DATA = date(2026, 9, 1)

# SIGEF-001 (fixture): quadrado de 0,01° centrado aqui — um lote com restrições cruzadas.
PONTO_LOTE = (-22.90, -43.10)
BBOX_LOTE = (-43.105, -22.905, -43.095, -22.895)  # oeste, sul, leste, norte
# Dois lotes sobrepostos (409): o mesmo quadrado de 0,02° sob dois ids.
PONTO_SOBREPOSTO = (-22.85, -43.30)
IDS_SOBREPOSTOS = ("OVL-1", "OVL-2")
# Dentro do RJ e do "Município 25" sintético, sem lote (404 com nome).
PONTO_SEM_LOTE = (-22.95, -43.49)
NOME_MUNICIPIO_SEM_LOTE = "Município 25"
# São Paulo: fora do RJ (422).
PONTO_FORA_DO_RJ = (-23.5505, -46.6333)

_RJ_SINTETICO = box(-44.9, -23.4, -40.9, -20.7)
_QUADRADO_SOBREPOSTO = (
    "MULTIPOLYGON(((-43.31 -22.86, -43.29 -22.86, -43.29 -22.84, -43.31 -22.84, -43.31 -22.86)))"
)


def semear_base(url: str) -> None:
    """Migra, ingere as fixtures e publica a versão `VERSAO_ID`."""
    versao = VersaoBase(id=VERSAO_ID, criada_em=DATA)
    with psycopg.connect(url) as conexao:
        aplicar_migracoes(conexao)
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
                (versao.id, versao.criada_em),
            )
        conexao.commit()

        # O limite sintético evita a rede (geobr) e ainda deixa São Paulo fora.
        ingerir_limite_rj(versao, conexao, ler=_ler_limite_sintetico)
        malha = malha_sintetica(codigos=("3304557", "3300100", "3303500"))
        ingerir_municipios_rj(versao, conexao, ler=lambda: malha, data_extracao=DATA)
        ingerir_sigef(
            FIXTURES / "sigef" / "sigef_rj_amostra.shp", versao, conexao, data_extracao=DATA
        )
        ingerir_app_car(
            FIXTURES / "restricao_car" / "app_amostra.shp", versao, conexao, data_extracao=DATA
        )
        ingerir_reserva_legal_car(
            FIXTURES / "restricao_car" / "reserva_legal_amostra.shp",
            versao,
            conexao,
            data_extracao=DATA,
        )
        ingerir_uc(
            FIXTURES / "restricao_uc" / "uc_amostra.geojson", versao, conexao, data_extracao=DATA
        )
        _semear_lotes_sobrepostos(conexao)
        materializar_intersecoes(versao, conexao)
        semear_cobertura(versao, conexao)
        resultado = publicar_versao(versao, conexao)
        assert resultado.publicada, f"a guarda reprovou a base dos testes de navegador: {resultado}"


def _ler_limite_sintetico(**_: object) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"geometry": [_RJ_SINTETICO]}, crs="EPSG:4674")


def _semear_lotes_sobrepostos(conexao: psycopg.Connection) -> None:
    with conexao.cursor() as cursor:
        for lote_id in IDS_SOBREPOSTOS:
            cursor.execute(
                "INSERT INTO lote_rural (id, uf, municipios, codigo_sigef, "
                "situacao_certificacao, geom_sigef, versao_base_id) VALUES "
                "(%s, 'RJ', ARRAY['3304557'], %s, 'certificado', ST_GeomFromText(%s, 4674), %s)",
                (lote_id, f"SIGEF-{lote_id}", _QUADRADO_SOBREPOSTO, VERSAO_ID),
            )
