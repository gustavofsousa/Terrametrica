"""Harness dos testes de navegador (AD-017): PostGIS + app real + Chromium, sem rede de produto.

Sobe um container PostGIS efêmero, semeia a base (`semente.py`), serve a app FastAPI com o front
estático numa porta livre (uvicorn em thread) e entrega ao teste uma `pagina` do Playwright cujas
rotas externas estão sob controle: fontes bloqueadas e o estilo do OpenFreeMap trocado por um
estilo mínimo local. O MapLibre vem do unpkg (única saída para a rede permitida).

Exige Docker e `playwright install chromium` (ver `docs/DEV-SETUP.md`).
"""

import json
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import uvicorn
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import BrowserContext, Page, Route
from testcontainers.community.postgres import PostgresContainer

from terrametrica.api.app import criar_app
from terrametrica.api.configuracao import DIRETORIO_APP_PADRAO
from terrametrica.api.limite_taxa import LimitadorEmMemoria
from tests.navegador.semente import semear_base

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
URL_ESTILO_OPENFREEMAP = "https://tiles.openfreemap.org/styles/positron"
HOSTS_BLOQUEADOS = ("fonts.googleapis.com", "fonts.gstatic.com")

# Estilo mínimo: fundo liso e uma fonte vazia só para carregar a atribuição do OpenFreeMap.
ESTILO_MINIMO: dict[str, Any] = {
    "version": 8,
    "sources": {
        "openmaptiles": {
            "type": "geojson",
            "data": {"type": "FeatureCollection", "features": []},
            "attribution": (
                '<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> '
                '© <a href="https://www.openmaptiles.org/" target="_blank">OpenMapTiles</a> '
                "Data from "
                '<a href="https://www.openstreetmap.org/copyright" target="_blank">'
                "OpenStreetMap</a>"
            ),
        }
    },
    "layers": [
        {"id": "fundo", "type": "background", "paint": {"background-color": "#f2efe9"}},
        {"id": "vazio", "type": "fill", "source": "openmaptiles", "paint": {"fill-color": "#fff"}},
    ],
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Todo teste desta pasta é de navegador; a suíte padrão o deixa de fora (addopts)."""
    for item in items:
        if "tests/navegador" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.navegador)


def _garantir_docker_disponivel() -> None:
    try:
        resultado = subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        pytest.fail("Docker não encontrado — instale e rode o Docker antes desta suíte.")
    if resultado.returncode != 0:
        pytest.fail("Docker não está disponível (`docker info` falhou).")


def _porta_livre() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def url_banco() -> Iterator[str]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        url = postgres.get_connection_url(driver=None)
        semear_base(url)
        yield url


@pytest.fixture(scope="session")
def base_url(url_banco: str) -> Iterator[str]:
    """Origem da app (API + front estático, mesma origem como no deploy — AD-013)."""
    app = criar_app(url_banco, acesso_aberto=True, limitador=LimitadorEmMemoria(limite=100_000))
    # INVARIANT: montado depois das rotas da API, que têm precedência sobre os arquivos.
    app.mount("/", StaticFiles(directory=DIRETORIO_APP_PADRAO, html=True), name="front")
    porta = _porta_livre()
    servidor = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning")
    )
    thread = threading.Thread(target=servidor.run, daemon=True)
    thread.start()
    origem = f"http://127.0.0.1:{porta}"
    for _ in range(100):
        try:
            if httpx.get(f"{origem}/saude", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        pytest.fail("o servidor uvicorn do teste de navegador não subiu em 10 s")
    yield origem
    servidor.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, Any]) -> dict[str, Any]:
    """WebGL em software (SwiftShader): o MapLibre precisa de WebGL, e o CI não tem GPU."""
    return {
        **browser_type_launch_args,
        "args": ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
    }


def _rotear_externos(contexto: BrowserContext) -> None:
    def bloquear(rota: Route) -> None:
        rota.abort()

    def estilo_minimo(rota: Route) -> None:
        rota.fulfill(
            status=200,
            content_type="application/json",
            headers={"access-control-allow-origin": "*"},
            body=json.dumps(ESTILO_MINIMO),
        )

    for host in HOSTS_BLOQUEADOS:
        contexto.route(f"https://{host}/**", bloquear)
    contexto.route(URL_ESTILO_OPENFREEMAP, estilo_minimo)


@pytest.fixture
def pagina(context: BrowserContext, base_url: str) -> Iterator[Page]:
    """Página com as rotas externas sob controle; `pagina.goto("/")` abre a app."""
    _rotear_externos(context)
    pagina = context.new_page()
    yield pagina
    pagina.close()


@pytest.fixture
def requisicoes(pagina: Page) -> list[str]:
    """URLs de todas as requisições que a página faz, na ordem."""
    urls: list[str] = []
    pagina.on("request", lambda requisicao: urls.append(requisicao.url))
    return urls
