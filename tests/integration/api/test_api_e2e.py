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

import math
import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

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
from terrametrica.ingestao.municipios_rj import ingerir_municipios_rj
from terrametrica.ingestao.publicar import publicar_versao
from terrametrica.ingestao.restricao_car import ingerir_app_car, ingerir_reserva_legal_car
from terrametrica.ingestao.restricao_uc import ingerir_uc
from terrametrica.ingestao.sigef import ingerir_sigef
from terrametrica.persistencia.migrar import aplicar_migracoes
from tests.fakes.malha_municipal_fake import malha_sintetica

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
            malha = malha_sintetica(codigos=("3304557", "3300100", "3303500"))
            ingerir_municipios_rj(versao, conexao, ler=lambda: malha)
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


def _vertices(geojson: dict[str, Any]) -> list[list[float]]:
    pontos: list[list[float]] = []

    def descer(no: Any) -> None:
        if isinstance(no, list) and no and isinstance(no[0], float):
            pontos.append(no)
        elif isinstance(no, list):
            for filho in no:
                descer(filho)

    descer(geojson["coordinates"])
    return pontos


# Dentro do RJ e dentro do quadrado sintético "Município 25" (código 3300025), sem lote.
LAT_SEM_LOTE, LON_SEM_LOTE = -22.95, -43.49
# Dentro do RJ (Vale do Paraíba fluminense) e fora de todo quadrado da malha sintética.
LAT_FORA_DA_MALHA, LON_FORA_DA_MALHA = -22.5, -43.7


class TestGeometriaNoDossie:
    """spec:mapa-do-lote-rj — MAPA-06, MAPA-07, MAPA-10, MUN-03."""

    def test_mapa06_200_traz_a_geometria_do_lote_em_lon_lat_com_6_casas(
        self, client: TestClient
    ) -> None:
        resp = client.get("/dossie", params={"lat": LAT_DENTRO, "lon": LON_DENTRO}, headers=CONTA)

        assert resp.status_code == 200
        geometria = resp.json()["lote"]["geometria"]
        assert geometria["type"] in {"Polygon", "MultiPolygon"}
        vertices = _vertices(geometria)
        # SIGEF-001: quadrado [-43.105, -43.095] × [-22.905, -22.895]
        for lon, lat in vertices:
            assert -43.1051 < lon < -43.0949
            assert -22.9051 < lat < -22.8949
            assert len(repr(lon).split(".")[1]) <= 6
            assert len(repr(lat).split(".")[1]) <= 6

    def test_mapa07_409_traz_a_geometria_de_cada_candidato(
        self, client: TestClient, url_banco: str
    ) -> None:
        wkt = (
            "MULTIPOLYGON(((-43.31 -22.86, -43.29 -22.86, -43.29 -22.84, "
            "-43.31 -22.84, -43.31 -22.86)))"
        )
        conexao = psycopg.connect(url_banco)
        try:
            with conexao.cursor() as cursor:
                for lote_id in ("OVL-1", "OVL-2"):
                    cursor.execute(
                        "INSERT INTO lote_rural (id, uf, municipios, codigo_sigef, "
                        "situacao_certificacao, geom_sigef, versao_base_id) VALUES "
                        "(%s, 'RJ', ARRAY['3304557'], %s, 'certificado', "
                        "ST_GeomFromText(%s, 4674), %s)",
                        (lote_id, f"SIGEF-{lote_id}", wkt, VERSAO_ID),
                    )
            conexao.commit()

            resp = client.get("/dossie", params={"lat": -22.85, "lon": -43.30}, headers=CONTA)
        finally:
            with conexao.cursor() as cursor:
                cursor.execute("DELETE FROM lote_rural WHERE id LIKE 'OVL-%'")
            conexao.commit()
            conexao.close()

        assert resp.status_code == 409
        candidatos = resp.json()["candidatos"]
        assert {c["lote_id"] for c in candidatos} == {"OVL-1", "OVL-2"}
        for candidato in candidatos:
            assert candidato["geometria"]["type"] in {"Polygon", "MultiPolygon"}
            assert len(_vertices(candidato["geometria"])) >= 4

    def test_edge_maior_lote_do_sigef_volta_com_a_geometria_completa_sem_simplificar(
        self, client: TestClient, url_banco: str
    ) -> None:
        # 2.301 vértices, como o maior lote do SIGEF RJ (medido): 2.300 distintos + o de fechamento.
        total = 2300
        anel = ", ".join(
            f"{-43.60 + 0.02 * math.cos(2 * math.pi * i / total):.6f} "
            f"{-22.60 + 0.02 * math.sin(2 * math.pi * i / total):.6f}"
            for i in range(total)
        )
        primeiro = anel.split(", ")[0]
        wkt = f"MULTIPOLYGON((({anel}, {primeiro})))"
        conexao = psycopg.connect(url_banco)
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO lote_rural (id, uf, municipios, codigo_sigef, "
                    "situacao_certificacao, geom_sigef, versao_base_id) VALUES "
                    "('GRANDE-1', 'RJ', ARRAY['3304557'], 'SIGEF-GRANDE', 'certificado', "
                    "ST_GeomFromText(%s, 4674), %s)",
                    (wkt, VERSAO_ID),
                )
            conexao.commit()

            resp = client.get("/dossie", params={"lat": -22.60, "lon": -43.60}, headers=CONTA)
        finally:
            with conexao.cursor() as cursor:
                cursor.execute("DELETE FROM lote_rural WHERE id = 'GRANDE-1'")
            conexao.commit()
            conexao.close()

        assert resp.status_code == 200
        assert len(_vertices(resp.json()["lote"]["geometria"])) == 2301

    def test_mun03_404_traz_codigo_e_nome_do_municipio_e_a_cobertura(
        self, client: TestClient
    ) -> None:
        resp = client.get(
            "/dossie", params={"lat": LAT_SEM_LOTE, "lon": LON_SEM_LOTE}, headers=CONTA
        )

        assert resp.status_code == 404
        corpo = resp.json()
        assert corpo["tipo"] == "sem_lote"
        assert corpo["municipio"] == "3300025"
        assert corpo["municipio_nome"] == "Município 25"
        assert isinstance(corpo["cobertura"], list)

    def test_mun03_404_fora_de_todo_municipio_devolve_municipio_nulo_sem_erro(
        self, client: TestClient
    ) -> None:
        resp = client.get(
            "/dossie",
            params={"lat": LAT_FORA_DA_MALHA, "lon": LON_FORA_DA_MALHA},
            headers=CONTA,
        )

        assert resp.status_code == 404
        corpo = resp.json()
        assert corpo["municipio"] is None
        assert corpo["municipio_nome"] is None
        assert corpo["cobertura"] == []

    def test_mapa10_consulta_log_continua_com_as_mesmas_colunas(self, url_banco: str) -> None:
        conexao = psycopg.connect(url_banco)
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'consulta_log'"
                )
                colunas = {linha[0] for linha in cursor.fetchall()}
        finally:
            conexao.close()

        assert colunas == {"id", "ts", "conta_id", "lote_id", "camadas", "latencia_ms"}


class TestRotaMapaContorno:
    """spec:mapa-do-lote-rj — MAPA-04."""

    def test_mapa04_200_com_feature_etag_e_cache_control(self, client: TestClient) -> None:
        resp = client.get("/mapa/contorno")  # pública: sem header de conta

        assert resp.status_code == 200
        corpo = resp.json()
        assert corpo["type"] == "Feature"
        assert corpo["geometry"]["type"] == "MultiPolygon"
        assert resp.headers["ETag"] == f'"{VERSAO_ID}"'
        assert resp.headers["Cache-Control"] == "public, max-age=86400"

    def test_mapa04_if_none_match_igual_devolve_304_sem_corpo(self, client: TestClient) -> None:
        resp = client.get("/mapa/contorno", headers={"If-None-Match": f'"{VERSAO_ID}"'})

        assert resp.status_code == 304
        assert resp.content == b""
        assert resp.headers["ETag"] == f'"{VERSAO_ID}"'

    def test_mapa04_if_none_match_de_outra_versao_devolve_200(self, client: TestClient) -> None:
        resp = client.get("/mapa/contorno", headers={"If-None-Match": '"versao-antiga"'})

        assert resp.status_code == 200


class TestAcessoAberto:
    """AD-014: período sem login — sem sessão nem header, a consulta funciona e é registrada."""

    def test_sem_credenciais_devolve_200_e_loga_conta_anonima_sem_ip(self, url_banco: str) -> None:
        client = TestClient(criar_app(url_banco, acesso_aberto=True))

        resp = client.get("/dossie", params={"lat": LAT_DENTRO, "lon": LON_DENTRO})

        assert resp.status_code == 200
        with psycopg.connect(url_banco) as conexao:
            contas = [
                linha[0]
                for linha in conexao.execute(
                    "SELECT conta_id FROM consulta_log WHERE conta_id LIKE 'anonimo:%'"
                )
            ]
        assert contas
        assert all("testclient" not in conta for conta in contas)

    def test_cota_vale_por_visitante_anonimo(self, url_banco: str) -> None:
        app = criar_app(url_banco, limitador=LimitadorEmMemoria(limite=1), acesso_aberto=True)
        client = TestClient(app)
        p = {"lat": LAT_DENTRO, "lon": LON_DENTRO}

        assert client.get("/dossie", params=p).status_code == 200
        assert client.get("/dossie", params=p).status_code == 429


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


class TestRotaCoberturaEstado:
    """F1.12 — COBPUB-01/02/03/06: agregação pública, sem autenticação."""

    def test_responde_200_sem_header_de_conta(self, client: TestClient) -> None:
        resp = client.get("/cobertura/estado")  # sem X-Conta-Id — COBPUB-01
        assert resp.status_code == 200

    def test_lista_municipio_com_lote_ingerido_e_todas_as_camadas(
        self, client: TestClient
    ) -> None:
        resp = client.get("/cobertura/estado")
        corpo = resp.json()

        municipios = {item["municipio"]: item for item in corpo["municipios"]}
        assert municipios  # COBPUB-02: pelo menos o município do lote SIGEF-001 aparece

        algum_municipio = next(iter(municipios.values()))
        camadas = {c["camada"]: c for c in algum_municipio["cobertura"]}
        assert "app" in camadas  # ingerida no fixture
        assert "corpo_dagua" in camadas  # nunca ingerida — não pode ficar omitida (COBPUB-03)
        assert camadas["corpo_dagua"]["tem_dado"] is False
        assert camadas["corpo_dagua"]["data_extracao"] is None

    def test_mun08_lista_os_92_municipios_com_codigo_e_nome_em_ordem_alfabetica(
        self, client: TestClient
    ) -> None:
        corpo = client.get("/cobertura/estado").json()

        itens = corpo["municipios"]
        assert len(itens) == 92
        assert all(len(item["municipio"]) == 7 for item in itens)
        nomes = [item["municipio_nome"] for item in itens]
        assert nomes == sorted(nomes)
        por_codigo = {item["municipio"]: item["municipio_nome"] for item in itens}
        assert por_codigo["3304557"] == "Município 00"
