"""Testes de integração do runner de migração (T8).

Sobe um container PostGIS efêmero (`testcontainers`), aplica a migração da Fatia 2
e faz introspecção via `information_schema`/`pg_extension` — sem mocks, contra um
banco real. Exige Docker disponível; ver `docs/DEV-SETUP.md`.
"""

import subprocess
from collections.abc import Iterator

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"

TABELAS_ESPERADAS = {
    "versao_base",
    "ponteiro_publicado",
    "limite_estado",
    "lote_rural",
    "proveniencia",
    "cobertura",
}


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
def conexao() -> Iterator[psycopg.Connection]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        url = postgres.get_connection_url(driver=None)
        with psycopg.connect(url) as conn:
            yield conn


class TestAplicarMigracoes:
    def test_cria_as_tabelas_de_dominio_da_fatia_2(self, conexao: psycopg.Connection) -> None:
        aplicar_migracoes(conexao)

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            tabelas = {linha[0] for linha in cursor.fetchall()}

        assert TABELAS_ESPERADAS <= tabelas

    def test_habilita_a_extensao_postgis(self, conexao: psycopg.Connection) -> None:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
            extensoes = {linha[0] for linha in cursor.fetchall()}

        assert "postgis" in extensoes

    def test_rodar_duas_vezes_e_idempotente(self, conexao: psycopg.Connection) -> None:
        aplicar_migracoes(conexao)  # já aplicada pelo teste anterior; não deve falhar nem duplicar

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM schema_migrations WHERE nome_arquivo = %s",
                ("0001_fatia2_sigef.sql",),
            )
            (quantidade,) = cursor.fetchone()

        assert quantidade == 1
