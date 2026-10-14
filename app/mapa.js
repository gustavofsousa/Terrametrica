// Mapa autenticado → painel do dossiê (Fatia 7, T10, AD-012).
//
// Leaflet + tiles OSM; clique captura lat/lon e chama GET /dossie autenticado pelo cookie de sessão
// (credentials:"include", sem X-Conta-Id). A resposta passa por dossie.js (view model puro) e é
// pintada no painel lateral. 401 → sessão ausente/expirada → volta ao login (PAINEL-07/12/06).

import { API_BASE } from "./config.js";
import { renderDossie } from "./dossie.js";
import { htmlCarregando, htmlPainel } from "./painel.js";

const RJ_CENTRO = [-22.4, -42.6]; // aproximadamente o centro do estado
const painel = document.getElementById("conteudo-painel");

const mapa = L.map("mapa").setView(RJ_CENTRO, 8);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap",
}).addTo(mapa);

let marcador = null;

mapa.on("click", async (evento) => {
  const { lat, lng } = evento.latlng;
  if (marcador) marcador.remove();
  marcador = L.marker([lat, lng]).addTo(mapa);
  await consultar(lat, lng);
});

let ultimoPonto = null;

async function consultar(lat, lon) {
  ultimoPonto = { lat, lon };
  pintarCarregando();
  let resp;
  try {
    resp = await fetch(`${API_BASE}/dossie?lat=${lat}&lon=${lon}`, {
      credentials: "include",
    });
  } catch {
    pintar(renderDossie({ erroRede: true }));
    return;
  }

  if (resp.status === 401) {
    window.location.href = "login.html"; // sessão ausente/expirada (PAINEL-12/06)
    return;
  }

  let corpo = {};
  try { corpo = await resp.json(); } catch { /* corpo vazio em alguns erros */ }
  pintar(renderDossie({ status: resp.status, corpo }));
}

// --- Pintura do painel a partir do view model (dossie.js → painel.js) ---

function pintar(vm) {
  painel.innerHTML = htmlPainel(vm);
}

function pintarCarregando() {
  painel.innerHTML = htmlCarregando();
}

// "Tentar de novo" repete o mesmo ponto (MAPA-18).
painel.addEventListener("click", (evento) => {
  if (evento.target.closest("[data-acao='tentar-de-novo']") && ultimoPonto) {
    consultar(ultimoPonto.lat, ultimoPonto.lon);
  }
});

// --- Logout ---
document.getElementById("sair").addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" });
  } finally {
    window.location.href = "login.html";
  }
});
