"""Prova fim-a-fim HTTP das rotas de auth (Fatia 7, T7) via TestClient + Postgres real.

Sobe um container só com as migrações (não precisa do pipeline de lotes — os fluxos de auth não
tocam o dossiê). Usa os adaptadores Postgres reais para token/credencial/sessão e um enviador fake
que captura o token em claro do link (para simular o clique no magic link). Cobre:

- solicitar: 202 (enviado), 422 (e-mail ruim), 429 (6ª/h), 502 (falha do enviador)
- confirmar: 302 + Set-Cookie (válido) vs 401 (inválido/usado)
- logout: 204 + cookie expirado; sessão invalidada some
"""

import subprocess
from collections.abc import Iterator
from datetime import datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from terrametrica.api.app import criar_app
from terrametrica.persistencia.migrar import aplicar_migracoes
from tests.fakes.auth_fake import FakeEnviadorEmail

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
BASE_URL = "https://app.terrametrica.test"


def _garantir_docker_disponivel() -> None:
    try:
        resultado = subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        pytest.fail("Docker não encontrado — instale e rode o Docker antes desta suíte.")
    if resultado.returncode != 0:
        pytest.fail("Docker não está disponível (`docker info` falhou).")


@pytest.fixture(scope="module")
def url_banco() -> Iterator[str]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        url = postgres.get_connection_url(driver=None)
        with psycopg.connect(url) as conn:
            aplicar_migracoes(conn)
        yield url


@pytest.fixture(autouse=True)
def _limpar(url_banco: str) -> None:
    with psycopg.connect(url_banco) as conn:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE login_token, sessao, credencial_login")
        conn.commit()


def _token_do_link(enviador: FakeEnviadorEmail) -> str:
    _, link = enviador.enviados[-1]
    return link.split("token=")[1]


class TestSolicitar:
    def test_email_valido_devolve_202_e_envia(self, url_banco: str) -> None:
        enviador = FakeEnviadorEmail()
        client = TestClient(criar_app(url_banco, enviador_email=enviador, base_url=BASE_URL))

        resp = client.post("/auth/solicitar", json={"email": "alice@example.com"})

        assert resp.status_code == 202
        assert len(enviador.enviados) == 1

    def test_email_malformado_devolve_422_sem_enviar(self, url_banco: str) -> None:
        enviador = FakeEnviadorEmail()
        client = TestClient(criar_app(url_banco, enviador_email=enviador, base_url=BASE_URL))

        resp = client.post("/auth/solicitar", json={"email": "sem-arroba"})

        assert resp.status_code == 422
        assert enviador.enviados == []

    def test_sexta_solicitacao_devolve_429(self, url_banco: str) -> None:
        enviador = FakeEnviadorEmail()
        client = TestClient(criar_app(url_banco, enviador_email=enviador, base_url=BASE_URL))

        for _ in range(5):
            r = client.post("/auth/solicitar", json={"email": "bob@example.com"})
            assert r.status_code == 202
        resp = client.post("/auth/solicitar", json={"email": "bob@example.com"})

        assert resp.status_code == 429
        assert len(enviador.enviados) == 5

    def test_falha_do_enviador_devolve_502(self, url_banco: str) -> None:
        enviador = FakeEnviadorEmail(falhar=True)
        client = TestClient(criar_app(url_banco, enviador_email=enviador, base_url=BASE_URL))

        resp = client.post("/auth/solicitar", json={"email": "alice@example.com"})

        assert resp.status_code == 502


class TestConfirmar:
    def test_link_valido_devolve_302_e_seta_cookie(self, url_banco: str) -> None:
        enviador = FakeEnviadorEmail()
        client = TestClient(criar_app(url_banco, enviador_email=enviador, base_url=BASE_URL))
        client.post("/auth/solicitar", json={"email": "nova@example.com"})
        token = _token_do_link(enviador)

        resp = client.get("/auth/confirmar", params={"token": token}, follow_redirects=False)

        assert resp.status_code == 302
        set_cookie = resp.headers["set-cookie"]
        assert "sessao=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=lax" in set_cookie

    def test_link_invalido_devolve_401(self, url_banco: str) -> None:
        client = TestClient(
            criar_app(url_banco, enviador_email=FakeEnviadorEmail(), base_url=BASE_URL)
        )

        resp = client.get("/auth/confirmar", params={"token": "nao-existe"}, follow_redirects=False)

        assert resp.status_code == 401

    def test_link_usado_nao_reautentica(self, url_banco: str) -> None:
        enviador = FakeEnviadorEmail()
        client = TestClient(criar_app(url_banco, enviador_email=enviador, base_url=BASE_URL))
        client.post("/auth/solicitar", json={"email": "a@example.com"})
        token = _token_do_link(enviador)

        primeiro = client.get("/auth/confirmar", params={"token": token}, follow_redirects=False)
        segundo = client.get("/auth/confirmar", params={"token": token}, follow_redirects=False)

        assert primeiro.status_code == 302
        assert segundo.status_code == 401  # uso único


class TestLogout:
    def test_logout_devolve_204_e_expira_cookie(self, url_banco: str) -> None:
        enviador = FakeEnviadorEmail()
        client = TestClient(criar_app(url_banco, enviador_email=enviador, base_url=BASE_URL))
        client.post("/auth/solicitar", json={"email": "a@example.com"})
        token = _token_do_link(enviador)
        confirmar = client.get(
            "/auth/confirmar", params={"token": token}, follow_redirects=False
        )
        cookie = confirmar.headers["set-cookie"].split(";")[0]  # sessao=<valor>

        resp = client.post("/auth/logout", headers={"Cookie": cookie})

        assert resp.status_code == 204
        assert 'sessao=""' in resp.headers.get("set-cookie", "") or "sessao=;" in resp.headers.get(
            "set-cookie", ""
        )


class TestSessaoRepoDireto:
    def test_sessao_invalidada_nao_resolve_conta(self, url_banco: str) -> None:
        # Após logout, o hash da sessão some do banco (PAINEL-14). Provado via repo direto.
        from terrametrica.auth.adaptadores import RepositorioSessaoPostgres
        from terrametrica.auth.regras import hash_token

        agora = datetime(2026, 9, 11, 12, 0)
        with psycopg.connect(url_banco) as conn:
            repo = RepositorioSessaoPostgres(conn)
            repo.criar("conta-1", hash_token("sx"), agora + timedelta(days=30))
            assert repo.conta_de_sessao(hash_token("sx"), agora) == "conta-1"
            repo.invalidar(hash_token("sx"))
            assert repo.conta_de_sessao(hash_token("sx"), agora) is None
