"""Testes de integração de `ingerir_uc` (Fatia 5, T25).

Usa a fixture `uc_amostra.geojson` (campos reais da camada consolidada UC ERJ do MPRJ descobertos
por acesso real na Fase 0/Fatia 5: `uc`, `categoria`, `jurisdicao`, `tipo`, `cod_cnuc`, `uf_abrang`,
EPSG:4326) — não depende do serviço ArcGIS ao vivo (455 feições, 40 MB) nem de rede. Prova a
reprojeção 4326→4674 e a gravação genérica em `restricao`. Mesmo padrão de container efêmero +
rollback por teste de `test_restricao_car.py`.
"""

import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.restricao_uc import FONTE_UC, ingerir_uc
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
FIXTURE_UC = (
    Path(__file__).resolve().parents[2] / "fixtures" / "restricao_uc" / "uc_amostra.geojson"
)


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
    versao_id = "2026-09-uc"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 4), "draft"),
        )
    return VersaoBase(id=versao_id, criada_em=date(2026, 9, 4))


class TestIngerirUc:
    def test_grava_ucs_com_tipo_unidade_conservacao_reprojetadas(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        relatorio = ingerir_uc(FIXTURE_UC, versao, conexao, data_extracao=date(2026, 9, 4))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT tipo, nome, categoria, ST_SRID(geom), GeometryType(geom), ST_IsValid(geom) "
                "FROM restricao WHERE versao_base_id = %s ORDER BY id",
                (versao.id,),
            )
            linhas = cursor.fetchall()

        assert relatorio.feicoes_gravadas == 2
        assert len(linhas) == 2
        for tipo, _nome, categoria, srid, geom_tipo, valida in linhas:
            assert tipo == Camada.UNIDADE_CONSERVACAO.value
            assert categoria in {"APA", "REBIO"}
            assert srid == 4674  # reprojetado do 4326 de origem para o canônico
            # Polygon e MultiPolygon da origem convergem para MULTIPOLYGON via para_multipolygon
            assert geom_tipo == "MULTIPOLYGON"
            assert valida is True

    def test_nome_da_uc_vira_nome_da_restricao(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_uc(FIXTURE_UC, versao, conexao, data_extracao=date(2026, 9, 4))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT nome FROM restricao WHERE versao_base_id = %s AND categoria = 'APA'",
                (versao.id,),
            )
            (nome,) = cursor.fetchone()  # type: ignore[misc]

        assert nome == "APA de Teste Sobreposta"

    def test_proveniencia_carimbada_com_fonte_e_link_da_uc(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_uc(FIXTURE_UC, versao, conexao, data_extracao=date(2026, 9, 4))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT fonte, data_extracao, link_oficial FROM proveniencia "
                "WHERE camada = %s AND versao_base_id = %s",
                (Camada.UNIDADE_CONSERVACAO.value, versao.id),
            )
            fonte, data_extracao, link = cursor.fetchone()  # type: ignore[misc]

        assert fonte == FONTE_UC
        assert data_extracao == date(2026, 9, 4)
        assert "mprj" in link.lower()
