// Renderização do painel (MAPA-09, MAPA-17, MAPA-18) — módulo puro: view model → string de HTML.
//
// SECURITY: todo texto vindo da API passa por `esc()` antes de entrar no HTML (nome de município,
// de restrição, de fonte…). O `mapa.js` só atribui o resultado a `innerHTML`.

export function esc(valor) {
  return String(valor)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

// Título de cada resultado: `tabindex="-1"` deixa o shell mover o foco para ele (MAPA-19).
const titulo = (texto) => `<h2 id="titulo-painel" tabindex="-1">${esc(texto)}</h2>`;

export function htmlPainel(vm) {
  switch (vm.estado) {
    case "dossie":       return htmlDossie(vm);
    case "sem_lote":     return htmlSemLote(vm);
    case "sobreposicao": return htmlSobreposicao(vm);
    case "cota":         return htmlCota(vm);
    case "fora_do_rj":   return htmlForaDoRj(vm);
    case "erro_rede":    return htmlErroRede(vm);
    default:             return htmlErro(vm);
  }
}

// MAPA-17: o shell põe `aria-busy="true"` no painel enquanto este texto está nele.
export function htmlCarregando() {
  return `<p class="dica" role="status">Consultando o lote…</p>`;
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
    `<div class="badge">${esc(camada)}: ${esc(p.fonte ?? "?")} · ${esc(formatarData(p.data_extracao))}</div>`
  ).join(" ");

  return `
    ${titulo(vm.titulo)}
    ${htmlMedidas(vm)}
    <div class="secao"><h3>Restrições</h3>${restricoes}</div>
    <div class="secao"><h3>Proveniência</h3>${prov || '<p class="dica">—</p>'}</div>
    ${vm.ressalva ? `<div class="secao"><h3>Ressalva</h3><p class="dica">${esc(vm.ressalva)}</p></div>` : ""}
  `;
}

// Área e perímetro nunca aparecem sem a fonte e a data de onde vieram (AD-005).
function htmlMedidas(vm) {
  if (!vm.area && !vm.perimetro) return "";
  const medidas = [
    vm.area ? `<dt>Área</dt><dd>${esc(vm.area)}</dd>` : "",
    vm.perimetro ? `<dt>Perímetro</dt><dd>${esc(vm.perimetro)}</dd>` : "",
  ].join("");
  return `<dl class="medidas">${medidas}</dl>${htmlFonte(vm.fonteArea)}`;
}

function htmlFonte(fonte) {
  if (!fonte) return "";
  const nome = `${esc(fonte.fonte ?? "?")} · ${esc(formatarData(fonte.data_extracao))}`;
  const link = linkSeguro(fonte.link_oficial);
  const origem = link ? `<a href="${esc(link)}" rel="noopener noreferrer">${nome}</a>` : nome;
  return `<p class="dica">Fonte da medida: ${origem}</p>`;
}

function htmlSemLote(vm) {
  const cobertura = vm.cobertura.map((c) =>
    `<div class="badge">${esc(c.camada)}: ${c.tem_dado ? "com dado" : "sem dado"}</div>`
  ).join(" ");
  return `
    ${titulo(vm.titulo)}
    <p class="dica">${esc(vm.mensagem)}</p>
    <p class="dica">Município: ${esc(vm.rotuloMunicipio)}</p>
    <div class="secao"><h3>Cobertura</h3>${cobertura || '<p class="dica">—</p>'}</div>
  `;
}

function htmlSobreposicao(vm) {
  const candidatos = vm.candidatos.map((c) =>
    `<div class="restricao">${esc(c.codigo_sigef ?? c.inscricao_cadastral ?? "lote")}</div>`
  ).join("");
  return `
    ${titulo(vm.titulo)}
    <p class="dica">${esc(vm.mensagem)}</p>
    <div class="secao"><h3>Candidatos</h3>${candidatos}</div>
  `;
}

function htmlCota(vm) {
  const espera = vm.retryAfterSegundos != null
    ? ` Tente novamente em ~${Math.ceil(vm.retryAfterSegundos / 60)} min.` : "";
  return `${titulo(vm.titulo)}<div class="aviso erro">${esc(vm.mensagem)}${esc(espera)}</div>`;
}

function htmlForaDoRj(vm) {
  return `${titulo(vm.titulo)}<p class="dica">Clique num ponto dentro do estado para consultar um lote.</p>`;
}

// MAPA-18: o botão repete o mesmo ponto; o shell liga o clique em `data-acao="tentar-de-novo"`.
function htmlErroRede(vm) {
  return `
    ${titulo(vm.titulo)}
    <div class="aviso erro">${esc(vm.mensagem)}</div>
    <button type="button" data-acao="tentar-de-novo">Tentar de novo</button>
  `;
}

function htmlErro(vm) {
  return `${titulo(vm.titulo ?? "Erro inesperado")}<div class="aviso erro">${esc(vm.mensagem ?? "Erro inesperado.")}</div>`;
}

// "2026-08-20" → "20/08/2026"; texto fora desse formato passa como veio.
function formatarData(iso) {
  const partes = String(iso ?? "").split("-");
  return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : String(iso ?? "");
}

// SECURITY: só http(s) vira href; `javascript:` e afins ficam como texto.
function linkSeguro(link) {
  return typeof link === "string" && /^https?:\/\//i.test(link) ? link : null;
}
