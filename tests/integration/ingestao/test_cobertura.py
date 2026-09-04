"""Testes de integração de `semear_cobertura` (Fatia 4, T21 — fecha TD-002, AD-009).

Semeia `lote_rural` + `restricao` + `proveniencia` direto por SQL (geometrias mínimas, sem
shapefile nem geobr) e prova que `semear_cobertura` deriva o produto (município do lote × camada
de restrição) marcando `tem_dado = true` com a data da proveniência da camada. Mesmo padrão de
container efêmero + rollback por teste de `test_restricao_car.py`.
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.cobertura import semear_cobertura
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"

# Dois municípios (códigos IBGE, como em `lote_rural.municipios`) e duas camadas de restrição,
# com datas de extração distintas por camada para provar que cada linha carrega a data certa.
MUNICIPIO_A = "3304557"  # Rio de Janeiro
MUNICIPIO_B = "3300100"  # Angra dos Reis
DATA_APP = date(2026, 9, 1)
DATA_RESERVA_LEGAL = date(2026, 8, 15)

_GEOM_MINIMA = "MULTIPOLYGON(((-43.2 -22.9,-43.2 -22.8,-43.1 -22.8,-43.1 -22.9,-43.2 -22.9)))"


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
def versao_com_dado(conexao: psycopg.Connection) -> VersaoBase:
    """Semeia dois lotes (municípios A e B) e as restrições app/reserva_legal com proveniência,
    sem materializar cobertura — o estado que `semear_cobertura` deve consumir."""
    versao_id = "2026-09-cobertura"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 4), "draft"),
        )
        for lote_id, municipio in (("L-A", MUNICIPIO_A), ("L-B", MUNICIPIO_B)):
            cursor.execute(
                "INSERT INTO lote_rural "
                "(id, uf, municipios, codigo_sigef, situacao_certificacao, geom_sigef, "
                " versao_base_id) "
                "VALUES (%s, 'RJ', %s, %s, 'CERTIFICADA', ST_GeomFromText(%s, 4674), %s)",
                (lote_id, [municipio], f"SIGEF-{lote_id}", _GEOM_MINIMA, versao_id),
            )
        for restr_id, tipo in (("R-APP", "app"), ("R-RL", "reserva_legal")):
            cursor.execute(
                "INSERT INTO restricao (id, tipo, nome, geom, versao_base_id) "
                "VALUES (%s, %s, %s, ST_GeomFromText(%s, 4674), %s)",
                (restr_id, tipo, tipo, _GEOM_MINIMA, versao_id),
            )
        for camada, data_extracao in (("app", DATA_APP), ("reserva_legal", DATA_RESERVA_LEGAL)):
            cursor.execute(
                "INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao, "
                "link_oficial) VALUES (%s, %s, 'CAR/SICAR', %s, 'http://exemplo')",
                (camada, versao_id, data_extracao),
            )
    return VersaoBase(id=versao_id, criada_em=date(2026, 9, 4))


def _cobertura(conexao: psycopg.Connection) -> dict[tuple[str, str], tuple[bool, date | None]]:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT municipio, camada, tem_dado, data_extracao FROM cobertura")
        return {(m, c): (tem, data) for m, c, tem, data in cursor.fetchall()}


class TestSemearCobertura:
    def test_semeia_produto_municipio_do_lote_por_camada_de_restricao(
        self, conexao: psycopg.Connection, versao_com_dado: VersaoBase
    ) -> None:
        semear_cobertura(versao_com_dado, conexao)

        cobertura = _cobertura(conexao)
        # 2 municípios (dos lotes) × 2 camadas (das restrições) = 4 linhas, todas tem_dado=true.
        assert cobertura == {
            (MUNICIPIO_A, "app"): (True, DATA_APP),
            (MUNICIPIO_A, "reserva_legal"): (True, DATA_RESERVA_LEGAL),
            (MUNICIPIO_B, "app"): (True, DATA_APP),
            (MUNICIPIO_B, "reserva_legal"): (True, DATA_RESERVA_LEGAL),
        }

    def test_carimba_data_de_extracao_da_proveniencia_da_camada(
        self, conexao: psycopg.Connection, versao_com_dado: VersaoBase
    ) -> None:
        semear_cobertura(versao_com_dado, conexao)

        cobertura = _cobertura(conexao)
        # A data vem da proveniência da camada, não de uma data única do passo — app e reserva
        # legal têm datas distintas e cada linha carrega a sua.
        assert cobertura[(MUNICIPIO_A, "app")][1] == DATA_APP
        assert cobertura[(MUNICIPIO_A, "reserva_legal")][1] == DATA_RESERVA_LEGAL

    def test_camada_nao_ingerida_nao_recebe_linha_de_cobertura(
        self, conexao: psycopg.Connection, versao_com_dado: VersaoBase
    ) -> None:
        semear_cobertura(versao_com_dado, conexao)

        cobertura = _cobertura(conexao)
        # unidade_conservacao (INEA/ICMBio) não foi ingerida → nenhuma linha; o dossiê a marca
        # honestamente como "sem cobertura" (DOS-11), não como coberta.
        assert not any(camada == "unidade_conservacao" for _, camada in cobertura)

    def test_relatorio_conta_linhas_semeadas(
        self, conexao: psycopg.Connection, versao_com_dado: VersaoBase
    ) -> None:
        relatorio = semear_cobertura(versao_com_dado, conexao)

        assert relatorio.versao_base_id == versao_com_dado.id
        assert relatorio.linhas_semeadas == 4

    def test_idempotente_nao_duplica_nem_erra_na_segunda_rodada(
        self, conexao: psycopg.Connection, versao_com_dado: VersaoBase
    ) -> None:
        semear_cobertura(versao_com_dado, conexao)
        semear_cobertura(versao_com_dado, conexao)  # ON CONFLICT DO UPDATE — não deve estourar PK

        cobertura = _cobertura(conexao)
        assert len(cobertura) == 4

    def test_reseed_atualiza_data_extracao_da_cobertura(
        self, conexao: psycopg.Connection, versao_com_dado: VersaoBase
    ) -> None:
        # AD-009/DOS-13: o upsert é DO UPDATE, não DO NOTHING — uma reingestão que corrige a data
        # de extração da proveniência TEM de refrescar a data carimbada na cobertura, senão o
        # dossiê mostraria uma data obsoleta para uma camada que na verdade foi reingerida.
        semear_cobertura(versao_com_dado, conexao)
        data_corrigida = date(2026, 10, 20)
        with conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE proveniencia SET data_extracao = %s "
                "WHERE camada = 'app' AND versao_base_id = %s",
                (data_corrigida, versao_com_dado.id),
            )

        semear_cobertura(versao_com_dado, conexao)

        cobertura = _cobertura(conexao)
        assert cobertura[(MUNICIPIO_A, "app")][1] == data_corrigida
        assert cobertura[(MUNICIPIO_B, "app")][1] == data_corrigida

    def test_restricao_sem_proveniencia_nao_gera_cobertura(
        self, conexao: psycopg.Connection
    ) -> None:
        # Boundary DOS-11 vs DOS-12 (AD-009/AD-005): sem data de extração (proveniência) não se
        # declara cobertura — o JOIN interno descarta a camada, que cai em "sem cobertura", nunca
        # é carimbada com data nula. Prova que o JOIN é INNER, não LEFT.
        versao_id = "2026-09-sem-proveniencia"
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
                (versao_id, date(2026, 9, 4)),
            )
            cursor.execute(
                "INSERT INTO lote_rural (id, uf, municipios, codigo_sigef, situacao_certificacao, "
                "geom_sigef, versao_base_id) VALUES ('L-A', 'RJ', %s, 'SIGEF-L-A', 'CERTIFICADA', "
                "ST_GeomFromText(%s, 4674), %s)",
                ([MUNICIPIO_A], _GEOM_MINIMA, versao_id),
            )
            cursor.execute(
                "INSERT INTO restricao (id, tipo, nome, geom, versao_base_id) "
                "VALUES ('R-APP', 'app', 'app', ST_GeomFromText(%s, 4674), %s)",
                (_GEOM_MINIMA, versao_id),
            )
            # deliberadamente NÃO inserimos proveniencia para 'app'

        relatorio = semear_cobertura(VersaoBase(id=versao_id, criada_em=date(2026, 9, 4)), conexao)

        assert relatorio.linhas_semeadas == 0
        assert _cobertura(conexao) == {}
