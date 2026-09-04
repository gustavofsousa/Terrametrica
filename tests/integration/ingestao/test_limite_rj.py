"""Testes de integração de `ingerir_limite_rj` (T11).

O teste principal faz a chamada real ao `geobr` (rede necessária) — não é mockado, por
instrução explícita da fase: se a rede falhar, `ingerir_limite_rj` levanta `RuntimeError` com
mensagem identificando a dependência de rede, não um erro genérico de conexão.

A correção de geometria inválida (`ST_MakeValid` equivalente) é coberta à parte, via unidade
isolada sobre `corrigir_geometria`/`para_multipolygon` (`validacao_geometria.py`) — o dado real
do IBGE via geobr chega válido (confirmado manualmente antes desta implementação), então não há
como exercitar o ramo de correção com dado real sem fabricar uma geometria inválida à parte.
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from shapely.geometry import MultiPolygon, Polygon
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.limite_rj import CAMADA_LIMITE_ESTADO, ingerir_limite_rj
from terrametrica.ingestao.validacao_geometria import corrigir_geometria, para_multipolygon
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"


def _garantir_docker_disponivel() -> None:
    try:
        resultado = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10, check=False
        )
    except FileNotFoundError:
        pytest.fail("Docker não encontrado — instale e rode o Docker antes desta suíte.")
    if resultado.returncode != 0:
        pytest.fail(
            "Docker não está disponível (`docker info` falhou) — os testes de integração "
            "exigem um container PostGIS efêmero via testcontainers."
        )


@pytest.fixture(scope="module")
def container() -> Iterator[PostgresContainer]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        with psycopg.connect(postgres.get_connection_url(driver=None)) as conexao_migracao:
            aplicar_migracoes(conexao_migracao)
        yield postgres


@pytest.fixture
def conexao(container: PostgresContainer) -> Iterator[psycopg.Connection]:
    conexao = psycopg.connect(container.get_connection_url(driver=None))
    try:
        yield conexao
    finally:
        conexao.rollback()
        conexao.close()


@pytest.fixture
def versao(conexao: psycopg.Connection) -> VersaoBase:
    versao_id = "2026-09-limite-rj"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 1), "draft"),
        )
    return VersaoBase(id=versao_id, criada_em=date(2026, 9, 1))


class TestIngerirLimiteRJ:
    def test_grava_exatamente_uma_linha_valida_em_epsg_4674_via_geobr(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        relatorio = ingerir_limite_rj(versao, conexao)

        assert relatorio.camada == CAMADA_LIMITE_ESTADO
        assert relatorio.versao_base_id == versao.id
        assert relatorio.feicoes_gravadas == 1

        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT ST_SRID(geom), ST_IsValid(geom), GeometryType(geom), uf
                FROM limite_estado
                WHERE versao_base_id = %s
                """,
                (versao.id,),
            )
            linhas = cursor.fetchall()

        assert len(linhas) == 1
        srid, valida, tipo, uf = linhas[0]
        assert srid == 4674
        assert valida is True
        assert tipo == "MULTIPOLYGON"
        assert uf == "RJ"


class TestCorrigirGeometria:
    def test_conserta_poligono_self_intersecting_sem_descartar(self) -> None:
        bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
        assert not bowtie.is_valid

        geom_corrigida, foi_corrigida = corrigir_geometria(bowtie)

        assert foi_corrigida is True
        assert geom_corrigida.is_valid


class TestParaMultipolygon:
    def test_normaliza_polygon_simples_para_multipolygon(self) -> None:
        quadrado = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

        resultado = para_multipolygon(quadrado)

        assert isinstance(resultado, MultiPolygon)
        assert len(resultado.geoms) == 1
