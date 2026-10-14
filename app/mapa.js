// Mapa do estado do RJ → painel do dossiê (Fatia 7 e F1.13, AD-012, AD-015).
//
// MapLibre GL JS + basemap OpenFreeMap; nunca `tile.openstreetmap.org`. O clique vai ao
// `consultas.js` (o último clique vence), a resposta vira view model em `dossie.js` e HTML em
// `painel.js`. Este shell só liga o DOM, o MapLibre e esses módulos puros. As coordenadas do
// MapLibre e do GeoJSON são `[lon, lat]`.

import * as maplibregl from "https://unpkg.com/maplibre-gl@6.14.0/dist/maplibre-gl.mjs";
import { API_BASE, BBOX_RJ } from "./config.js";
import { criarControladorDeConsultas } from "./consultas.js";
import { renderDossie } from "./dossie.js";
import { bboxDe, mascaraFora } from "./geometria.js";
import { escreverSelecao, lerSelecao } from "./url.js";
import { htmlCarregando, htmlPainel, variavelDeCor } from "./painel.js";

const URL_ESTILO = "https://tiles.openfreemap.org/styles/positron";
const ESTILO_SEM_BASE = { version: 8, sources: {}, layers: [] };
const MARGEM_PX = 48;

const $ = (id) => document.getElementById(id);
const painel = $("conteudo-painel");
const regiaoDoPainel = document.querySelector(".painel"); // a região `aria-live` (MAPA-17, MAPA-19)
const reducaoDeMovimento = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const cssVar = (nome) => getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
const FEATURES_VAZIAS = { type: "FeatureCollection", features: [] };
const DICA_INICIAL = painel.innerHTML; // o texto "Clique num ponto…" que a página já traz

const mapa = new maplibregl.Map({
  container: "mapa",
  style: URL_ESTILO,
  bounds: [[BBOX_RJ.oeste, BBOX_RJ.sul], [BBOX_RJ.leste, BBOX_RJ.norte]],
  fitBoundsOptions: { padding: 16, animate: false },
  attributionControl: { compact: false },
});
mapa.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
globalThis.__mapa = mapa; // gancho dos testes de navegador

// --- Basemap: se o estilo não carrega, o mapa segue sem fundo e a consulta continua (MAPA-03) ---

let estiloCarregado = false;
let usandoEstiloSemBase = false;

mapa.on("error", (evento) => {
  console.warn("mapa:", evento.error?.message ?? evento);
  if (estiloCarregado || usandoEstiloSemBase) return;
  usandoEstiloSemBase = true;
  const aviso = $("aviso-mapa");
  aviso.textContent = "Mapa base indisponível";
  aviso.hidden = false;
  mapa.setStyle(ESTILO_SEM_BASE);
});

mapa.on("style.load", () => {
  estiloCarregado = true;
  adicionarCamadas();
  carregarContorno();
  abrirSelecaoDaUrl();
});

// Os rótulos do basemap ficam por cima dos nossos dados: tudo entra antes do primeiro `symbol`.
function primeiroRotulo() {
  return mapa.getStyle().layers.find((camada) => camada.type === "symbol")?.id;
}

function adicionarCamadas() {
  const antes = primeiroRotulo();
  mapa.addSource("fora-rj", { type: "geojson", data: FEATURES_VAZIAS });
  mapa.addSource("rj-contorno", { type: "geojson", data: FEATURES_VAZIAS });
  mapa.addSource("lote", { type: "geojson", data: FEATURES_VAZIAS, promoteId: "lote_id" });
  mapa.addSource("candidatos", { type: "geojson", data: FEATURES_VAZIAS, promoteId: "lote_id" });
  mapa.addSource("ponto-clicado", { type: "geojson", data: FEATURES_VAZIAS });

  mapa.addLayer({
    id: "fora-rj", type: "fill", source: "fora-rj",
    paint: { "fill-color": cssVar("--ink"), "fill-opacity": 0.35 },
  }, antes);
  mapa.addLayer({
    id: "rj-contorno", type: "line", source: "rj-contorno",
    paint: { "line-color": cssVar("--ink-soft"), "line-width": 1.5 },
  }, antes);
  // Candidatos da sobreposição: tracejados, cada um com a sua cor. `hover` engrossa o contorno;
  // "passar o mouse" nunca parece "selecionado" (MAPA-12).
  const comHover = (normal, destacado) =>
    ["case", ["boolean", ["feature-state", "hover"], false], destacado, normal];
  mapa.addLayer({
    id: "lote-candidatos-fill", type: "fill", source: "candidatos",
    paint: { "fill-color": ["get", "cor"], "fill-opacity": comHover(0.08, 0.3) },
  }, antes);
  mapa.addLayer({
    id: "lote-candidatos", type: "line", source: "candidatos",
    paint: {
      "line-color": ["get", "cor"], "line-width": comHover(2, 4), "line-dasharray": [2, 2],
    },
  }, antes);
  mapa.addLayer({
    id: "lote-selecionado-fill", type: "fill", source: "lote",
    paint: { "fill-color": cssVar("--boundary"), "fill-opacity": 0.25 },
  }, antes);
  mapa.addLayer({
    id: "lote-selecionado", type: "line", source: "lote",
    paint: { "line-color": cssVar("--boundary"), "line-width": 2.5 },
  }, antes);
  mapa.addLayer({
    id: "ponto-clicado", type: "circle", source: "ponto-clicado",
    paint: {
      "circle-radius": 6, "circle-color": cssVar("--ink"),
      "circle-stroke-width": 2, "circle-stroke-color": "#fff",
    },
  });
  document.documentElement.dataset.mapReady = "true";
}

// O contorno é peripheral: sem ele o mapa abre sem moldura e o clique continua (spec, Error Handling).
async function carregarContorno() {
  try {
    const resposta = await fetch(`${API_BASE}/mapa/contorno`);
    if (!resposta.ok) return;
    const contorno = await resposta.json();
    mapa.getSource("rj-contorno")?.setData(contorno);
    mapa.getSource("fora-rj")?.setData(mascaraFora(contorno));
  } catch (erro) {
    console.warn("contorno do RJ indisponível:", erro);
  }
}

// --- Consulta: o último clique vence --------------------------------------------------------

let ultimoPonto = null;

const consultas = criarControladorDeConsultas({
  fetchFn: (url, opcoes) => fetch(url, opcoes),
  baseUrl: API_BASE,
  aoIniciar: (ponto) => {
    ultimoPonto = ponto;
    // replaceState, nunca pushState: o histórico não cresce a cada clique (MAPA-14).
    history.replaceState(null, "", location.pathname + escreverSelecao(ponto.lat, ponto.lon));
    limparLote();
    marcarPonto(ponto);
    regiaoDoPainel.setAttribute("aria-busy", "true");
    painel.innerHTML = htmlCarregando();
  },
  aoResponder: (resultado) => {
    regiaoDoPainel.setAttribute("aria-busy", "false");
    if (resultado.status === 401) {
      window.location.href = "login.html"; // sessão ausente/expirada (PAINEL-12/06)
      return;
    }
    const vm = renderDossie(resultado);
    painel.innerHTML = htmlPainel(vm);
    focarTitulo();
    if (vm.estado === "dossie" && vm.geometria) selecionarLote(vm);
    if (vm.estado === "sobreposicao") mostrarCandidatos(vm.candidatos);
  },
});

mapa.on("click", (evento) => consultas.consultar(evento.lngLat.lat, evento.lngLat.lng));

// O resultado leva o foco ao título do painel, mas nunca no meio de um arraste do mapa (MAPA-19).
let arrastando = false;
mapa.on("dragstart", () => { arrastando = true; });
mapa.on("dragend", () => { arrastando = false; });

function focarTitulo() {
  if (!arrastando) document.getElementById("titulo-painel")?.focus({ preventScroll: true });
}

// ?lat=&lon= válidos e dentro do RJ viram uma consulta; qualquer outra coisa é ignorada (MAPA-13).
let selecaoDaUrlAberta = false;
function abrirSelecaoDaUrl() {
  if (selecaoDaUrlAberta) return;
  selecaoDaUrlAberta = true;
  const ponto = lerSelecao(location.search);
  if (ponto) consultas.consultar(ponto.lat, ponto.lon);
}

// Esc limpa a seleção: contorno, ponto, painel e parâmetros da URL (MAPA-14).
document.addEventListener("keydown", (evento) => {
  if (evento.key !== "Escape") return;
  consultas.cancelar();
  regiaoDoPainel.setAttribute("aria-busy", "false");
  limparLote();
  mapa.getSource("ponto-clicado")?.setData(FEATURES_VAZIAS);
  painel.innerHTML = DICA_INICIAL;
  ultimoPonto = null;
  history.replaceState(null, "", location.pathname);
});

// "Tentar de novo" repete o mesmo ponto (MAPA-18).
painel.addEventListener("click", (evento) => {
  if (evento.target.closest("[data-acao='tentar-de-novo']") && ultimoPonto) {
    consultas.consultar(ultimoPonto.lat, ultimoPonto.lon);
  }
});

// --- Lote selecionado ------------------------------------------------------------------------

function selecionarLote(vm) {
  const feature = {
    type: "Feature",
    properties: { lote_id: vm.lote.lote_id },
    geometry: vm.geometria,
  };
  mapa.getSource("lote")?.setData({ type: "FeatureCollection", features: [feature] });
  enquadrar(vm.geometria);
}

function mostrarCandidatos(candidatos) {
  const features = candidatos
    .filter((c) => c.geometria)
    .map((c, indice) => ({
      type: "Feature",
      properties: { lote_id: c.lote_id, cor: cssVar(variavelDeCor(indice)) },
      geometry: c.geometria,
    }));
  if (features.length === 0) return;
  const colecao = { type: "FeatureCollection", features };
  mapa.getSource("candidatos")?.setData(colecao);
  enquadrar(colecao);
}

function limparLote() {
  mapa.getSource("lote")?.setData(FEATURES_VAZIAS);
  mapa.getSource("candidatos")?.setData(FEATURES_VAZIAS);
  destacarCandidato(null);
}

// --- Candidato sob o cursor: o mesmo destaque na lista e no mapa (MAPA-12) -----------------

let candidatoDestacado = null;

function destacarCandidato(loteId) {
  if (candidatoDestacado === loteId) return;
  if (candidatoDestacado !== null) {
    mapa.setFeatureState({ source: "candidatos", id: candidatoDestacado }, { hover: false });
  }
  candidatoDestacado = loteId;
  for (const linha of painel.querySelectorAll(".candidato")) {
    linha.classList.toggle("is-hover", linha.dataset.loteId === loteId);
  }
  if (loteId !== null) mapa.setFeatureState({ source: "candidatos", id: loteId }, { hover: true });
}

const idDaLinha = (evento) => evento.target.closest(".candidato")?.dataset.loteId ?? null;
painel.addEventListener("pointerover", (evento) => destacarCandidato(idDaLinha(evento)));
painel.addEventListener("pointerleave", () => destacarCandidato(null));
painel.addEventListener("focusin", (evento) => destacarCandidato(idDaLinha(evento)));
painel.addEventListener("focusout", () => destacarCandidato(null));

mapa.on("mousemove", "lote-candidatos-fill", (evento) => {
  destacarCandidato(evento.features[0]?.id !== undefined ? String(evento.features[0].id) : null);
});
mapa.on("mouseleave", "lote-candidatos-fill", () => destacarCandidato(null));

function marcarPonto({ lat, lon }) {
  mapa.getSource("ponto-clicado")?.setData({
    type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] },
  });
}

// O padding tira da área útil o pedaço do mapa que o painel cobre (MAPA-08).
function enquadrar(geojson) {
  mapa.fitBounds(bboxDe(geojson), {
    padding: paddingLivre(),
    maxZoom: 18,
    duration: reducaoDeMovimento() ? 0 : 600,
  });
}

function paddingLivre() {
  const padding = { top: MARGEM_PX, right: MARGEM_PX, bottom: MARGEM_PX, left: MARGEM_PX };
  const area = $("mapa").getBoundingClientRect();
  const folha = document.querySelector(".painel").getBoundingClientRect();
  const sobrepoe = folha.left < area.right && folha.right > area.left
    && folha.top < area.bottom && folha.bottom > area.top;
  if (!sobrepoe) return padding;
  const folhaInferior = folha.width >= area.width * 0.9; // ocupa a largura toda: é a folha do celular
  if (folhaInferior) padding.bottom += area.bottom - folha.top;
  else padding.right += area.right - folha.left;
  return padding;
}

// A folha inferior cobre o rodapé do mapa: o CSS sobe os controles de rodapé por esta variável.
new ResizeObserver(([entrada]) => {
  const altura = entrada.target.getBoundingClientRect().height;
  document.documentElement.style.setProperty("--altura-folha", `${altura}px`);
}).observe(document.querySelector(".painel"));

// --- Logout ----------------------------------------------------------------------------------
$("sair").addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" });
  } finally {
    window.location.href = "login.html";
  }
});
