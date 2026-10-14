"""Smoke do harness de navegador — spec:mapa-do-lote-rj (T19, AD-017)."""

from playwright.sync_api import Page, expect


def test_ad017_cobertura_publica_abre_com_a_tabela_dos_92_municipios(
    pagina: Page, base_url: str
) -> None:
    pagina.goto(f"{base_url}/cobertura.html")

    linhas = pagina.locator("table.tabela-cobertura tbody tr")
    expect(linhas).to_have_count(92)
    expect(linhas.first).to_contain_text("Município")
