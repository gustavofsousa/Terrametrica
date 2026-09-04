"""Testes de integração de `publicar_versao` (T13) — guarda de 90% + swap atômico.

Semeia `versao_base`/`limite_estado`/`lote_rural`/`ponteiro_publicado` diretamente via SQL —
não depende de rodar `ingerir_limite_rj`/`ingerir_sigef` (T11/T12) para montar os cenários de
guarda, isolando o teste da regra de publicação da regra de ingestão. Mesmo padrão de container
efêmero de `test_limite_rj.py`/`test_sigef.py`.
"""

import subprocess
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

import terrametrica.ingestao.publicar as publicar_mod
from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.limite_rj import CAMADA_LIMITE_ESTADO
from terrametrica.ingestao.publicar import publicar_versao
from terrametrica.persistencia.migrar import aplicar_migracoes

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


def _quadrado_wkt(lon: float, lat: float, lado: float = 0.01) -> str:
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


def _semear_versao_base(
    conexao: psycopg.Connection, versao_id: str, status: str = "draft"
) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao_id, date(2026, 9, 1), status),
        )


def _semear_limite_estado(conexao: psycopg.Connection, versao_id: str) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO limite_estado (uf, geom, versao_base_id) "
            "VALUES ('RJ', ST_GeomFromText(%s, 4674), %s)",
            (_quadrado_wkt(-43.5, -22.5, lado=1.0), versao_id),
        )


def _semear_lotes(conexao: psycopg.Connection, versao_id: str, quantidade: int) -> None:
    with conexao.cursor() as cursor:
        for indice in range(quantidade):
            wkt = _quadrado_wkt(-43.0 + indice * 0.02, -22.9)
            cursor.execute(
                """
                INSERT INTO lote_rural
                    (id, uf, municipios, codigo_sigef, situacao_certificacao, geom_sigef,
                     versao_base_id)
                VALUES (%s, 'RJ', %s, %s, 'certificado', ST_GeomFromText(%s, 4674), %s)
                """,
                (
                    f"{versao_id}-LOTE-{indice}",
                    ["Maricá"],
                    f"SIGEF-{versao_id}-{indice}",
                    wkt,
                    versao_id,
                ),
            )


def _apontar_ponteiro(conexao: psycopg.Connection, camada: str, versao_id: str) -> None:
    # upsert: `ponteiro_publicado` tem uma única linha por camada em todo o container —
    # compartilhado entre os métodos de teste deste módulo (alguns commitam ao publicar
    # com sucesso), então uma segunda semeadura para a mesma camada precisa substituir, não
    # colidir.
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ponteiro_publicado (camada, versao_base_id) VALUES (%s, %s)
            ON CONFLICT (camada) DO UPDATE SET versao_base_id = EXCLUDED.versao_base_id
            """,
            (camada, versao_id),
        )


def _versao_apontada(conexao: psycopg.Connection, camada: str) -> str | None:
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT versao_base_id FROM ponteiro_publicado WHERE camada = %s", (camada,)
        )
        linha = cursor.fetchone()
    return linha[0] if linha else None


def _status_versao(conexao: psycopg.Connection, versao_id: str) -> str:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT status FROM versao_base WHERE id = %s", (versao_id,))
        (status,) = cursor.fetchone()  # type: ignore[misc]
    return str(status)


class TestPrimeiraPublicacao:
    def test_sem_versao_anterior_sempre_passa_e_publica(
        self, conexao: psycopg.Connection
    ) -> None:
        _semear_versao_base(conexao, "pub1-v1")
        _semear_limite_estado(conexao, "pub1-v1")
        _semear_lotes(conexao, "pub1-v1", 10)

        resultado = publicar_versao(VersaoBase(id="pub1-v1", criada_em=date(2026, 9, 1)), conexao)

        assert resultado.publicada is True
        assert all(c.feicoes_anteriores is None for c in resultado.camadas)
        assert _versao_apontada(conexao, CAMADA_LIMITE_ESTADO) == "pub1-v1"
        assert _versao_apontada(conexao, Camada.LOTE_RURAL.value) == "pub1-v1"
        assert _status_versao(conexao, "pub1-v1") == "published"


class TestReingestaoDentroDaGuarda:
    def test_nova_versao_com_90_por_cento_ou_mais_faz_swap_atomico(
        self, conexao: psycopg.Connection
    ) -> None:
        _semear_versao_base(conexao, "guard90-v1")
        _semear_limite_estado(conexao, "guard90-v1")
        _semear_lotes(conexao, "guard90-v1", 10)
        _apontar_ponteiro(conexao, CAMADA_LIMITE_ESTADO, "guard90-v1")
        _apontar_ponteiro(conexao, Camada.LOTE_RURAL.value, "guard90-v1")

        _semear_versao_base(conexao, "guard90-v2")
        _semear_limite_estado(conexao, "guard90-v2")
        _semear_lotes(conexao, "guard90-v2", 9)  # 90% de 10

        versao_nova = VersaoBase(id="guard90-v2", criada_em=date(2026, 9, 2))
        resultado = publicar_versao(versao_nova, conexao)

        assert resultado.publicada is True
        assert _versao_apontada(conexao, CAMADA_LIMITE_ESTADO) == "guard90-v2"
        assert _versao_apontada(conexao, Camada.LOTE_RURAL.value) == "guard90-v2"
        assert _status_versao(conexao, "guard90-v2") == "published"


class TestReingestaoForaDaGuarda:
    def test_nova_versao_com_menos_de_90_por_cento_e_rejeitada(
        self, conexao: psycopg.Connection
    ) -> None:
        _semear_versao_base(conexao, "guard80-v1")
        _semear_limite_estado(conexao, "guard80-v1")
        _semear_lotes(conexao, "guard80-v1", 10)
        _apontar_ponteiro(conexao, CAMADA_LIMITE_ESTADO, "guard80-v1")
        _apontar_ponteiro(conexao, Camada.LOTE_RURAL.value, "guard80-v1")

        _semear_versao_base(conexao, "guard80-v2")
        _semear_limite_estado(conexao, "guard80-v2")
        _semear_lotes(conexao, "guard80-v2", 8)  # 80% de 10, abaixo do limiar

        versao_nova = VersaoBase(id="guard80-v2", criada_em=date(2026, 9, 2))
        resultado = publicar_versao(versao_nova, conexao)

        assert resultado.publicada is False
        camada_lote = next(c for c in resultado.camadas if c.camada == Camada.LOTE_RURAL.value)
        assert camada_lote.publicada is False
        assert _versao_apontada(conexao, CAMADA_LIMITE_ESTADO) == "guard80-v1"
        assert _versao_apontada(conexao, Camada.LOTE_RURAL.value) == "guard80-v1"
        assert _status_versao(conexao, "guard80-v2") == "draft"


class TestAtomicidadeDoSwap:
    def test_falha_no_meio_do_swap_nao_deixa_ponteiro_em_estado_parcial(
        self, conexao: psycopg.Connection, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _semear_versao_base(conexao, "atomic-v1")
        _semear_limite_estado(conexao, "atomic-v1")
        _semear_lotes(conexao, "atomic-v1", 10)
        _apontar_ponteiro(conexao, CAMADA_LIMITE_ESTADO, "atomic-v1")
        _apontar_ponteiro(conexao, Camada.LOTE_RURAL.value, "atomic-v1")
        conexao.commit()  # baseline durável: precisa sobreviver ao rollback da tentativa v2

        _semear_versao_base(conexao, "atomic-v2")
        _semear_limite_estado(conexao, "atomic-v2")
        _semear_lotes(conexao, "atomic-v2", 10)  # 100% de v1 — guarda passa, chega no laço de swap

        trocar_original = publicar_mod._trocar_ponteiro
        chamadas: list[str] = []

        def trocar_com_falha_na_segunda_camada(
            conexao_: psycopg.Connection, camada: str, versao_id: str
        ) -> None:
            chamadas.append(camada)
            if len(chamadas) == 2:
                raise RuntimeError("falha simulada no meio do swap (DOS-28)")
            trocar_original(conexao_, camada, versao_id)

        monkeypatch.setattr(publicar_mod, "_trocar_ponteiro", trocar_com_falha_na_segunda_camada)

        with pytest.raises(RuntimeError, match="falha simulada"):
            publicar_versao(VersaoBase(id="atomic-v2", criada_em=date(2026, 9, 2)), conexao)

        assert len(chamadas) == 2  # confirma que a falha ocorreu depois da 1ª camada trocada
        assert _versao_apontada(conexao, CAMADA_LIMITE_ESTADO) == "atomic-v1"
        assert _versao_apontada(conexao, Camada.LOTE_RURAL.value) == "atomic-v1"
