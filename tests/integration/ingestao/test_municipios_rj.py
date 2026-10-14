"""Ingestão da malha municipal contra PostGIS — spec:mapa-do-lote-rj (T2: MUN-01, 05, 06).

A malha vem de um leitor injetável com feições sintéticas: a chamada real ao geobr é coberta
pela carga real de `carregar_base`, não pela suíte.
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.municipios_rj import (
    FONTE_MALHA,
    MalhaIncompleta,
    ingerir_municipios_rj,
    sha256_canonico,
)
from terrametrica.persistencia.migrar import aplicar_migracoes
from tests.fakes.malha_municipal_fake import malha_sintetica

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
    versao_id = "2026-10-municipios"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
            (versao_id, date(2026, 10, 1)),
        )
    return VersaoBase(id=versao_id, criada_em=date(2026, 10, 1))


def _contar_municipios(conexao: psycopg.Connection, versao: VersaoBase) -> int:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM municipio WHERE versao_base_id = %s", (versao.id,))
        (total,) = cursor.fetchone()  # type: ignore[misc]
    return int(total)


def test_mun01_92_feicoes_sinteticas_viram_92_linhas(
    conexao: psycopg.Connection, versao: VersaoBase
) -> None:
    relatorio = ingerir_municipios_rj(versao, conexao, ler=lambda: malha_sintetica(92))

    assert _contar_municipios(conexao, versao) == 92
    assert relatorio.feicoes_gravadas == 92
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT nome, uf, ST_SRID(geom) FROM municipio WHERE codigo = '3300003' "
            "AND versao_base_id = %s",
            (versao.id,),
        )
        assert cursor.fetchone() == ("Município 03", "33", 4674)


def test_mun06_segunda_carga_na_mesma_versao_continua_com_92_linhas(
    conexao: psycopg.Connection, versao: VersaoBase
) -> None:
    ingerir_municipios_rj(versao, conexao, ler=lambda: malha_sintetica(92))
    ingerir_municipios_rj(versao, conexao, ler=lambda: malha_sintetica(92))

    assert _contar_municipios(conexao, versao) == 92
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM proveniencia WHERE camada = 'municipio' AND versao_base_id = %s",
            (versao.id,),
        )
        assert cursor.fetchone() == (1,)


def test_mun05_proveniencia_cita_fonte_data_e_sha256_da_malha(
    conexao: psycopg.Connection, versao: VersaoBase
) -> None:
    malha = malha_sintetica(92)

    ingerir_municipios_rj(
        versao, conexao, ler=lambda: malha, data_extracao=date(2026, 10, 14)
    )

    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT fonte, data_extracao, sha256 FROM proveniencia "
            "WHERE camada = 'municipio' AND versao_base_id = %s",
            (versao.id,),
        )
        assert cursor.fetchone() == (FONTE_MALHA, date(2026, 10, 14), sha256_canonico(malha))
    assert FONTE_MALHA == "IBGE — Malha Municipal 2025"


def test_mun04_malha_com_91_nao_grava_nada(
    conexao: psycopg.Connection, versao: VersaoBase
) -> None:
    with pytest.raises(MalhaIncompleta, match="91 feições"):
        ingerir_municipios_rj(versao, conexao, ler=lambda: malha_sintetica(91))

    assert _contar_municipios(conexao, versao) == 0
