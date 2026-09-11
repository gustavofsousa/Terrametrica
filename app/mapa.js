// Mapa autenticado → painel do dossiê (Fatia 7, T10, AD-012).
//
// Leaflet + tiles OSM; clique captura lat/lon e chama GET /dossie autenticado pelo cookie de sessão
// (credentials:"include", sem X-Conta-Id). A resposta passa por dossie.js (view model puro) e é
// pintada no painel lateral. 401 → sessão ausente/expirada → volta ao login (PAINEL-07/12/06).

import { API_BASE } from "./config.js";
import { renderDossie } from "./dossie.js";

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

async function consultar(lat, lon) {
  pintarCarregando();
  let resp;
  try {
    resp = await fetch(`${API_BASE}/dossie?lat=${lat}&lon=${lon}`, {
      credentials: "include",
    });
  } catch {
    pintarErro("Falha de conexão ao consultar o lote.");
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

// --- Pintura do painel a partir do view model (dossie.js) ---

function pintar(vm) {
  switch (vm.estado) {
    case "dossie":       painel.innerHTML = htmlDossie(vm); break;
    case "sem_lote":     painel.innerHTML = htmlSemLote(vm); break;
    case "sobreposicao": painel.innerHTML = htmlSobreposicao(vm); break;
    case "cota":         painel.innerHTML = htmlCota(vm); break;
    default:             pintarErro(vm.mensagem ?? "Erro inesperado.");
  }
}

function pintarCarregando() {
  painel.innerHTML = `<p class="dica" role="status">Consultando o lote…</p>`;
}

function pintarErro(msg) {
  painel.innerHTML = `<div class="aviso erro">${esc(msg)}</div>`;
}

function htmlDossie(vm) {
  const restricoes = vm.restricoes.length
    ? vm.restricoes.map((r) => `
        <div class="restricao">
          <strong>${esc(r.nome)}</strong>
          ${r.pctDoLote != null ? `<span class="pct"> ${esc(r.pctDoLote)}% do lote</span>` : ""}
          ${r.categoria ? `<div class="badge">${esc(r.categoria)}</div>` : ""}
        </div>`).join("")
    : `<p class="dica">Nenhuma restrição cruzada com este lote.</p>`;

  const prov = Object.entries(vm.proveniencia).map(([camada, p]) =>
    `<div class="badge">${esc(camada)}: ${esc(p.fonte ?? "?")} · ${esc(p.data_extracao ?? "")}</div>`
  ).join(" ");

  return `
    <h2>${esc(vm.titulo)}</h2>
    <div class="secao"><h3>Restrições</h3>${restricoes}</div>
    <div class="secao"><h3>Proveniência</h3>${prov || '<p class="dica">—</p>'}</div>
    ${vm.ressalva ? `<div class="secao"><h3>Ressalva</h3><p class="dica">${esc(vm.ressalva)}</p></div>` : ""}
  `;
}

function htmlSemLote(vm) {
  const cobertura = vm.cobertura.map((c) =>
    `<div class="badge">${esc(c.camada)}: ${c.tem_dado ? "com dado" : "sem dado"}</div>`
  ).join(" ");
  return `
    <h2>${esc(vm.titulo)}</h2>
    <p class="dica">${esc(vm.mensagem)}</p>
    ${vm.municipio ? `<p class="dica">Município: ${esc(vm.municipio)}</p>` : ""}
    <div class="secao"><h3>Cobertura</h3>${cobertura || '<p class="dica">—</p>'}</div>
  `;
}

function htmlSobreposicao(vm) {
  const candidatos = vm.candidatos.map((c) =>
    `<div class="restricao">${esc(c.codigo_sigef ?? c.inscricao_cadastral ?? "lote")}</div>`
  ).join("");
  return `
    <h2>${esc(vm.titulo)}</h2>
    <p class="dica">${esc(vm.mensagem)}</p>
    <div class="secao"><h3>Candidatos</h3>${candidatos}</div>
  `;
}

function htmlCota(vm) {
  const espera = vm.retryAfterSegundos != null
    ? ` Tente novamente em ~${Math.ceil(vm.retryAfterSegundos / 60)} min.` : "";
  return `<h2>${esc(vm.titulo)}</h2><div class="aviso erro">${esc(vm.mensagem)}${espera}</div>`;
}

// Escapa texto para inserção segura em HTML (evita XSS a partir de dados da API).
function esc(valor) {
  return String(valor)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

// --- Logout ---
document.getElementById("sair").addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" });
  } finally {
    window.location.href = "login.html";
  }
});
