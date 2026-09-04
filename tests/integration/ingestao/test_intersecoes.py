"""Testes de integração de `materializar_intersecoes` (T17).

Usa as fixtures reais já existentes: `sigef_rj_amostra.shp` (lote SIGEF-001, bounds
[-43.105,-22.905,-43.095,-22.895]) e `app_amostra.shp`/`reserva_legal_amostra.shp` (T16),
posicionadas deliberadamente contra SIGEF-001: uma feição APP com sobreposição plena (metade do
lote), uma marginal (~0.5% do lote), uma sem sobreposição nenhuma, e uma Reserva Legal com
sobreposição plena na outra metade.
"""

import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.intersecoes import materializar_intersecoes
from terrametrica.ingestao.restricao_car import ingerir_app_car, ingerir_reserva_legal_car
from terrametrica.ingestao.sigef import ingerir_sigef
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
FIXTURE_SIGEF = FIXTURES / "sigef" / "sigef_rj_amostra.shp"
FIXTURE_APP = FIXTURES / "restricao_car" / "app_amostra.shp"
FIXTURE_RESERVA_LEGAL = FIXTURES / "restricao_car" / "reserva_legal_amostra.shp"


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
def versao_com_lote_e_restricoes(conexao: psycopg.Connection) -> VersaoBase:
    """Semeia `lote_rural` (SIGEF-001..004) e `restricao` (APP + Reserva Legal ativas) na mesma
    versão, sem publicar — `materializar_intersecoes` lê staging, não a versão publicada."""
    versao_id = "2026-09-intersecoes"
    versao = VersaoBase(id=versao_id, criada_em=date(2026, 9, 4))
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, versao.criada_em, "draft"),
        )
    ingerir_sigef(FIXTURE_SIGEF, versao, conexao, data_extracao=date(2026, 9, 1))
    ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=date(2026, 9, 1))
    ingerir_reserva_legal_car(
        FIXTURE_RESERVA_LEGAL, versao, conexao, data_extracao=date(2026, 9, 1)
    )
    return versao


class TestMaterializarIntersecoes:
    def test_intersecao_plena_grava_area_correta(
        self, conexao: psycopg.Connection, versao_com_lote_e_restricoes: VersaoBase
    ) -> None:
        materializar_intersecoes(versao_com_lote_e_restricoes, conexao)

        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT im.area_intersecao_m2
                FROM intersecao_materializada im
                JOIN lote_rural l ON l.id = im.lote_id AND l.versao_base_id = im.versao_base_id
                JOIN restricao r ON r.id = im.restricao_id AND r.versao_base_id = im.versao_base_id
                WHERE l.codigo_sigef = %s AND r.categoria = %s
                """,
                ("SIGEF-001", "APP_AREA_AC"),
            )
            linha = cursor.fetchone()

        assert linha is not None
        (area_m2,) = linha
        # metade de um lote ~0.01° x 0.01° a lat -22.9 — só precisa ser claramente >0 e plausível
        assert area_m2 > 400_000.0  # ~50% de ~1.03 km² em m²

    def test_intersecao_marginal_tambem_e_materializada(
        self, conexao: psycopg.Connection, versao_com_lote_e_restricoes: VersaoBase
    ) -> None:
        materializar_intersecoes(versao_com_lote_e_restricoes, conexao)

        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT im.area_intersecao_m2
                FROM intersecao_materializada im
                JOIN lote_rural l ON l.id = im.lote_id AND l.versao_base_id = im.versao_base_id
                JOIN restricao r ON r.id = im.restricao_id AND r.versao_base_id = im.versao_base_id
                WHERE l.codigo_sigef = %s AND r.categoria = %s
                """,
                ("SIGEF-001", "APP_ESCADINHA"),
            )
            linha = cursor.fetchone()

        assert linha is not None
        (area_m2,) = linha
        assert 0.0 < area_m2 < 10_000.0  # faixa fina — bem menor que a plena

    def test_sem_sobreposicao_nao_gera_linha(
        self, conexao: psycopg.Connection, versao_com_lote_e_restricoes: VersaoBase
    ) -> None:
        materializar_intersecoes(versao_com_lote_e_restricoes, conexao)

        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*)
                FROM intersecao_materializada im
                JOIN restricao r ON r.id = im.restricao_id AND r.versao_base_id = im.versao_base_id
                WHERE r.categoria = %s
                """,
                ("APP_RIO_ATE_10",),
            )
            (total,) = cursor.fetchone()  # type: ignore[misc]

        assert total == 0

    def test_toque_de_borda_sem_area_nao_gera_linha(
        self, conexao: psycopg.Connection, versao_com_lote_e_restricoes: VersaoBase
    ) -> None:
        # Restrição que compartilha SÓ a borda direita do lote SIGEF-001 (x = -43.095):
        # ST_Intersects é verdadeiro (fronteira em comum), mas ST_Intersection é uma linha,
        # área = 0. O filtro `area_m2 > 0` de `materializar_intersecoes` tem que descartá-la —
        # senão o dossiê mostraria uma restrição de 0% que não cobre nada do lote (ruído).
        versao = versao_com_lote_e_restricoes
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO restricao (id, tipo, nome, categoria, geom, versao_base_id)
                VALUES (%s, 'app', %s, %s, ST_GeomFromText(%s, 4674), %s)
                """,
                (
                    "app-toque-borda",
                    "APP que só toca a borda",
                    "APP_RIO_ATE_10",
                    "MULTIPOLYGON(((-43.095 -22.905, -43.090 -22.905, "
                    "-43.090 -22.895, -43.095 -22.895, -43.095 -22.905)))",
                    versao.id,
                ),
            )

        materializar_intersecoes(versao, conexao)

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM intersecao_materializada "
                "WHERE restricao_id = %s AND versao_base_id = %s",
                ("app-toque-borda", versao.id),
            )
            (total,) = cursor.fetchone()  # type: ignore[misc]

        assert total == 0

    def test_rodar_duas_vezes_nao_duplica_linhas(
        self, conexao: psycopg.Connection, versao_com_lote_e_restricoes: VersaoBase
    ) -> None:
        materializar_intersecoes(versao_com_lote_e_restricoes, conexao)
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM intersecao_materializada WHERE versao_base_id = %s",
                (versao_com_lote_e_restricoes.id,),
            )
            (total_primeira_vez,) = cursor.fetchone()  # type: ignore[misc]

        segundo_relatorio = materializar_intersecoes(versao_com_lote_e_restricoes, conexao)
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM intersecao_materializada WHERE versao_base_id = %s",
                (versao_com_lote_e_restricoes.id,),
            )
            (total_segunda_vez,) = cursor.fetchone()  # type: ignore[misc]

        assert total_segunda_vez == total_primeira_vez
        assert segundo_relatorio.pares_materializados == 0
