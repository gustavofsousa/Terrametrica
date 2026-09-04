"""Testes de integração de `ingerir_sigef` (T12).

Usa a fixture `.shp` sintética em `tests/fixtures/sigef/sigef_rj_amostra.shp` (4 feições: 3
válidas + 1 propositalmente inválida/self-intersecting) — não depende do arquivo real de SIGEF
(~1 GB) nem de rede/login GOV.BR. Mesmo padrão de container efêmero + rollback por teste de
`test_limite_rj.py`/`test_repositorio_lotes_postgis.py`.
"""

import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.sigef import _mapear_situacao, ingerir_sigef
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
FIXTURE_SIGEF = (
    Path(__file__).resolve().parents[2] / "fixtures" / "sigef" / "sigef_rj_amostra.shp"
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
    versao_id = "2026-09-sigef"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 1), "draft"),
        )
    return VersaoBase(id=versao_id, criada_em=date(2026, 9, 1))


class TestIngerirSigef:
    def test_grava_todas_as_feicoes_com_geom_car_nulo_em_epsg_4674(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_sigef(FIXTURE_SIGEF, versao, conexao, data_extracao=date(2026, 8, 20))

        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT codigo_sigef, situacao_certificacao, geom_car,
                       ST_SRID(geom_sigef), GeometryType(geom_sigef), ST_IsValid(geom_sigef)
                FROM lote_rural
                WHERE versao_base_id = %s
                ORDER BY codigo_sigef
                """,
                (versao.id,),
            )
            linhas = cursor.fetchall()

        assert len(linhas) == 4
        for _codigo, situacao, geom_car, srid, tipo, valida in linhas:
            assert geom_car is None
            assert srid == 4674
            assert tipo == "MULTIPOLYGON"
            assert valida is True
            assert situacao in {"certificado", "em_analise"}

        por_codigo = {linha[0]: linha[1] for linha in linhas}
        assert por_codigo["SIGEF-001"] == "certificado"
        assert por_codigo["SIGEF-003"] == "em_analise"

    def test_feicao_invalida_e_corrigida_e_marcada_nao_descartada(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_sigef(FIXTURE_SIGEF, versao, conexao, data_extracao=date(2026, 8, 20))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT geometria_corrigida FROM lote_rural "
                "WHERE versao_base_id = %s AND codigo_sigef = %s",
                (versao.id, "SIGEF-004"),
            )
            (corrigida,) = cursor.fetchone()  # type: ignore[misc]

        assert corrigida is True

    def test_proveniencia_carimbada_com_fonte_e_link(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        ingerir_sigef(FIXTURE_SIGEF, versao, conexao, data_extracao=date(2026, 8, 20))

        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT fonte, data_extracao, link_oficial FROM proveniencia "
                "WHERE camada = %s AND versao_base_id = %s",
                (Camada.LOTE_RURAL.value, versao.id),
            )
            linha = cursor.fetchone()

        assert linha is not None
        fonte, data_extracao, link_oficial = linha
        assert fonte == "SIGEF"
        assert data_extracao == date(2026, 8, 20)
        assert link_oficial.startswith("https://sigef.incra.gov.br")

    def test_relatorio_reporta_contagens_corretas(
        self, conexao: psycopg.Connection, versao: VersaoBase
    ) -> None:
        relatorio = ingerir_sigef(FIXTURE_SIGEF, versao, conexao, data_extracao=date(2026, 8, 20))

        assert relatorio.camada == Camada.LOTE_RURAL.value
        assert relatorio.versao_base_id == versao.id
        assert relatorio.feicoes_gravadas == 4
        assert relatorio.feicoes_corrigidas == 1


class TestMapearSituacao:
    def test_certificada_mapeia_para_certificado(self) -> None:
        assert _mapear_situacao("CERTIFICADA") == "certificado"

    def test_qualquer_outro_texto_mapeia_para_em_analise(self) -> None:
        assert _mapear_situacao("EM ANALISE") == "em_analise"
        assert _mapear_situacao("cancelada") == "em_analise"
