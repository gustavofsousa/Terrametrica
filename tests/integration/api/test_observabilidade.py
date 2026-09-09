"""Integração de `registrar_consulta` (T31, DOS-30) contra PostGIS real.

Grava e relê a linha de `consulta_log`. Confere que uma consulta que resolveu um lote carrega o
`lote_id` e as camadas, e que uma consulta sem lote (fora do RJ / sobreposição) grava `lote_id`
nulo mas ainda registra a tentativa — a consulta aconteceu.
"""

import subprocess
from collections.abc import Iterator

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.api.observabilidade import EntradaConsulta, registrar_consulta
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"


def _garantir_docker_disponivel() -> None:
    try:
        resultado = subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        pytest.fail("Docker não encontrado — instale e rode o Docker antes desta suíte.")
    if resultado.returncode != 0:
        pytest.fail("Docker não está disponível (`docker info` falhou).")


@pytest.fixture(scope="module")
def container() -> Iterator[PostgresContainer]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        with psycopg.connect(postgres.get_connection_url(driver=None)) as conn:
            aplicar_migracoes(conn)
        yield postgres


@pytest.fixture
def conexao(container: PostgresContainer) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(container.get_connection_url(driver=None))
    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE consulta_log")
        conn.commit()
        yield conn
    finally:
        conn.close()


class TestRegistrarConsulta:
    def test_grava_consulta_com_lote_e_camadas(self, conexao: psycopg.Connection) -> None:
        registrar_consulta(
            conexao,
            EntradaConsulta(
                conta_id="conta-a",
                latencia_ms=42,
                lote_id="RJ-1",
                camadas=("lote_rural", "app"),
            ),
        )

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT conta_id, lote_id, camadas, latencia_ms FROM consulta_log"
            )
            linhas = cursor.fetchall()

        assert linhas == [("conta-a", "RJ-1", ["lote_rural", "app"], 42)]

    def test_grava_consulta_sem_lote_com_lote_id_nulo(self, conexao: psycopg.Connection) -> None:
        registrar_consulta(
            conexao, EntradaConsulta(conta_id="conta-b", latencia_ms=7)
        )

        with conexao.cursor() as cursor:
            cursor.execute("SELECT conta_id, lote_id, camadas FROM consulta_log")
            (linha,) = cursor.fetchall()

        assert linha == ("conta-b", None, [])
