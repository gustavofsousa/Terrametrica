"""Testes de integração do adapter `LimiteEstadoPostGIS` (T10).

Mesmo padrão de `test_repositorio_lotes_postgis.py`: container PostGIS por módulo,
migrações aplicadas uma vez, transação com rollback por teste. O polígono do RJ é um
retângulo simples semeado direto via SQL — geometria real via geobr é a T11 (fase
seguinte), fora do escopo aqui.
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import Coordenada, VersaoBase
from terrametrica.persistencia.limite_estado_postgis import LimiteEstadoPostGIS
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"

# Retângulo simples que aproxima o RJ (não é o polígono real do estado).
LON_OESTE, LON_LESTE = -44.9, -40.9
LAT_SUL, LAT_NORTE = -23.4, -20.7
RETANGULO_RJ_WKT = (
    f"MULTIPOLYGON((("
    f"{LON_OESTE} {LAT_SUL}, {LON_LESTE} {LAT_SUL}, "
    f"{LON_LESTE} {LAT_NORTE}, {LON_OESTE} {LAT_NORTE}, {LON_OESTE} {LAT_SUL}"
    f")))"
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
def limite(conexao: psycopg.Connection) -> LimiteEstadoPostGIS:
    return LimiteEstadoPostGIS(conexao)


@pytest.fixture
def versao_com_rj_semeado(conexao: psycopg.Connection) -> VersaoBase:
    versao_id = "2026-09"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 1), "published"),
        )
        cursor.execute(
            "INSERT INTO limite_estado (uf, geom, versao_base_id) "
            "VALUES ('RJ', ST_GeomFromText(%s, 4674), %s)",
            (RETANGULO_RJ_WKT, versao_id),
        )
    return VersaoBase(id=versao_id, criada_em=date(2026, 9, 1))


class TestContem:
    def test_coordenada_dentro_do_retangulo_e_true(
        self,
        limite: LimiteEstadoPostGIS,
        versao_com_rj_semeado: VersaoBase,
    ) -> None:
        centro = Coordenada(lat=(LAT_SUL + LAT_NORTE) / 2, lon=(LON_OESTE + LON_LESTE) / 2)

        assert limite.contem(centro) is True

    def test_coordenada_claramente_fora_e_false(
        self,
        limite: LimiteEstadoPostGIS,
        versao_com_rj_semeado: VersaoBase,
    ) -> None:
        fora = Coordenada(lat=-15.0, lon=-47.9)  # Brasília, bem fora do retângulo

        assert limite.contem(fora) is False

    def test_coordenada_na_borda_do_retangulo_e_false(
        self,
        limite: LimiteEstadoPostGIS,
        versao_com_rj_semeado: VersaoBase,
    ) -> None:
        # ST_Contains exclui a borda do polígono: ponto exatamente sobre o vértice
        # oeste/sul do retângulo não é "contido" — comportamento documentado no
        # docstring do adapter.
        na_borda = Coordenada(lat=LAT_SUL, lon=LON_OESTE)

        assert limite.contem(na_borda) is False

    def test_sem_nenhum_limite_semeado_e_false(
        self,
        limite: LimiteEstadoPostGIS,
    ) -> None:
        qualquer_ponto = Coordenada(lat=-22.9, lon=-43.1)

        assert limite.contem(qualquer_ponto) is False
