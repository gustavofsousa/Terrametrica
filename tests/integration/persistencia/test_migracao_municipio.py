"""Migração 0008 (malha municipal) e seu rollback manual — spec:mapa-do-lote-rj (T1).

Container PostGIS efêmero próprio: o rollback altera o schema, então não divide o banco
com as outras suítes de persistência.
"""

import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from terrametrica.api.app import criar_app
from terrametrica.persistencia.migrar import DIRETORIO_MIGRACOES, aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
ROLLBACK = DIRETORIO_MIGRACOES / "rollback" / "0008_f113_municipio.down.sql"
QUADRADO = "MULTIPOLYGON(((-43 -22, -42.99 -22, -42.99 -21.99, -43 -21.99, -43 -22)))"


def _garantir_docker_disponivel() -> None:
    try:
        resultado = subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        pytest.fail("Docker não encontrado — instale e rode o Docker antes desta suíte.")
    if resultado.returncode != 0:
        pytest.fail("Docker não está disponível (`docker info` falhou).")


@pytest.fixture
def url_banco() -> Iterator[str]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        url = postgres.get_connection_url(driver=None)
        with psycopg.connect(url) as conn:
            aplicar_migracoes(conn)
        yield url


@pytest.fixture
def conexao(url_banco: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(url_banco) as conn:
        yield conn


def _existe_tabela(conexao: psycopg.Connection, nome: str) -> bool:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{nome}",))
        (existe,) = cursor.fetchone()  # type: ignore[misc]
    return bool(existe)


def _semear_base_com_lote(conexao: psycopg.Connection) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES ('2026-10', %s, 'published')",
            (date(2026, 10, 1),),
        )
        cursor.execute(
            """
            INSERT INTO lote_rural (id, uf, municipios, codigo_sigef, situacao_certificacao,
                                    geom_sigef, versao_base_id)
            VALUES ('L1', 'RJ', ARRAY['Resende'], 'S1', 'certificado',
                    ST_GeomFromText(%s, 4674), '2026-10')
            """,
            (QUADRADO,),
        )
        cursor.execute(
            """
            INSERT INTO restricao (id, tipo, nome, geom, versao_base_id)
            VALUES ('R1', 'app', 'APP', ST_GeomFromText(%s, 4674), '2026-10')
            """,
            (QUADRADO,),
        )
        cursor.execute(
            "INSERT INTO ponteiro_publicado (camada, versao_base_id) VALUES "
            "('lote_rural', '2026-10'), ('municipio', '2026-10')"
        )
        cursor.execute(
            """
            INSERT INTO municipio (codigo, nome, uf, geom, versao_base_id)
            VALUES ('3304201', 'Resende', '33', ST_GeomFromText(%s, 4674), '2026-10')
            """,
            (QUADRADO,),
        )
        cursor.execute(
            "INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao,"
            " link_oficial, sha256)"
            " VALUES ('municipio', '2026-10', 'IBGE', %s, 'https://x', 'abc')",
            (date(2026, 10, 1),),
        )
        cursor.execute(
            "INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao, link_oficial)"
            " VALUES ('lote_rural', '2026-10', 'SIGEF', %s, 'https://y')",
            (date(2026, 10, 1),),
        )
    conexao.commit()


def _contar(conexao: psycopg.Connection, tabela: str) -> int:
    with conexao.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {tabela}")
        (total,) = cursor.fetchone()  # type: ignore[misc]
    return int(total)


def _executar_rollback(conexao: psycopg.Connection) -> None:
    with conexao.cursor() as cursor:
        for comando in ROLLBACK.read_text(encoding="utf-8").split(";"):
            if comando.strip():
                cursor.execute(comando)
    conexao.commit()


def test_mun01_aplicar_duas_vezes_cria_municipio_com_check_de_7_digitos(
    conexao: psycopg.Connection,
) -> None:
    aplicar_migracoes(conexao)  # segunda aplicação: não falha

    assert _existe_tabela(conexao, "municipio")
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM schema_migrations WHERE nome_arquivo = '0008_f113_municipio.sql'"
        )
        assert cursor.fetchone() == (1,)
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES ('v', now(), 'draft')"
        )
        with pytest.raises(psycopg.errors.CheckViolation):
            cursor.execute(
                "INSERT INTO municipio (codigo, nome, uf, geom, versao_base_id) "
                "VALUES ('330420', 'Curto', '33', ST_GeomFromText(%s, 4674), 'v')",
                (QUADRADO,),
            )
    conexao.rollback()


def test_mun09_rollback_remove_so_a_malha_e_preserva_lotes_restricoes_e_ponteiro(
    conexao: psycopg.Connection,
) -> None:
    _semear_base_com_lote(conexao)
    antes = {t: _contar(conexao, t) for t in ("lote_rural", "restricao", "versao_base")}

    _executar_rollback(conexao)

    assert not _existe_tabela(conexao, "municipio")
    assert {t: _contar(conexao, t) for t in antes} == antes
    with conexao.cursor() as cursor:
        cursor.execute("SELECT camada FROM ponteiro_publicado")
        assert cursor.fetchall() == [("lote_rural",)]
        cursor.execute("SELECT camada FROM proveniencia")
        assert cursor.fetchall() == [("lote_rural",)]
        cursor.execute(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'proveniencia' AND column_name = 'sha256'"
        )
        assert cursor.fetchone() == (0,)


def test_mun09_depois_do_rollback_o_dossie_de_um_lote_conhecido_continua_200(
    url_banco: str, conexao: psycopg.Connection
) -> None:
    _semear_base_com_lote(conexao)
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO limite_estado (uf, geom, versao_base_id) "
            "VALUES ('RJ', ST_GeomFromText(%s, 4674), '2026-10')",
            (QUADRADO,),
        )
    conexao.commit()
    _executar_rollback(conexao)

    resposta = TestClient(criar_app(url_banco, acesso_aberto=True)).get(
        "/dossie", params={"lat": -21.995, "lon": -42.995}
    )

    assert resposta.status_code == 200
    assert resposta.json()["lote"]["lote_id"] == "L1"


def test_mun09_depois_do_rollback_a_migracao_aplica_de_novo(conexao: psycopg.Connection) -> None:
    _executar_rollback(conexao)

    aplicar_migracoes(conexao)

    assert _existe_tabela(conexao, "municipio")


def test_mun09_runner_nao_aplica_arquivos_da_pasta_rollback(conexao: psycopg.Connection) -> None:
    assert ROLLBACK.is_file()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT nome_arquivo FROM schema_migrations")
        aplicadas = {linha[0] for linha in cursor.fetchall()}

    assert not any(nome.endswith(".down.sql") for nome in aplicadas)
    assert {p.name for p in Path(DIRETORIO_MIGRACOES).glob("*.sql")} == aplicadas
