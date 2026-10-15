"""O mapa do painel no navegador — spec:mapa-do-lote-rj (T20: MAPA-01..05, MAPA-08)."""

from playwright.sync_api import Page, Route, expect

from tests.navegador.ajudas import (
    URL_ESTILO_OPENFREEMAP,
    abrir_mapa,
    centrar,
    clicar_no_centro,
    consultar_ponto,
    duracoes_dos_enquadramentos,
    esperar_mapa_parado,
    espiar_enquadramentos,
    estado_do_candidato,
    ids_do_lote_selecionado,
    ids_dos_candidatos,
)
from tests.navegador.semente import (
    ID_LOTE_MINUSCULO,
    IDS_SOBREPOSTOS,
    PONTO_FORA_DO_RJ,
    PONTO_LOTE,
    PONTO_LOTE_MINUSCULO,
    PONTO_SEM_LOTE,
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
        self, pagina: Page, base_url: str, requisicoes: list[str]
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
        # edge case: arrastar sem clicar nunca consulta o dossiê
        assert not [u for u in requisicoes if "/dossie?" in u]

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
        espiar_enquadramentos(pagina)

        consultar_ponto(pagina, *PONTO_LOTE, zoom=11)

        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")
        assert duracoes_dos_enquadramentos(pagina) == [0]

    def test_mapa08_sem_preferencia_de_movimento_o_enquadramento_anima(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        espiar_enquadramentos(pagina)

        consultar_ponto(pagina, *PONTO_LOTE, zoom=11)

        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")
        duracoes = duracoes_dos_enquadramentos(pagina)
        assert len(duracoes) == 1 and duracoes[0] > 0

    def test_edge_lote_menor_que_um_pixel_aproxima_ate_o_zoom_maximo_do_estilo(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_LOTE_MINUSCULO, zoom=20)

        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-TINY")
        esperar_mapa_parado(pagina)

        zoom = pagina.evaluate("() => __mapa.getZoom()")
        maximo = pagina.evaluate("() => __mapa.getMaxZoom()")
        assert zoom == maximo
        assert ids_do_lote_selecionado(pagina) == [ID_LOTE_MINUSCULO]

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


class TestSelecaoNaUrl:
    """spec:mapa-do-lote-rj — MAPA-13, MAPA-14."""

    def test_mapa13_abrir_com_parametros_de_um_lote_mostra_o_contorno_e_o_dossie(
        self, pagina: Page, base_url: str
    ) -> None:
        lat, lon = PONTO_LOTE
        abrir_mapa(pagina, base_url, f"/?lat={lat}&lon={lon}")

        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")
        esperar_mapa_parado(pagina)
        assert ids_do_lote_selecionado(pagina) == ["SIGEF-001"]

    def test_mapa13_parametros_invalidos_nao_fazem_nenhuma_requisicao_ao_dossie(
        self, pagina: Page, base_url: str, requisicoes: list[str]
    ) -> None:
        for consulta in ("?lat=abc&lon=-43.1", "?lat=-23.5505&lon=-46.6333", "?lat=-22.9"):
            abrir_mapa(pagina, base_url, f"/{consulta}")
            esperar_mapa_parado(pagina)

        assert requisicoes
        assert not [u for u in requisicoes if "/dossie?" in u]  # a API, não o dossie.js
        expect(pagina.locator("#conteudo-painel")).to_contain_text("Clique num ponto")

    def test_mapa14_cliques_trocam_a_url_sem_criar_entradas_no_historico(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        entradas = pagina.evaluate("() => history.length")

        for ponto in (PONTO_LOTE, PONTO_SEM_LOTE, PONTO_LOTE):
            consultar_ponto(pagina, *ponto)
            expect(pagina.locator("#conteudo-painel h2")).to_be_visible()

        assert pagina.evaluate("() => history.length") == entradas
        lat, lon = PONTO_LOTE
        assert pagina.url.endswith(f"?lat={lat:.6f}&lon={lon:.6f}")

    def test_mapa14_esc_remove_contorno_painel_e_parametros(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_LOTE)
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")
        esperar_mapa_parado(pagina)  # querySourceFeatures só vê o lote depois de renderizado
        assert ids_do_lote_selecionado(pagina) == ["SIGEF-001"]

        pagina.keyboard.press("Escape")

        expect(pagina.locator("#conteudo-painel")).to_contain_text("Clique num ponto")
        esperar_mapa_parado(pagina)
        assert ids_do_lote_selecionado(pagina) == []
        assert "?" not in pagina.url


class TestCelular:
    """spec:mapa-do-lote-rj — MAPA-15, MAPA-16 (viewport 390×844)."""

    def test_mapa15_folha_inferior_com_ate_50_por_cento_e_o_lote_fica_acima_dela(
        self, pagina_celular: Page, base_url: str
    ) -> None:
        pagina = pagina_celular
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_LOTE, zoom=11)
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")
        esperar_mapa_parado(pagina)

        folha = pagina.locator(".painel").bounding_box()
        mapa = pagina.locator("#mapa canvas").bounding_box()
        assert folha is not None and mapa is not None
        assert folha["height"] <= 422  # 50% de 844
        assert folha["y"] + folha["height"] == 844  # encostada na base
        assert mapa["width"] == 390  # o mapa ocupa a largura inteira
        # cantos do SIGEF-001: [-43.105, -22.905] e [-43.095, -22.895]
        cantos = pagina.evaluate(
            """() => [[-43.105, -22.905], [-43.095, -22.895]].map((c) => {
                const p = __mapa.project(c);
                return [p.x, p.y];
            })"""
        )
        for x, y in cantos:
            assert 0 <= x <= 390
            assert 0 <= y <= folha["y"], (y, folha["y"])  # acima da folha

    def test_mapa16_toque_no_mapa_visivel_consulta_e_nada_o_bloqueia(
        self, pagina_celular: Page, base_url: str
    ) -> None:
        pagina = pagina_celular
        abrir_mapa(pagina, base_url)
        lat, lon = PONTO_LOTE
        # O lote vai para a parte de cima do mapa, a que a folha não cobre.
        pagina.evaluate(
            "([lon, lat]) => __mapa.jumpTo({ center: [lon, lat], zoom: 14, "
            "padding: { bottom: 422 } })",
            [lon, lat],
        )
        esperar_mapa_parado(pagina)
        x, y = pagina.evaluate(
            "([lon, lat]) => { const p = __mapa.project([lon, lat]); return [p.x, p.y]; }",
            [lon, lat],
        )
        folha = pagina.locator(".painel").bounding_box()
        assert folha is not None and y < folha["y"]
        alvo = pagina.evaluate(
            "([x, y]) => document.elementFromPoint(x, y).tagName", [x, y]
        )
        assert alvo == "CANVAS"  # nenhuma camada invisível sobre o mapa

        pagina.touchscreen.tap(x, y)

        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")

    def test_alvos_de_toque_de_pelo_menos_44px_e_sem_rolagem_horizontal(
        self, pagina_celular: Page, base_url: str
    ) -> None:
        pagina = pagina_celular
        abrir_mapa(pagina, base_url)

        tamanhos = pagina.evaluate(
            """() => [...document.querySelectorAll('button')].map((b) => {
                const r = b.getBoundingClientRect();
                return [b.getAttribute('aria-label') || b.textContent.trim(), r.width, r.height];
            })"""
        )

        assert len(tamanhos) >= 4  # sair + controles do mapa
        for rotulo, largura, altura in tamanhos:
            assert largura >= 44 and altura >= 44, (rotulo, largura, altura)
        dimensoes = pagina.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"
        )
        assert dimensoes[0] <= dimensoes[1]

    def test_atribuicao_fica_acima_da_folha_e_visivel(
        self, pagina_celular: Page, base_url: str
    ) -> None:
        pagina = pagina_celular
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_LOTE, zoom=11)
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")

        atribuicao = pagina.locator(".maplibregl-ctrl-attrib").bounding_box()
        folha = pagina.locator(".painel").bounding_box()
        assert atribuicao is not None and folha is not None
        assert atribuicao["y"] + atribuicao["height"] <= folha["y"] + 1


class TestEsperaErroEFoco:
    """spec:mapa-do-lote-rj — MAPA-17, MAPA-18, MAPA-19."""

    def test_mapa17_durante_a_consulta_o_painel_fica_busy_e_sem_lote_selecionado(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        consultar_ponto(pagina, *PONTO_LOTE)
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")
        esperar_mapa_parado(pagina)
        assert ids_do_lote_selecionado(pagina) == ["SIGEF-001"]
        pendentes: list[Route] = []
        pagina.route("**/dossie?*", lambda rota: pendentes.append(rota))

        clicar_no_centro(pagina)

        expect(pagina.locator(".painel")).to_have_attribute("aria-busy", "true")
        expect(pagina.locator("#conteudo-painel")).to_have_text("Consultando o lote…")
        # o lote anterior saiu do estilo de selecionado enquanto a nova consulta espera
        assert ids_do_lote_selecionado(pagina) == []
        pendentes[0].continue_()
        expect(pagina.locator(".painel")).to_have_attribute("aria-busy", "false")
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")

    def test_mapa18_api_bloqueada_mostra_erro_e_tentar_de_novo_repete_o_mesmo_ponto(
        self, pagina: Page, base_url: str, requisicoes: list[str]
    ) -> None:
        abrir_mapa(pagina, base_url)
        pagina.route("**/dossie?*", lambda rota: rota.abort())

        consultar_ponto(pagina, *PONTO_LOTE)

        painel = pagina.locator("#conteudo-painel")
        expect(painel).to_contain_text("Não foi possível consultar")
        botao = painel.get_by_role("button", name="Tentar de novo")
        expect(botao).to_be_visible()

        pagina.unroute("**/dossie?*")
        botao.click()

        expect(painel).to_contain_text("SIGEF-001")
        consultas = [u for u in requisicoes if "/dossie?" in u]
        assert len(consultas) == 2
        assert consultas[0] == consultas[1]  # o mesmo ponto, não o último clique do mouse

    def test_mapa19_o_resultado_leva_o_foco_ao_titulo_e_a_regiao_e_anunciada(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)

        consultar_ponto(pagina, *PONTO_LOTE)

        expect(pagina.locator(".painel")).to_have_attribute("aria-live", "polite")
        titulo = pagina.locator("#conteudo-painel h2")
        expect(titulo).to_have_text("SIGEF-001")
        expect(titulo).to_be_focused()

    def test_mapa19_resultado_que_chega_durante_um_arraste_nao_rouba_o_foco(
        self, pagina: Page, base_url: str
    ) -> None:
        abrir_mapa(pagina, base_url)
        pendentes: list[Route] = []
        pagina.route("**/dossie?*", lambda rota: pendentes.append(rota))
        consultar_ponto(pagina, *PONTO_LOTE)
        expect(pagina.locator("#conteudo-painel")).to_have_text("Consultando o lote…")
        caixa = pagina.locator("#mapa canvas").bounding_box()
        assert caixa is not None
        x, y = caixa["x"] + 100, caixa["y"] + 100

        pagina.mouse.move(x, y)
        pagina.mouse.down()
        pagina.mouse.move(x + 60, y + 40, steps=6)  # arraste em curso
        pendentes[0].continue_()
        expect(pagina.locator("#conteudo-painel")).to_contain_text("SIGEF-001")

        assert pagina.evaluate("() => document.activeElement.id") != "titulo-painel"
        pagina.mouse.up()
