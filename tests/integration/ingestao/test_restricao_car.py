"""Testes de integração de `ingerir_app_car`/`ingerir_reserva_legal_car` (T16).

Usa as fixtures `.shp` sintéticas em `tests/fixtures/restricao_car/` (campos reais descobertos na
Fase 0/design.md "Fatia 3": `cod_tema`, `nom_tema`, `cod_imovel`, `ind_status`) — não depende dos
arquivos reais do CAR (~1 GB, 430k feições) nem de rede/captcha. Mesmo padrão de container efêmero
+ rollback por teste de `test_sigef.py`.
"""

import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.restricao_car import ingerir_app_car, ingerir_reserva_legal_car
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
FIXTURE_APP = (
    Path(__file__).resolve().parents[2] / "fixtures" / "restricao_car" / "app_amostra.shp"
)
FIXTURE_RESERVA_LEGAL = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "restricao_car"
    / "reserva_legal_amostra.shp"
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
    versao_id = "2026-09-restricao-car"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 4), "draft"),
        )
    return VersaoBase(id=versao_id, criada_em=date(2026, 9, 4))


class TestIngerirAppCar:
    def test_grava_so_feicoes_ativas_com_tipo_app(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=date(2026, 9, 1))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT tipo, categoria, ST_SRID(geom), GeometryType(geom), ST_IsValid(geom) "
                "FROM restricao WHERE versao_base_id = %s ORDER BY id",
                (versao.id,),
            )
            linhas = cursor.fetchall()

        # fixture tem 5 feições, 1 com ind_status='CA' (filtrada) → 4 gravadas
        assert len(linhas) == 4
        for tipo, categoria, srid, geom_tipo, valida in linhas:
            assert tipo == "app"
            assert categoria in {"APP_AREA_AC", "APP_RIO_ATE_10", "APP_ESCADINHA", "APP_TOTAL"}
            assert srid == 4674
            assert geom_tipo == "MULTIPOLYGON"
            assert valida is True

    def test_feicao_cancelada_nao_e_gravada(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=date(2026, 9, 1))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM restricao WHERE versao_base_id = %s AND categoria = %s",
                (versao.id, "APP_VAZIO"),
            )
            (total,) = cursor.fetchone()  # type: ignore[misc]

        assert total == 0

    def test_feicao_invalida_e_corrigida_nao_descartada(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        relatorio = ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=date(2026, 9, 1))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT ST_IsValid(geom) FROM restricao WHERE versao_base_id = %s "
                "AND categoria = %s",
                (versao.id, "APP_TOTAL"),
            )
            (valida,) = cursor.fetchone()  # type: ignore[misc]

        assert valida is True
        assert relatorio.feicoes_corrigidas == 1

    def test_proveniencia_carimbada_com_fonte_car(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=date(2026, 9, 1))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT fonte, data_extracao FROM proveniencia "
                "WHERE camada = %s AND versao_base_id = %s",
                (Camada.APP.value, versao.id),
            )
            linha = cursor.fetchone()

        assert linha is not None
        fonte, data_extracao = linha
        assert fonte == "CAR/SICAR"
        assert data_extracao == date(2026, 9, 1)

    def test_relatorio_reporta_contagens_corretas(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        relatorio = ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=date(2026, 9, 1))

        assert relatorio.camada == Camada.APP.value
        assert relatorio.feicoes_gravadas == 4
        assert relatorio.feicoes_corrigidas == 1


class TestIngerirReservaLegalCar:
    def test_grava_so_feicoes_ativas_com_tipo_reserva_legal(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        relatorio = ingerir_reserva_legal_car(
            FIXTURE_RESERVA_LEGAL, versao, conexao, data_extracao=date(2026, 9, 1)
        )

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT tipo FROM restricao WHERE versao_base_id = %s", (versao.id,)
            )
            linhas = cursor.fetchall()

        # fixture tem 2 feições, 1 com ind_status='PE' (filtrada) → 1 gravada
        assert len(linhas) == 1
        assert linhas[0][0] == "reserva_legal"
        assert relatorio.feicoes_gravadas == 1
        assert relatorio.camada == Camada.RESERVA_LEGAL.value

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT fonte, data_extracao FROM proveniencia "
                "WHERE camada = %s AND versao_base_id = %s",
                (Camada.RESERVA_LEGAL.value, versao.id),
            )
            linha_proveniencia = cursor.fetchone()

        assert linha_proveniencia is not None
        assert linha_proveniencia[0] == "CAR/SICAR"
        assert linha_proveniencia[1] == date(2026, 9, 1)
