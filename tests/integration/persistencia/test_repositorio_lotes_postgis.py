"""Testes de integração do adapter `RepositorioLotesPostGIS` (T9).

Sobe um container PostGIS efêmero (`testcontainers`) uma vez por módulo e aplica as
migrações da Fatia 2 (schema + índices GiST). Cada teste roda numa transação própria,
semeando dados via SQL direto e revertendo no teardown — a ingestão real (T12) é fora do
escopo desta fatia; aqui só validamos o contrato do Protocol `RepositorioLotes` contra o
schema real (mesmos ramos do fake em memória de T5, exceto TD-001).
"""

import json
import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import (
    Camada,
    CoberturaCamada,
    Coordenada,
    LoteRural,
    Municipio,
    Sobreposicao,
    TipoRestricao,
    VersaoBase,
)
from terrametrica.persistencia import repositorio_lotes_postgis as repositorio_postgis
from terrametrica.persistencia.migrar import aplicar_migracoes
from terrametrica.persistencia.repositorio_lotes_postgis import (
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


def _inserir_restricao(
    conexao: psycopg.Connection,
    versao: VersaoBase,
    *,
    id_: str,
    tipo: str,
    nome: str,
    categoria: str | None,
    wkt: str,
) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO restricao (id, tipo, nome, categoria, geom, versao_base_id)
            VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4674), %s)
            """,
            (id_, tipo, nome, categoria, wkt, versao.id),
        )


def _inserir_intersecao_materializada(
    conexao: psycopg.Connection,
    versao: VersaoBase,
    *,
    lote_id: str,
    restricao_id: str,
    area_m2: float,
) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO intersecao_materializada
                (lote_id, restricao_id, area_intersecao_m2, versao_base_id)
            VALUES (%s, %s, %s, %s)
            """,
            (lote_id, restricao_id, area_m2, versao.id),
        )


class TestIntersecoesDe:
    def test_retorna_lista_vazia_quando_nada_foi_materializado(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9))
        lote = repositorio.lote_em(Coordenada(lat=-22.9, lon=-43.1), versao)
        assert isinstance(lote, LoteRural)

        assert repositorio.intersecoes_de(lote, versao) == []

    def test_retorna_intersecoes_materializadas_do_lote(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9))
        _inserir_restricao(
            conexao,
            versao,
            id_="app-1",
            tipo=TipoRestricao.APP.value,
            nome="Area de Preservacao Permanente em area consolidada",
            categoria="APP_AREA_AC",
            wkt=_quadrado_wkt(-43.1, -22.9, lado=0.005),
        )
        _inserir_intersecao_materializada(
            conexao, versao, lote_id="RJ-1", restricao_id="app-1", area_m2=12345.0
        )

        lote = repositorio.lote_em(Coordenada(lat=-22.9, lon=-43.1), versao)
        assert isinstance(lote, LoteRural)

        (item,) = repositorio.intersecoes_de(lote, versao)
        assert item.tipo is TipoRestricao.APP
        assert item.nome == "Area de Preservacao Permanente em area consolidada"
        assert item.categoria == "APP_AREA_AC"
        assert item.area_intersecao.valor == 12345.0
        assert item.grau_suscetibilidade is None

    def test_nao_mistura_intersecoes_de_outro_lote(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9))
        _inserir_lote(
            conexao, versao, id_="RJ-2", wkt=_quadrado_wkt(-44.0, -23.0), codigo_sigef="SIGEF-2"
        )
        _inserir_restricao(
            conexao,
            versao,
            id_="rl-1",
            tipo=TipoRestricao.RESERVA_LEGAL.value,
            nome="Reserva Legal Proposta",
            categoria="ARL_PROPOSTA",
            wkt=_quadrado_wkt(-44.0, -23.0, lado=0.005),
        )
        _inserir_intersecao_materializada(
            conexao, versao, lote_id="RJ-2", restricao_id="rl-1", area_m2=500.0
        )

        lote_rj1 = repositorio.lote_em(Coordenada(lat=-22.9, lon=-43.1), versao)
        assert isinstance(lote_rj1, LoteRural)

        assert repositorio.intersecoes_de(lote_rj1, versao) == []


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


class TestCoberturaDeTodos:
    def test_agrega_todos_os_municipios_em_ordem_alfabetica(
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
                    "Niterói",
                    Camada.APP.value,
                    True,
                    date(2026, 8, 1),
                    "Angra dos Reis",
                    Camada.UNIDADE_CONSERVACAO.value,
                    False,
                    None,
                ),
            )

        resultado = repositorio.cobertura_de_todos()

        municipios = [item.municipio for item in resultado]
        assert municipios == ["Angra dos Reis", "Niterói"]  # COBPUB-02: ordem alfabética

        angra = resultado[0]
        assert angra.camadas == (
            CoberturaCamada(camada=Camada.UNIDADE_CONSERVACAO, tem_dado=False, data_extracao=None),
        )

        niteroi = resultado[1]
        assert niteroi.camadas == (
            CoberturaCamada(camada=Camada.APP, tem_dado=True, data_extracao=date(2026, 8, 1)),
        )

    def test_base_vazia_devolve_lista_vazia(
        self,
        repositorio: RepositorioLotesPostGIS,
    ) -> None:
        assert repositorio.cobertura_de_todos() == []  # COBPUB-06


def _inserir_municipio(
    conexao: psycopg.Connection, versao: VersaoBase, *, codigo: str, nome: str, wkt: str
) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO municipio (codigo, nome, uf, geom, versao_base_id) "
            "VALUES (%s, %s, '33', ST_GeomFromText(%s, 4674), %s)",
            (codigo, nome, wkt, versao.id),
        )


class TestMunicipioEm:
    """spec:mapa-do-lote-rj — MUN-02 (fecha TD-001)."""

    PONTO = Coordenada(lat=-22.9, lon=-43.1)

    def test_mun02_ponto_dentro_do_municipio_devolve_codigo_e_nome(
        self,
        conexao: psycopg.Connection,
        repositorio: RepositorioLotesPostGIS,
        versao: VersaoBase,
    ) -> None:
        _inserir_municipio(
            conexao, versao, codigo="3300100", nome="Município A", wkt=_quadrado_wkt(-43.1, -22.9)
        )
        _inserir_municipio(
            conexao, versao, codigo="3300200", nome="Município B", wkt=_quadrado_wkt(-42.0, -22.9)
        )

        assert repositorio.municipio_em(self.PONTO, versao) == Municipio(
            codigo="3300100", nome="Município A"
        )

    def test_mun02_ponto_no_mar_devolve_none(
        self,
        conexao: psycopg.Connection,
        repositorio: RepositorioLotesPostGIS,
        versao: VersaoBase,
    ) -> None:
        _inserir_municipio(
            conexao, versao, codigo="3300100", nome="Município A", wkt=_quadrado_wkt(-43.1, -22.9)
        )

        assert repositorio.municipio_em(Coordenada(lat=-25.0, lon=-40.0), versao) is None

    def test_mun02_mesma_coordenada_em_duas_versoes_devolve_o_municipio_de_cada_uma(
        self,
        conexao: psycopg.Connection,
        repositorio: RepositorioLotesPostGIS,
        versao: VersaoBase,
    ) -> None:
        outra = VersaoBase(id="2026-10", criada_em=date(2026, 10, 1))
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
                (outra.id, outra.criada_em),
            )
        _inserir_municipio(
            conexao, versao, codigo="3300100", nome="Município A", wkt=_quadrado_wkt(-43.1, -22.9)
        )
        _inserir_municipio(
            conexao, outra, codigo="3300200", nome="Município B", wkt=_quadrado_wkt(-43.1, -22.9)
        )

        assert repositorio.municipio_em(self.PONTO, versao) == Municipio("3300100", "Município A")
        assert repositorio.municipio_em(self.PONTO, outra) == Municipio("3300200", "Município B")

    def test_mun02_mensagem_do_td_001_foi_removida_do_adapter(self) -> None:
        assert not hasattr(repositorio_postgis, "MENSAGEM_TD_001")


def _vertices(geojson: dict[str, object]) -> list[list[float]]:
    """Todos os pontos `[lon, lat]` de um (Multi)Polygon GeoJSON."""
    pontos: list[list[float]] = []

    def descer(no: object) -> None:
        if isinstance(no, list) and no and isinstance(no[0], float):
            pontos.append(no)
        elif isinstance(no, list):
            for filho in no:
                descer(filho)

    descer(geojson["coordinates"])
    return pontos


class TestGeometriasDe:
    """spec:mapa-do-lote-rj — MAPA-06, MAPA-07."""

    def test_mapa06_lote_rural_e_urbano_na_mesma_chamada_com_lon_lat_e_6_casas(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(
            conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1234567891, -22.9876543219)
        )
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO lote_urbano (id, municipio, geom, versao_base_id) "
                "VALUES ('niteroi:7', '3303302', ST_GeomFromText(%s, 4674), %s)",
                (_quadrado_wkt(-43.05, -22.9), versao.id),
            )

        geometrias = repositorio.geometrias_de(["RJ-1", "niteroi:7"], versao)

        assert set(geometrias) == {"RJ-1", "niteroi:7"}
        assert geometrias["RJ-1"]["type"] == "MultiPolygon"
        assert geometrias["niteroi:7"]["type"] == "MultiPolygon"
        assert "crs" not in geometrias["RJ-1"]
        for geometria in geometrias.values():
            lon, lat = _vertices(geometria)[0]
            assert lon < -40
            assert lat > -24
        for lon, lat in _vertices(geometrias["RJ-1"]):
            assert len(repr(lon).split(".")[1]) <= 6
            assert len(repr(lat).split(".")[1]) <= 6

    def test_mapa06_id_inexistente_fica_fora_do_resultado_sem_erro(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        _inserir_lote(conexao, versao, id_="RJ-1", wkt=_quadrado_wkt(-43.1, -22.9))

        geometrias = repositorio.geometrias_de(["RJ-1", "NAO-EXISTE"], versao)

        assert set(geometrias) == {"RJ-1"}

    def test_mapa06_lista_vazia_devolve_dict_vazio(
        self, repositorio: RepositorioLotesPostGIS, versao: VersaoBase
    ) -> None:
        assert repositorio.geometrias_de([], versao) == {}


class TestContornoEstado:
    """spec:mapa-do-lote-rj — MAPA-04."""

    def test_mapa04_contorno_e_multipolygon_valido_com_menos_vertices_que_o_original(
        self,
        repositorio: RepositorioLotesPostGIS,
        conexao: psycopg.Connection,
        versao: VersaoBase,
    ) -> None:
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO limite_estado (uf, geom, versao_base_id) VALUES "
                "('RJ', ST_Multi(ST_SetSRID(ST_Buffer(ST_MakePoint(-43.0, -22.5), 0.5, "
                "'quad_segs=200'), 4674)), %s)",
                (versao.id,),
            )
            cursor.execute(
                "SELECT ST_NPoints(geom) FROM limite_estado WHERE versao_base_id = %s",
                (versao.id,),
            )
            (vertices_originais,) = cursor.fetchone()  # type: ignore[misc]

        contorno = repositorio.contorno_estado(versao)

        assert contorno is not None
        assert contorno["type"] == "MultiPolygon"
        assert 4 <= len(_vertices(contorno)) < vertices_originais
        with conexao.cursor() as cursor:
            cursor.execute("SELECT ST_IsValid(ST_GeomFromGeoJSON(%s))", (json.dumps(contorno),))
            assert cursor.fetchone() == (True,)

    def test_mapa04_versao_sem_limite_devolve_none(
        self, repositorio: RepositorioLotesPostGIS, versao: VersaoBase
    ) -> None:
        assert repositorio.contorno_estado(versao) is None
