"""F1.9 — lote urbano de Niterói sobre PostGIS real: clique → dossiê urbano com proveniência SIGeo.

Fixture sintética em EPSG:31983 (CRS nativo do SIGeo) com as sujeiras do dado real: inscrição "0",
sem endereço, feição sem polígono. A UC de teste (APA) cobre só o lote 1.
"""

import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import (
    Camada,
    Coordenada,
    LoteRural,
    LoteUrbano,
    Sobreposicao,
    TipoRestricao,
    VersaoBase,
)
from terrametrica.ingestao.cobertura import semear_cobertura
from terrametrica.ingestao.intersecoes import materializar_intersecoes
from terrametrica.ingestao.lote_urbano_niteroi import (
    CODIGO_IBGE_NITEROI,
    FONTE_SIGEO,
    ingerir_lotes_niteroi,
)
from terrametrica.ingestao.publicar import publicar_versao
from terrametrica.ingestao.restricao_uc import ingerir_uc
from terrametrica.persistencia.migrar import aplicar_migracoes
from terrametrica.persistencia.repositorio_lotes_postgis import RepositorioLotesPostGIS

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
FIXTURE_LOTES = FIXTURES / "lote_urbano" / "lotes_niteroi_amostra.geojson"
FIXTURE_UC = FIXTURES / "restricao_uc" / "uc_amostra.geojson"
VERSAO = VersaoBase(id="urbano-v1", criada_em=date(2026, 9, 30))
DATA_EXTRACAO = date(2026, 9, 30)

NO_LOTE_COM_UC = Coordenada(lat=-22.901, lon=-43.101)
NO_LOTE_SEM_UC = Coordenada(lat=-22.880, lon=-43.050)
NO_LOTE_SEM_INSCRICAO = Coordenada(lat=-22.900, lon=-43.020)
NO_VAZIO = Coordenada(lat=-22.700, lon=-43.300)


@pytest.fixture(scope="module")
def container() -> Iterator[PostgresContainer]:
    if subprocess.run(["docker", "info"], capture_output=True, check=False).returncode != 0:
        pytest.fail("Docker não está disponível — testes de integração exigem PostGIS efêmero.")
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        with psycopg.connect(postgres.get_connection_url(driver=None)) as conexao:
            aplicar_migracoes(conexao)
        yield postgres


@pytest.fixture(scope="module")
def conexao(container: PostgresContainer) -> Iterator[psycopg.Connection]:
    conexao = psycopg.connect(container.get_connection_url(driver=None))
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
            (VERSAO.id, VERSAO.criada_em),
        )
    conexao.commit()
    relatorio = ingerir_lotes_niteroi(FIXTURE_LOTES, VERSAO, conexao, data_extracao=DATA_EXTRACAO)
    ingerir_uc(FIXTURE_UC, VERSAO, conexao, data_extracao=DATA_EXTRACAO)
    materializar_intersecoes(VERSAO, conexao)
    semear_cobertura(VERSAO, conexao)
    conexao.commit()
    conexao.relatorio = relatorio  # type: ignore[attr-defined]
    yield conexao
    conexao.close()


def test_feicao_sem_poligono_nao_e_gravada_mas_e_contada(conexao: psycopg.Connection) -> None:
    relatorio = conexao.relatorio  # type: ignore[attr-defined]

    assert relatorio.feicoes_gravadas == 3
    assert relatorio.feicoes_sem_geometria == 1


def test_clique_no_lote_devolve_lote_urbano_com_area_em_m2_e_endereco(
    conexao: psycopg.Connection,
) -> None:
    achado = RepositorioLotesPostGIS(conexao).lote_em(NO_LOTE_COM_UC, VERSAO)

    assert isinstance(achado, LoteUrbano)
    assert achado.municipio == CODIGO_IBGE_NITEROI
    assert achado.inscricao_cadastral == "1110560060"
    assert achado.logradouro == "CARAMUJO,DO, 12"
    assert achado.bairro == "CARAMUJO"
    # quadrado de ~0,001° ≈ 100m × 103m
    assert 8_000 < achado.area.valor < 14_000


def test_numero_zero_e_inscricao_zero_do_sigeo_nao_viram_dado(
    conexao: psycopg.Connection,
) -> None:
    sem_numero = RepositorioLotesPostGIS(conexao).lote_em(NO_LOTE_SEM_UC, VERSAO)
    sem_inscricao = RepositorioLotesPostGIS(conexao).lote_em(NO_LOTE_SEM_INSCRICAO, VERSAO)

    assert isinstance(sem_numero, LoteUrbano)
    assert sem_numero.logradouro == "DAS FLORES"
    assert isinstance(sem_inscricao, LoteUrbano)
    assert sem_inscricao.inscricao_cadastral is None
    assert sem_inscricao.logradouro is None


def test_clique_fora_de_qualquer_lote_devolve_none(conexao: psycopg.Connection) -> None:
    assert RepositorioLotesPostGIS(conexao).lote_em(NO_VAZIO, VERSAO) is None


def test_uc_cruza_o_lote_urbano_e_so_o_lote_que_ela_toca(conexao: psycopg.Connection) -> None:
    repo = RepositorioLotesPostGIS(conexao)
    com_uc = repo.lote_em(NO_LOTE_COM_UC, VERSAO)
    sem_uc = repo.lote_em(NO_LOTE_SEM_UC, VERSAO)
    assert com_uc is not None and sem_uc is not None

    intersecoes = repo.intersecoes_de(com_uc, VERSAO)  # type: ignore[arg-type]

    assert [i.tipo for i in intersecoes] == [TipoRestricao.UNIDADE_CONSERVACAO]
    assert repo.intersecoes_de(sem_uc, VERSAO) == []  # type: ignore[arg-type]


def test_proveniencia_da_camada_urbana_carrega_a_atribuicao_exigida_pela_licenca(
    conexao: psycopg.Connection,
) -> None:
    proveniencia = RepositorioLotesPostGIS(conexao).proveniencia_de(Camada.LOTE_URBANO, VERSAO)

    assert proveniencia is not None
    assert proveniencia.fonte == FONTE_SIGEO
    assert "Niter" in proveniencia.fonte
    assert proveniencia.data_extracao == DATA_EXTRACAO


def test_cobertura_declara_niteroi_com_lote_urbano_e_uc(conexao: psycopg.Connection) -> None:
    cobertura = {
        c.camada: c for c in RepositorioLotesPostGIS(conexao).cobertura_de(CODIGO_IBGE_NITEROI)
    }

    assert cobertura[Camada.LOTE_URBANO].tem_dado is True
    assert cobertura[Camada.UNIDADE_CONSERVACAO].tem_dado is True


# Quadrado de ±0,0002° centrado no lote urbano 3 (que tem ±0,0005°): cabe inteiro dentro dele.
_QUADRADO_DENTRO_DO_LOTE_3 = (
    "POLYGON((-43.0202 -22.9002, -43.0198 -22.9002, -43.0198 -22.8998, "
    "-43.0202 -22.8998, -43.0202 -22.9002))"
)


def test_clique_em_lote_urbano_e_rural_ao_mesmo_tempo_exige_escolha(
    conexao: psycopg.Connection,
) -> None:
    """URB-02: nenhuma das naturezas esconde a outra — vira `Sobreposicao` (DOS-06)."""
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO lote_rural (id, uf, municipios, codigo_sigef, situacao_certificacao, "
            "geom_sigef, versao_base_id) VALUES ('RURAL-SOBRE-URBANO', 'RJ', %s, 'SIGEF-X', "
            "'certificado', ST_Multi(ST_GeomFromText(%s, 4674)), %s)",
            ([CODIGO_IBGE_NITEROI], _QUADRADO_DENTRO_DO_LOTE_3, VERSAO.id),
        )
    conexao.commit()
    try:
        achado = RepositorioLotesPostGIS(conexao).lote_em(NO_LOTE_SEM_INSCRICAO, VERSAO)
    finally:
        with conexao.cursor() as cursor:
            cursor.execute("DELETE FROM lote_rural WHERE id = 'RURAL-SOBRE-URBANO'")
        conexao.commit()

    assert isinstance(achado, Sobreposicao)
    naturezas = {type(candidato) for candidato in achado.candidatos}
    assert naturezas == {LoteRural, LoteUrbano}


def test_reserva_legal_do_car_nunca_e_materializada_para_lote_urbano(
    conexao: psycopg.Connection,
) -> None:
    """URB-05 (cláusula APP/RL): CAR é cadastro rural; lote urbano só recebe restrições comuns."""
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO restricao (id, tipo, nome, geom, versao_base_id) VALUES "
            "('RL-SOBRE-URBANO', 'reserva_legal', 'RL de teste', "
            "ST_Multi(ST_GeomFromText(%s, 4674)), %s)",
            (_QUADRADO_DENTRO_DO_LOTE_3, VERSAO.id),
        )
    conexao.commit()
    try:
        materializar_intersecoes(VERSAO, conexao)
        conexao.commit()
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM intersecao_materializada "
                "WHERE restricao_id = 'RL-SOBRE-URBANO'"
            )
            (pares,) = cursor.fetchone()  # type: ignore[misc]
    finally:
        with conexao.cursor() as cursor:
            cursor.execute("DELETE FROM restricao WHERE id = 'RL-SOBRE-URBANO'")
        conexao.commit()

    assert pares == 0


def test_guarda_de_publicacao_barra_versao_que_perde_lotes_urbanos(
    container: PostgresContainer,
) -> None:
    """URB-08: `lote_urbano` participa da guarda de 90% (AD-008) — versão nova com menos de 90%
    dos lotes da publicada não troca o ponteiro."""
    with psycopg.connect(container.get_connection_url(driver=None)) as conn:
        for versao_id, lotes in (("guarda-v1", 10), ("guarda-v2", 5)):
            conn.execute(
                "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
                (versao_id, date(2026, 9, 30)),
            )
            for n in range(lotes):
                conn.execute(
                    "INSERT INTO lote_urbano (id, municipio, geom, versao_base_id) "
                    "VALUES (%s, %s, ST_Multi(ST_GeomFromText(%s, 4674)), %s)",
                    (f"niteroi:g{n}", CODIGO_IBGE_NITEROI, _QUADRADO_DENTRO_DO_LOTE_3, versao_id),
                )
        conn.commit()

        primeira = publicar_versao(VersaoBase(id="guarda-v1", criada_em=date(2026, 9, 30)), conn)
        segunda = publicar_versao(VersaoBase(id="guarda-v2", criada_em=date(2026, 9, 30)), conn)

    assert all(c.publicada for c in primeira.camadas)
    urbano = next(c for c in segunda.camadas if c.camada == Camada.LOTE_URBANO.value)
    assert urbano.publicada is False
    assert (urbano.feicoes_novas, urbano.feicoes_anteriores) == (5, 10)
