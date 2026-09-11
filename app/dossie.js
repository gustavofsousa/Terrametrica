// Render do painel lateral do dossiê — módulo puro, sem DOM (Fatia 7, T8, AD-012).
//
// Recebe a resposta da API (`{status, corpo}` de GET /dossie) e devolve um *view model*: uma
// estrutura de dados descrevendo o que o painel deve mostrar. Manter isto puro (sem tocar o DOM)
// é o que o torna testável por `node --test` sem navegador — o `mapa.js` (T10) traduz este view
// model em elementos HTML. Os quatro estados 200/404/409/429 vêm dos DTOs de `api/dto.py`.

// Constrói o view model a partir de uma resposta da API. `status` é o HTTP status; `corpo` é o JSON.
export function renderDossie({ status, corpo }) {
  switch (status) {
    case 200:
      return dossie(corpo);
    case 404:
      return semLote(corpo);
    case 409:
      return sobreposicao(corpo);
    case 429:
      return cotaExcedida(corpo);
    default:
      return { estado: "erro", titulo: "Erro inesperado", mensagem: `HTTP ${status}` };
  }
}

// 200 — dossiê do lote: dados, restrições, proveniência, ressalva (PAINEL-08).
function dossie(corpo) {
  return {
    estado: "dossie",
    titulo: tituloDoLote(corpo.lote),
    lote: corpo.lote,
    restricoes: (corpo.restricoes ?? []).map((r) => ({
      tipo: r.tipo,
      nome: r.nome,
      pctDoLote: r.pct_do_lote,
      categoria: r.categoria,
      grauSuscetibilidade: r.grau_suscetibilidade,
    })),
    proveniencia: corpo.proveniencia ?? {},
    ressalva: corpo.ressalva ?? null,
  };
}

// 404 — clique sem lote conhecido: mensagem + cobertura do município (PAINEL-09).
function semLote(corpo) {
  return {
    estado: "sem_lote",
    titulo: "Nenhum lote neste ponto",
    mensagem: corpo.mensagem ?? "",
    municipio: corpo.municipio ?? null,
    cobertura: corpo.cobertura ?? [],
  };
}

// 409 — sobreposição: mensagem + candidatos a escolher (PAINEL-10).
function sobreposicao(corpo) {
  return {
    estado: "sobreposicao",
    titulo: "Mais de um lote neste ponto",
    mensagem: corpo.mensagem ?? "",
    candidatos: corpo.candidatos ?? [],
  };
}

// 429 — cota excedida: mensagem + tempo de espera (PAINEL-11).
function cotaExcedida(corpo) {
  return {
    estado: "cota",
    titulo: "Limite de consultas atingido",
    mensagem: corpo.erro ?? "cota excedida",
    retryAfterSegundos: corpo.retry_after_segundos ?? null,
  };
}

function tituloDoLote(lote) {
  if (!lote) return "Lote";
  if (lote.natureza === "rural") return lote.codigo_sigef ?? "Lote rural";
  return lote.inscricao_cadastral ?? "Lote urbano";
}
