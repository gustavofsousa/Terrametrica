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
import { htmlCarregando, htmlPainel } from "./painel.js";

const URL_ESTILO = "https://tiles.openfreemap.org/styles/positron";
const ESTILO_SEM_BASE = { version: 8, sources: {}, layers: [] };
const MARGEM_PX = 48;

const $ = (id) => document.getElementById(id);
const painel = $("conteudo-painel");
const reducaoDeMovimento = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const cssVar = (nome) => getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
const FEATURES_VAZIAS = { type: "FeatureCollection", features: [] };

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
  mapa.addSource("ponto-clicado", { type: "geojson", data: FEATURES_VAZIAS });

  mapa.addLayer({
    id: "fora-rj", type: "fill", source: "fora-rj",
    paint: { "fill-color": cssVar("--ink"), "fill-opacity": 0.35 },
  }, antes);
  mapa.addLayer({
    id: "rj-contorno", type: "line", source: "rj-contorno",
    paint: { "line-color": cssVar("--ink-soft"), "line-width": 1.5 },
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
    limparLote();
    marcarPonto(ponto);
    painel.innerHTML = htmlCarregando();
  },
  aoResponder: (resultado) => {
    if (resultado.status === 401) {
      window.location.href = "login.html"; // sessão ausente/expirada (PAINEL-12/06)
      return;
    }
    const vm = renderDossie(resultado);
    painel.innerHTML = htmlPainel(vm);
    if (vm.estado === "dossie" && vm.geometria) selecionarLote(vm);
  },
});

mapa.on("click", (evento) => consultas.consultar(evento.lngLat.lat, evento.lngLat.lng));

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

function limparLote() {
  mapa.getSource("lote")?.setData(FEATURES_VAZIAS);
}

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
  if (folha.top > area.top + area.height / 2) padding.bottom += area.bottom - folha.top;
  else if (folha.left > area.left + area.width / 2) padding.right += area.right - folha.left;
  return padding;
}

// --- Logout ----------------------------------------------------------------------------------
$("sair").addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" });
  } finally {
    window.location.href = "login.html";
  }
});
