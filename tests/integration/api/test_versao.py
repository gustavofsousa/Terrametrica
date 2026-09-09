"""Integração de `resolver_versao_publicada` (T28) contra PostGIS real.

Semeia `versao_base` + `ponteiro_publicado` diretamente via SQL (não roda o pipeline caro de
ingestão — este teste só afirma a leitura do ponteiro) e confere que a versão publicada é
resolvida, e que a ausência de ponteiro levanta erro claro em vez de devolver `None` silencioso.
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.api.versao import SemVersaoPublicada, resolver_versao_publicada
from terrametrica.dominio.modelos import Camada
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
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _semear_versao(conexao: psycopg.Connection, versao_id: str, criada_em: date) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'published')",
            (versao_id, criada_em),
        )
        cursor.execute(
            "INSERT INTO ponteiro_publicado (camada, versao_base_id) VALUES (%s, %s)",
            (Camada.LOTE_RURAL.value, versao_id),
        )


class TestResolverVersaoPublicada:
    def test_resolve_a_versao_apontada_para_lote_rural(self, conexao: psycopg.Connection) -> None:
        _semear_versao(conexao, "v-2026-09", date(2026, 9, 1))

        versao = resolver_versao_publicada(conexao)

        assert versao.id == "v-2026-09"
        assert versao.criada_em == date(2026, 9, 1)

    def test_sem_ponteiro_levanta_erro_claro(self, conexao: psycopg.Connection) -> None:
        with pytest.raises(SemVersaoPublicada):
            resolver_versao_publicada(conexao)
