"""A guarda de publicação cobre a camada `municipio` — spec:mapa-do-lote-rj (T4: MUN-01, MUN-04).

Container próprio: `ponteiro_publicado` é global por camada, e o estado deixado por
`test_publicar.py` mudaria a "versão anterior" destes cenários.
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.municipios_rj import CAMADA_MUNICIPIO, ingerir_municipios_rj
from terrametrica.ingestao.publicar import publicar_versao
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


@pytest.fixture
def conexao() -> Iterator[psycopg.Connection]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        with psycopg.connect(postgres.get_connection_url(driver=None)) as conn:
            aplicar_migracoes(conn)
            yield conn


def _criar_versao(conexao: psycopg.Connection, versao_id: str, *, municipios: int) -> VersaoBase:
    versao = VersaoBase(id=versao_id, criada_em=date(2026, 10, 1))
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
            (versao.id, versao.criada_em),
        )
    if municipios:
        ingerir_municipios_rj(versao, conexao, ler=lambda: malha_sintetica(municipios))
    conexao.commit()
    return versao


def _ponteiro(conexao: psycopg.Connection, camada: str) -> str | None:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT versao_base_id FROM ponteiro_publicado WHERE camada = %s", (camada,))
        linha = cursor.fetchone()
    return linha[0] if linha else None


def test_mun01_primeira_versao_com_92_municipios_publica_e_aponta_a_camada(
    conexao: psycopg.Connection,
) -> None:
    versao = _criar_versao(conexao, "mun-v1", municipios=92)

    resultado = publicar_versao(versao, conexao)

    assert resultado.publicada is True
    camada = next(c for c in resultado.camadas if c.camada == CAMADA_MUNICIPIO)
    assert (camada.feicoes_novas, camada.feicoes_anteriores) == (92, None)
    assert _ponteiro(conexao, CAMADA_MUNICIPIO) == "mun-v1"


def test_mun04_versao_sem_municipios_nao_publica_se_a_anterior_tinha(
    conexao: psycopg.Connection,
) -> None:
    anterior = _criar_versao(conexao, "mun-v1", municipios=92)
    assert publicar_versao(anterior, conexao).publicada is True
    nova = _criar_versao(conexao, "mun-v2", municipios=0)

    resultado = publicar_versao(nova, conexao)

    assert resultado.publicada is False
    camada = next(c for c in resultado.camadas if c.camada == CAMADA_MUNICIPIO)
    assert (camada.publicada, camada.feicoes_novas, camada.feicoes_anteriores) == (False, 0, 92)
    assert _ponteiro(conexao, CAMADA_MUNICIPIO) == "mun-v1"
