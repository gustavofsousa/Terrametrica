"""Testes de integração do adapter `RepositorioLotesPostGIS` (T9).

Sobe um container PostGIS efêmero (`testcontainers`) uma vez por módulo e aplica as
migrações da Fatia 2 (schema + índices GiST). Cada teste roda numa transação própria,
semeando dados via SQL direto e revertendo no teardown — a ingestão real (T12) é fora do
escopo desta fatia; aqui só validamos o contrato do Protocol `RepositorioLotes` contra o
schema real (mesmos ramos do fake em memória de T5, exceto TD-001).
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import (
    Camada,
    Coordenada,
    LoteRural,
    Sobreposicao,
    VersaoBase,
)
from terrametrica.persistencia.migrar import aplicar_migracoes
from terrametrica.persistencia.repositorio_lotes_postgis import (
    MENSAGEM_TD_001,
    RepositorioLotesPostGIS,
)

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"


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


def _quadrado_wkt(lon: float, lat: float, lado: float = 0.01) -> str:
    """MULTIPOLYGON de um quadrado centrado em (lon, lat), lado em graus."""
    meio = lado / 2
    pontos = [
        (lon - meio, lat - meio),
        (lon + meio, lat - meio),
        (lon + meio, lat + meio),
        (lon - meio, lat + meio),
        (lon - meio, lat - meio),
    ]
    anel = ", ".join(f"{x} {y}" for x, y in pontos)
    return f"MULTIPOLYGON((({anel})))"


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
def repositorio(conexao: psycopg.Connection) -> RepositorioLotesPostGIS:
    return RepositorioLotesPostGIS(conexao)


@pytest.fixture
def versao(conexao: psycopg.Connection) -> VersaoBase:
    versao_id = "2026-09"
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 1), "published"),
        )
    return VersaoBase(id=versao_id, criada_em=date(2026, 9, 1))


def _inserir_lote(
    conexao: psycopg.Connection,
    versao: VersaoBase,
    *,
    id_: str,
    wkt: str,
    codigo_sigef: str = "SIGEF-1",
    municipios: list[str] | None = None,
    situacao: str = "certificado",
    denominacao: str | None = "Fazenda Teste",
) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO lote_rural
                (id, uf, municipios, codigo_sigef, denominacao, situacao_certificacao,
                 geom_sigef, versao_base_id)
            VALUES (%s, 'RJ', %s, %s, %s, %s, ST_GeomFromText(%s, 4674), %s)
            """,
            (
                id_,
                municipios or ["Cachoeiras de Macacu"],
                codigo_sigef,
                denominacao,
                situacao,
                wkt,
                versao.id,
            ),
        )


class TestLoteEm:
    def test_encontra_o_lote_que_contem_o_ponto(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9))

        resultado = repositorio.lote_em(Coordenada(lat=-22.9, lon=-43.1), versao)

        assert isinstance(resultado, LoteRural)
        assert resultado.lote_id == "RJ-1"
        assert resultado.municipios == ("Cachoeiras de Macacu",)
        assert resultado.perimetro_m > 0
        assert resultado.area.valor > 0

    def test_retorna_sobreposicao_quando_dois_lotes_cobrem_o_mesmo_ponto(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9, lado=0.02))
        _inserir_lote(conexao, versao, id_="RJ-2", wkt=_quadrado_wkt(-43.1, -22.9, lado=0.02))

        resultado = repositorio.lote_em(Coordenada(lat=-22.9, lon=-43.1), versao)

        assert isinstance(resultado, Sobreposicao)
        assert {c.lote_id for c in resultado.candidatos} == {"RJ-1", "RJ-2"}  # type: ignore[union-attr]

    def test_retorna_none_quando_nenhum_lote_cobre_o_ponto(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9))

        resultado = repositorio.lote_em(Coordenada(lat=-20.0, lon=-40.0), versao)

        assert resultado is None


class TestIntersecoesDe:
    def test_retorna_lista_vazia(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9))
        lote = repositorio.lote_em(Coordenada(lat=-22.9, lon=-43.1), versao)
        assert isinstance(lote, LoteRural)

        assert repositorio.intersecoes_de(lote, versao) == []


class TestProvenienciaDe:
    def test_retorna_registro_semeado(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao,
                                           link_oficial)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    Camada.LOTE_RURAL.value,
                    versao.id,
                    "SIGEF/INCRA",
                    date(2026, 8, 1),
                    "https://sigef.incra.gov.br",
                ),
            )

        resultado = repositorio.proveniencia_de(Camada.LOTE_RURAL, versao)

        assert resultado is not None
        assert resultado.fonte == "SIGEF/INCRA"
        assert resultado.data_extracao == date(2026, 8, 1)
        assert resultado.link_oficial == "https://sigef.incra.gov.br"

    def test_retorna_none_quando_nao_ha_stamp(
        self,
        repositorio: RepositorioLotesPostGIS,
        versao: VersaoBase,
    ) -> None:
        resultado = repositorio.proveniencia_de(Camada.LOTE_RURAL, versao)

        assert resultado is None


class TestCoberturaDe:
    def test_reflete_linhas_semeadas(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
    ) -> None:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cobertura (municipio, camada, tem_dado, data_extracao)
                VALUES (%s, %s, %s, %s), (%s, %s, %s, %s)
                """,
                (
                    "Maricá",
                    Camada.INUNDACAO.value,
                    True,
                    date(2026, 8, 1),
                    "Maricá",
                    Camada.UNIDADE_CONSERVACAO.value,
                    False,
                    None,
                ),
            )

        resultado = repositorio.cobertura_de("Maricá")

        por_camada = {item.camada: item for item in resultado}
        assert por_camada[Camada.INUNDACAO].tem_dado is True
        assert por_camada[Camada.INUNDACAO].data_extracao == date(2026, 8, 1)
        assert por_camada[Camada.UNIDADE_CONSERVACAO].tem_dado is False


class TestMunicipioEm:
    def test_levanta_not_implemented_citando_td_001(
        self,
        repositorio: RepositorioLotesPostGIS,
        versao: VersaoBase,
    ) -> None:
        with pytest.raises(NotImplementedError, match="TD-001"):
            repositorio.municipio_em(Coordenada(lat=-22.9, lon=-43.1), versao)

        assert "TD-001" in MENSAGEM_TD_001
