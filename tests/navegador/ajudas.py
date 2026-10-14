"""Gestos e leituras do mapa compartilhados pelos testes de navegador."""

from typing import Any

from playwright.sync_api import Page

URL_ESTILO_OPENFREEMAP = "https://tiles.openfreemap.org/styles/positron"


def abrir_mapa(pagina: Page, base_url: str, caminho: str = "/") -> None:
    """Abre a página e espera as camadas do mapa existirem."""
    pagina.goto(f"{base_url}{caminho}")
    pagina.wait_for_selector("html[data-map-ready='true']", state="attached")


def centrar(pagina: Page, lat: float, lon: float, zoom: float = 14) -> None:
    """Põe `[lon, lat]` no centro do mapa, sem animação, e espera o mapa assentar."""
    pagina.evaluate(
        "([lon, lat, zoom]) => __mapa.jumpTo({ center: [lon, lat], zoom })", [lon, lat, zoom]
    )
    esperar_mapa_parado(pagina)


def esperar_mapa_parado(pagina: Page) -> None:
    """Câmera parada e nada carregando. Não espera o evento `idle`: ele não repete se o mapa já está
    ocioso, e o teste ficaria preso."""
    pagina.wait_for_function("() => !__mapa.isMoving() && __mapa.loaded()")


def clicar_no_centro(pagina: Page) -> None:
    caixa = pagina.locator("#mapa canvas").bounding_box()
    assert caixa is not None
    pagina.mouse.click(caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)


def consultar_ponto(pagina: Page, lat: float, lon: float, zoom: float = 14) -> None:
    centrar(pagina, lat, lon, zoom)
    clicar_no_centro(pagina)


def ids_do_lote_selecionado(pagina: Page) -> list[str]:
    ids: list[Any] = pagina.evaluate("() => __mapa.querySourceFeatures('lote').map((f) => f.id)")
    return sorted({str(i) for i in ids})


def ids_dos_candidatos(pagina: Page) -> list[str]:
    ids: list[Any] = pagina.evaluate(
        "() => __mapa.querySourceFeatures('candidatos').map((f) => f.id)"
    )
    return sorted({str(i) for i in ids})


def estado_do_candidato(pagina: Page, lote_id: str) -> dict[str, Any]:
    estado: dict[str, Any] | None = pagina.evaluate(
        "(id) => __mapa.getFeatureState({ source: 'candidatos', id })", lote_id
    )
    return estado or {}
