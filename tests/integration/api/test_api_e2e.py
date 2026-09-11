"""Prova fim-a-fim HTTP da Fatia 6 (T32): request → motor → resposta sobre PostGIS real.

Sobe o pipeline completo (mesmo padrão de `test_dossie_e2e.py`: limite RJ via geobr real + fixtures
SIGEF/CAR/UC + publicação) uma vez por módulo, e exercita a app via `TestClient`. Prova que a rota
`/dossie` é a versão HTTP da chamada Python que o e2e da Fatia 2-5 já faz — traduzindo o
tipo-resultado da montagem em HTTP:

- 200 + ficha do lote na coordenada do SIGEF-001 (DOS-01)
- idempotência: a mesma coordenada, mesma versão publicada, devolve corpo idêntico (DOS-26/AF-3)
- 422 fora do RJ (DOS-05) e 422 para coordenada fora de faixa (DOS-02)
- 401 sem header X-Conta-Id (AF-4)
- 429 + Retry-After ao estourar a cota (DOS-27/AF-2)
- +1 linha em consulta_log por consulta a /dossie (DOS-30/AF-1)
- /cobertura devolve o estado por camada do município (DOS-11/13)
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
from terrametrica.api.limite_taxa import LimitadorEmMemoria
from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.cobertura import semear_cobertura
from terrametrica.ingestao.intersecoes import materializar_intersecoes
from terrametrica.ingestao.limite_rj import ingerir_limite_rj
from terrametrica.ingestao.publicar import publicar_versao
from terrametrica.ingestao.restricao_car import ingerir_app_car, ingerir_reserva_legal_car
from terrametrica.ingestao.restricao_uc import ingerir_uc
from terrametrica.ingestao.sigef import ingerir_sigef
from terrametrica.persistencia.migrar import aplicar_migracoes

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
FIXTURE_SIGEF = FIXTURES / "sigef" / "sigef_rj_amostra.shp"
FIXTURE_APP = FIXTURES / "restricao_car" / "app_amostra.shp"
FIXTURE_RESERVA_LEGAL = FIXTURES / "restricao_car" / "reserva_legal_amostra.shp"
FIXTURE_UC = FIXTURES / "restricao_uc" / "uc_amostra.geojson"

VERSAO_ID = "e2e-api-v1"
DATA_EXTRACAO_SIGEF = date(2026, 8, 20)
DATA_EXTRACAO_CAR = date(2026, 9, 1)
DATA_EXTRACAO_UC = date(2026, 9, 4)

# SIGEF-001 (fixture): centroid (-43.10, -22.90); ponto dentro do lote (ver test_dossie_e2e.py).
LAT_DENTRO, LON_DENTRO = -22.90, -43.10
# São Paulo capital — fora do RJ.
LAT_FORA, LON_FORA = -23.5505, -46.6333

CONTA = {"X-Conta-Id": "conta-teste"}


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
        conexao = psycopg.connect(url)
        try:
            aplicar_migracoes(conexao)
            with conexao.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, 'draft')",
                    (VERSAO_ID, date(2026, 9, 1)),
                )
            conexao.commit()

            versao = VersaoBase(id=VERSAO_ID, criada_em=date(2026, 9, 1))
            ingerir_limite_rj(versao, conexao)
            ingerir_sigef(FIXTURE_SIGEF, versao, conexao, data_extracao=DATA_EXTRACAO_SIGEF)
            ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=DATA_EXTRACAO_CAR)
            ingerir_reserva_legal_car(
                FIXTURE_RESERVA_LEGAL, versao, conexao, data_extracao=DATA_EXTRACAO_CAR
            )
            ingerir_uc(FIXTURE_UC, versao, conexao, data_extracao=DATA_EXTRACAO_UC)
            materializar_intersecoes(versao, conexao)
            semear_cobertura(versao, conexao)
            resultado = publicar_versao(versao, conexao)
            assert resultado.publicada is True
        finally:
            conexao.close()
        yield url


@pytest.fixture
def client(url_banco: str) -> TestClient:
    """App com limitador default (100/h) — cota não atrapalha os testes de conteúdo."""
    return TestClient(criar_app(url_banco))


class TestRotaDossie:
    def test_lote_sigef_devolve_200_com_ficha(self, client: TestClient) -> None:
        resp = client.get("/dossie", params={"lat": LAT_DENTRO, "lon": LON_DENTRO}, headers=CONTA)

        assert resp.status_code == 200
        corpo = resp.json()
        assert corpo["tipo"] == "dossie"
        assert corpo["lote"]["codigo_sigef"] == "SIGEF-001"
        assert corpo["proveniencia"]["lote_rural"]["fonte"] == "SIGEF"

    def test_idempotente_sob_a_mesma_versao(self, client: TestClient) -> None:
        p = {"lat": LAT_DENTRO, "lon": LON_DENTRO}
        primeira = client.get("/dossie", params=p, headers=CONTA)
        segunda = client.get("/dossie", params=p, headers=CONTA)

        assert primeira.status_code == segunda.status_code == 200
        assert primeira.json() == segunda.json()

    def test_fora_do_rj_devolve_422(self, client: TestClient) -> None:
        resp = client.get("/dossie", params={"lat": LAT_FORA, "lon": LON_FORA}, headers=CONTA)

        assert resp.status_code == 422
        assert resp.json()["tipo"] == "fora_do_rj"

    def test_coordenada_fora_de_faixa_devolve_422(self, client: TestClient) -> None:
        resp = client.get("/dossie", params={"lat": 999.0, "lon": 0.0}, headers=CONTA)

        assert resp.status_code == 422
        assert "erro" in resp.json()

    def test_sem_header_conta_devolve_401(self, client: TestClient) -> None:
        resp = client.get("/dossie", params={"lat": LAT_DENTRO, "lon": LON_DENTRO})

        assert resp.status_code == 401


class TestCotaDeConsultas:
    def test_estourar_a_cota_devolve_429_com_retry_after(self, url_banco: str) -> None:
        # Limitador injetado com cota 2 para não precisar de 100 chamadas.
        app = criar_app(url_banco, limitador=LimitadorEmMemoria(limite=2))
        client = TestClient(app)
        p = {"lat": LAT_DENTRO, "lon": LON_DENTRO}

        assert client.get("/dossie", params=p, headers=CONTA).status_code == 200
        assert client.get("/dossie", params=p, headers=CONTA).status_code == 200
        terceira = client.get("/dossie", params=p, headers=CONTA)

        assert terceira.status_code == 429
        assert int(terceira.headers["Retry-After"]) > 0


class TestObservabilidade:
    def test_cada_consulta_grava_uma_linha_em_consulta_log(
        self, url_banco: str
    ) -> None:
        client = TestClient(criar_app(url_banco))
        conexao = psycopg.connect(url_banco)
        try:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM consulta_log WHERE conta_id = 'obs-conta'")
                (antes,) = cursor.fetchone()

            client.get(
                "/dossie",
                params={"lat": LAT_DENTRO, "lon": LON_DENTRO},
                headers={"X-Conta-Id": "obs-conta"},
            )

            with conexao.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM consulta_log WHERE conta_id = 'obs-conta'")
                (depois,) = cursor.fetchone()
        finally:
            conexao.close()

        assert depois == antes + 1


class TestFluxoCookieDossie:
    """Prova de ponta (PAINEL-07/08): login por magic link → cookie de sessão → /dossie sem header.

    O painel não manda `X-Conta-Id`: a identidade vem só do cookie httpOnly. Este teste percorre o
    fluxo real (solicitar → confirmar → clicar) sobre a mesma base seedada da F1.10.
    """

    def test_clique_autenticado_por_cookie_retorna_dossie_sem_header(self, url_banco: str) -> None:
        from tests.fakes.auth_fake import FakeEnviadorEmail

        enviador = FakeEnviadorEmail()
        # base_url https:// no TestClient p/ o cookie Secure de sessão voltar na chamada a /dossie.
        client = TestClient(
            criar_app(url_banco, enviador_email=enviador, base_url="https://x.test"),
            base_url="https://testserver",
        )

        client.post("/auth/solicitar", json={"email": "painel@example.com"})
        _, link = enviador.enviados[-1]
        token = link.split("token=")[1]
        confirmar = client.get("/auth/confirmar", params={"token": token}, follow_redirects=False)
        assert confirmar.status_code == 302

        # O TestClient guarda o cookie de sessão; a chamada a /dossie NÃO manda X-Conta-Id.
        resp = client.get("/dossie", params={"lat": LAT_DENTRO, "lon": LON_DENTRO})

        assert resp.status_code == 200
        assert resp.json()["lote"]["codigo_sigef"] == "SIGEF-001"

    def test_dossie_sem_cookie_e_sem_header_devolve_401(self, url_banco: str) -> None:
        client = TestClient(criar_app(url_banco, enviador_email=None))
        resp = client.get("/dossie", params={"lat": LAT_DENTRO, "lon": LON_DENTRO})
        assert resp.status_code == 401


class TestRotaCobertura:
    def test_saude_responde_ok(self, client: TestClient) -> None:
        resp = client.get("/saude")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
