"""Testes de integração dos adaptadores de auth (Fatia 7, T5) contra Postgres real.

Sobe um container PostGIS efêmero, aplica migrações (0006 inclusa) e exercita os repositórios
contra o banco — sem mocks de banco. Prova os caminhos-chave: consumir atômico (uso único à prova
de corrida), contagem na janela do rate limit, ciclo de vida da sessão (criar/ler/expirar/invalidar)
e o upsert de credencial. O `EnviadorResend` é testado com `httpx.MockTransport` (sem rede real).
"""

import subprocess
from collections.abc import Iterator
from datetime import datetime, timedelta

import httpx
import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.auth.adaptadores import (
    EnviadorResend,
    RepositorioCredencialPostgres,
    RepositorioSessaoPostgres,
    RepositorioTokenPostgres,
)
from terrametrica.auth.regras import Email, hash_token
from terrametrica.dominio.modelos import PapelConta
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
AGORA = datetime(2026, 9, 11, 12, 0)


def _garantir_docker_disponivel() -> None:
    try:
        resultado = subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        pytest.fail("Docker não encontrado — instale e rode o Docker antes desta suíte.")
    if resultado.returncode != 0:
        pytest.fail("Docker não está disponível (`docker info` falhou).")


@pytest.fixture(scope="module")
def conexao() -> Iterator[psycopg.Connection]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        url = postgres.get_connection_url(driver=None)
        with psycopg.connect(url) as conn:
            aplicar_migracoes(conn)
            yield conn


@pytest.fixture(autouse=True)
def _limpar_tabelas(conexao: psycopg.Connection) -> None:
    with conexao.cursor() as cursor:
        cursor.execute("TRUNCATE login_token, sessao, credencial_login")
    conexao.commit()


class TestRepositorioToken:
    def test_consumir_token_valido_devolve_registro_e_marca_usado(
        self, conexao: psycopg.Connection
    ) -> None:
        repo = RepositorioTokenPostgres(conexao)
        h = hash_token("tok-1")
        repo.salvar(h, Email("a@b.com"), AGORA + timedelta(minutes=15))

        registro = repo.consumir(h, AGORA)

        assert registro is not None
        assert registro.email.valor == "a@b.com"

    def test_consumir_e_atomico_segundo_consumo_devolve_none(
        self, conexao: psycopg.Connection
    ) -> None:
        repo = RepositorioTokenPostgres(conexao)
        h = hash_token("tok-2")
        repo.salvar(h, Email("a@b.com"), AGORA + timedelta(minutes=15))

        primeiro = repo.consumir(h, AGORA)
        segundo = repo.consumir(h, AGORA)

        assert primeiro is not None
        assert segundo is None  # uso único: o token já foi marcado usado

    def test_consumir_token_expirado_devolve_none(self, conexao: psycopg.Connection) -> None:
        repo = RepositorioTokenPostgres(conexao)
        h = hash_token("tok-3")
        repo.salvar(h, Email("a@b.com"), AGORA - timedelta(seconds=1))

        assert repo.consumir(h, AGORA) is None

    def test_contar_na_janela_conta_so_apos_desde_e_por_email(
        self, conexao: psycopg.Connection
    ) -> None:
        repo = RepositorioTokenPostgres(conexao)
        # 3 tokens do mesmo e-mail (criado_em = now() no insert), 1 de outro e-mail.
        for i in range(3):
            repo.salvar(hash_token(f"a{i}"), Email("a@b.com"), AGORA + timedelta(minutes=15))
        repo.salvar(hash_token("z"), Email("z@b.com"), AGORA + timedelta(minutes=15))

        # janela ampla (última hora a partir do futuro) pega os 3 de a@b.com, não os de z@b.com.
        desde = datetime.now() - timedelta(hours=1)
        assert repo.contar_na_janela(Email("a@b.com"), desde) == 3
        assert repo.contar_na_janela(Email("z@b.com"), desde) == 1


class TestRepositorioCredencial:
    def test_email_novo_nao_tem_conta(self, conexao: psycopg.Connection) -> None:
        repo = RepositorioCredencialPostgres(conexao)
        assert repo.conta_de_email(Email("novo@b.com")) is None

    def test_criar_e_recuperar_conta(self, conexao: psycopg.Connection) -> None:
        repo = RepositorioCredencialPostgres(conexao)
        conta_id = repo.criar_conta_para_email(Email("x@b.com"), PapelConta.CONSULTA)

        assert conta_id
        assert repo.conta_de_email(Email("x@b.com")) == conta_id


class TestRepositorioSessao:
    def test_criar_e_ler_sessao_valida(self, conexao: psycopg.Connection) -> None:
        repo = RepositorioSessaoPostgres(conexao)
        h = hash_token("sess-1")
        repo.criar("conta-1", h, AGORA + timedelta(days=30))

        assert repo.conta_de_sessao(h, AGORA) == "conta-1"

    def test_sessao_expirada_nao_e_lida(self, conexao: psycopg.Connection) -> None:
        repo = RepositorioSessaoPostgres(conexao)
        h = hash_token("sess-2")
        repo.criar("conta-1", h, AGORA - timedelta(seconds=1))

        assert repo.conta_de_sessao(h, AGORA) is None

    def test_invalidar_remove_sessao_e_e_idempotente(self, conexao: psycopg.Connection) -> None:
        repo = RepositorioSessaoPostgres(conexao)
        h = hash_token("sess-3")
        repo.criar("conta-1", h, AGORA + timedelta(days=30))

        repo.invalidar(h)
        repo.invalidar(h)  # segundo invalidar não deve levantar

        assert repo.conta_de_sessao(h, AGORA) is None


class TestEnviadorResend:
    def test_envia_chama_resend_com_destinatario_e_link(self) -> None:
        capturado: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            capturado["url"] = str(request.url)
            capturado["body"] = request.content.decode()
            return httpx.Response(200, json={"id": "email-1"})

        cliente = httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.resend.com"
        )
        enviador = EnviadorResend("chave", "noreply@terrametrica.xyz", transporte=cliente)

        enviador.enviar_magic_link(Email("dest@b.com"), "https://app.x/auth/confirmar?token=abc")

        assert "/emails" in str(capturado["url"])
        assert "dest@b.com" in str(capturado["body"])
        assert "token=abc" in str(capturado["body"])

    def test_falha_do_resend_propaga_excecao(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"erro": "indisponível"})

        cliente = httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.resend.com"
        )
        enviador = EnviadorResend("chave", "noreply@terrametrica.xyz", transporte=cliente)

        with pytest.raises(httpx.HTTPStatusError):
            enviador.enviar_magic_link(Email("dest@b.com"), "https://app.x/link")
