"""O mapa do painel no navegador — spec:mapa-do-lote-rj (T20: MAPA-01..05, MAPA-08)."""

from playwright.sync_api import Page, Route, expect

from tests.navegador.ajudas import (
    URL_ESTILO_OPENFREEMAP,
    abrir_mapa,
    centrar,
    clicar_no_centro,
    consultar_ponto,
    esperar_mapa_parado,
    estado_do_candidato,
    ids_do_lote_selecionado,
    ids_dos_candidatos,
)
from tests.navegador.semente import (
    IDS_SOBREPOSTOS,
    PONTO_FORA_DO_RJ,
    PONTO_LOTE,
    PONTO_SOBREPOSTO,
)

BBOX_RJ = {"oeste": -44.9, "sul": -23.4, "leste": -40.9, "norte": -20.7}


def _luminancia(cor: tuple[float, float, float]) -> float:
    def canal(valor: float) -> float:
        v = valor / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(c) for c in cor)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    clara, escura = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (clara + 0.05) / (escura + 0.05)


def _rgb(texto: str) -> tuple[float, float, float, float]:
    """`rgb(1, 2, 3)` ou `rgba(1, 2, 3, .5)` → (r, g, b, alfa)."""
    numeros = [float(n) for n in texto[texto.index("(") + 1 : texto.index(")")].split(",")]
    return (*numeros[:3], numeros[3] if len(numeros) == 4 else 1.0)  # type: ignore[return-value]


class TestMapaBase:
    def test_mapa01_nenhuma_requisicao_vai_ao_tile_server_do_osm(
        self, pagina: Page, base_url: str, requisicoes: list[str]
    ) -> None:
        abrir_mapa(pagina, base_url)
        clicar_no_centro(pagina)
        esperar_mapa_parado(pagina)

        assert requisicoes  # a captura funcionou
        assert not [u for u in requisicoes if "tile.openstreetmap.org" in u]

    def test_mapa01_atribuicao_do_basemap_esta_visivel(self, pagina: Page, base_url: str) -> None:
        abrir_mapa(pagina, base_url)

        atribuicao = pagina.locator(".maplibregl-ctrl-attrib")
        expect(atribuicao).to_be_visible()
        expect(atribuicao).to_contain_text("OpenStreetMap")
        expect(atribuicao).to_contain_text("OpenFreeMap")

    def test_mapa02_camera_inicial_enquadra_o_rj_e_o_arraste_nao_e_travado(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        esperar_mapa_parado(pagina)

        centro = pagina.evaluate("() => __mapa.getCenter().toArray()")
        assert BBOX_RJ["oeste"] < centro[0] < BBOX_RJ["leste"]
        assert BBOX_RJ["sul"] < centro[1] < BBOX_RJ["norte"]
        assert pagina.evaluate("() => __mapa.getMaxBounds()") is None  # sem trava de bbox

        caixa = pagina.locator("#mapa canvas").bounding_box()
        assert caixa is not None
        x, y = caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2
        pagina.mouse.move(x, y)
        pagina.mouse.down()
        pagina.mouse.move(x + 250, y + 120, steps=8)
        pagina.mouse.up()
        esperar_mapa_parado(pagina)
        depois = pagina.evaluate("() => __mapa.getCenter().toArray()")
        assert depois[0] < centro[0]  # arrastou para a direita → o centro andou para o oeste

    def test_mapa04_contorno_e_mascara_fora_do_rj_estao_no_mapa(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        pagina.wait_for_function(
            "() => __mapa.getSource('rj-contorno').serialize().data?.type === 'Feature'"
        )

        camadas = pagina.evaluate("() => __mapa.getStyle().layers.map((l) => l.id)")
        assert camadas.index("fora-rj") < camadas.index("rj-contorno") < camadas.index(
            "lote-selecionado"
        )
        opacidade = pagina.evaluate("() => __mapa.getPaintProperty('fora-rj', 'fill-opacity')")
        assert 0 < opacidade < 1

    def test_mapa03_estilo_bloqueado_mostra_aviso_e_o_clique_ainda_consulta(
        self, pagina: Page, base_url: str
    ) -> None:
        pagina.route(URL_ESTILO_OPENFREEMAP, lambda rota: rota.abort())

        abrir_mapa(pagina, base_url)
        expect(pagina.locator("#aviso-mapa")).to_have_text("Mapa base indisponível")

        consultar_ponto(pagina, *PONTO_LOTE)
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")


class TestClique:
    def test_mapa08_clique_no_lote_desenha_o_contorno_e_enquadra_na_area_livre(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_LOTE, zoom=11)

        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")
        esperar_mapa_parado(pagina)
        assert ids_do_lote_selecionado(pagina) == ["SIGEF-001"]
        assert pagina.evaluate("() => __mapa.getLayer('lote-selecionado').source") == "lote"

        # bbox do SIGEF-001: [-43.105, -22.905, -43.095, -22.895] → cantos dentro do canvas
        cantos = pagina.evaluate(
            """() => [[-43.105, -22.905], [-43.095, -22.895]].map((c) => {
                const p = __mapa.project(c);
                return [p.x, p.y];
            })"""
        )
        caixa = pagina.locator("#mapa canvas").bounding_box()
        painel = pagina.locator(".painel").bounding_box()
        assert caixa is not None and painel is not None
        assert caixa["x"] + caixa["width"] <= painel["x"] + 1  # o mapa não fica sob o painel
        for x, y in cantos:
            assert 0 <= x <= caixa["width"]
            assert 0 <= y <= caixa["height"]

    def test_mapa08_com_movimento_reduzido_o_enquadramento_nao_anima(
        self, pagina: Page, base_url: str
    ) -> None:
        pagina.emulate_media(reduced_motion="reduce")
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_LOTE, zoom=11)

        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")

        assert pagina.evaluate("() => __mapa.isMoving()") is False

    def test_mapa05_clique_fora_do_rj_mostra_o_estado_fora_do_rj(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_FORA_DO_RJ, zoom=8)

        painel = pagina.locator("#conteudo-painel")
        expect(painel).to_contain_text("Fora do estado do Rio de Janeiro")
        expect(painel).not_to_contain_text("Erro inesperado")
        assert ids_do_lote_selecionado(pagina) == []


class TestUxDoD:
    def test_foco_visivel_no_mapa_nos_controles_e_no_botao_sair(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        focados: dict[str, bool] = {}

        for _ in range(10):
            pagina.keyboard.press("Tab")
            info = pagina.evaluate(
                """() => {
                    const e = document.activeElement;
                    const s = getComputedStyle(e);
                    const rotulo = e.id || e.getAttribute('aria-label') || e.className || e.tagName;
                    const contorno = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0;
                    return [String(rotulo), contorno || s.boxShadow !== 'none'];
                }"""
            )
            focados[info[0]] = bool(info[1])
            if info[0] == "sair":
                break

        assert "sair" in focados
        assert len(focados) >= 3  # canvas do mapa + controles de zoom + sair
        assert all(focados.values()), focados

    def test_atribuicao_legivel_com_contraste_de_pelo_menos_4_5(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        cores = pagina.evaluate(
            """() => {
                const caixa = document.querySelector('.maplibregl-ctrl-attrib');
                const link = caixa.querySelector('a');
                return [getComputedStyle(link).color, getComputedStyle(caixa).backgroundColor,
                        getComputedStyle(document.querySelector('#mapa')).backgroundColor];
            }"""
        )
        texto = _rgb(cores[0])[:3]
        r, g, b, alfa = _rgb(cores[1])
        fundo_do_mapa = (242.0, 239.0, 233.0)  # #f2efe9, o fundo do estilo mínimo de teste
        canais = zip((r, g, b), fundo_do_mapa, strict=True)
        fundo = tuple(alfa * c + (1 - alfa) * f for c, f in canais)

        assert _contraste(texto, fundo) >= 4.5  # type: ignore[arg-type]

    def test_estado_de_espera_mostra_consultando_o_lote(
        self, pagina: Page, base_url: str
    ) -> None:
        pendentes: list[Route] = []
        pagina.route("**/dossie?*", lambda rota: pendentes.append(rota))
        abrir_mapa(pagina, base_url)

        consultar_ponto(pagina, *PONTO_LOTE)

        expect(pagina.locator("#conteudo-painel")).to_have_text("Consultando o lote…")
        pagina.wait_for_function("() => true")
        for rota in pendentes:
            rota.continue_()
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")

    def test_sem_rolagem_horizontal_em_320px(self, pagina: Page, base_url: str) -> None:
        pagina.set_viewport_size({"width": 320, "height": 640})

        abrir_mapa(pagina, base_url)

        largura = pagina.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"
        )
        assert largura[0] <= largura[1], largura
        centrar(pagina, *PONTO_LOTE)


class TestSobreposicao:
    def test_mapa12_clique_na_sobreposicao_desenha_um_contorno_por_candidato(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_SOBREPOSTO, zoom=11)

        linhas = pagina.locator("#conteudo-painel .candidato")
        expect(linhas).to_have_count(2)
        esperar_mapa_parado(pagina)
        assert ids_dos_candidatos(pagina) == sorted(IDS_SOBREPOSTOS)
        assert ids_do_lote_selecionado(pagina) == []  # candidato não é "selecionado"
        tracejado = pagina.evaluate(
            "() => __mapa.getPaintProperty('lote-candidatos', 'line-dasharray')"
        )
        assert tracejado == [2, 2]

    def test_mapa12_hover_na_linha_destaca_so_o_candidato_certo_no_mapa(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_SOBREPOSTO, zoom=11)
        segunda = pagina.locator("#conteudo-painel .candidato[data-lote-id='OVL-2']")
        expect(segunda).to_be_visible()

        segunda.hover()

        assert estado_do_candidato(pagina, "OVL-2").get("hover") is True
        assert estado_do_candidato(pagina, "OVL-1").get("hover") in (None, False)
        expect(segunda).to_have_class("restricao candidato is-hover")
        # hover não é seleção: o lote selecionado continua vazio
        assert ids_do_lote_selecionado(pagina) == []

        pagina.locator(".marca").hover()  # sai da linha
        assert estado_do_candidato(pagina, "OVL-2").get("hover") in (None, False)
