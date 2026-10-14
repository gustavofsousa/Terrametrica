// Render do painel lateral do dossiê — módulo puro, sem DOM (Fatia 7, T8, AD-012).
//
// Recebe a resposta da API (`{status, corpo}` de GET /dossie) e devolve um *view model*: uma
// estrutura de dados descrevendo o que o painel deve mostrar. Manter isto puro (sem tocar o DOM)
// é o que o torna testável por `node --test` sem navegador — o `mapa.js` (T10) traduz este view
// model em elementos HTML. Os estados 200/404/409/422/429 vêm dos DTOs de `api/dto.py`;
// `erro_rede` é a consulta que nem chegou a uma resposta HTTP (MAPA-18).

const FORMATO_HA = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const FORMATO_M = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

// Constrói o view model a partir de uma resposta da API. `status` é o HTTP status; `corpo` é o JSON.
// `erroRede` marca a consulta que falhou antes de ter resposta (queda de rede ou timeout).
export function renderDossie({ status, corpo, erroRede = false }) {
  if (erroRede) return erroDeRede();
  switch (status) {
    case 200:
      return dossie(corpo);
    case 404:
      return semLote(corpo);
    case 409:
      return sobreposicao(corpo);
    case 422:
      return foraDoRj(corpo);
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
    area: areaFormatada(corpo.lote),
    perimetro: perimetroFormatado(corpo.lote),
    fonteArea: (corpo.proveniencia ?? {})[camadaDoLote(corpo.lote)] ?? null,
    geometria: corpo.lote?.geometria ?? null,
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
    municipioNome: corpo.municipio_nome ?? null,
    rotuloMunicipio: corpo.municipio_nome ?? "Ponto fora de município mapeado",
    cobertura: corpo.cobertura ?? [],
  };
}

// 422 — clique fora do RJ (MAPA-05). O 422 de coordenada inválida traz `erro` e não é isto.
function foraDoRj(corpo) {
  if (corpo?.erro) {
    return { estado: "erro", titulo: "Coordenada inválida", mensagem: corpo.erro };
  }
  return {
    estado: "fora_do_rj",
    titulo: "Fora do estado do Rio de Janeiro",
    mensagem: corpo?.mensagem ?? "",
  };
}

// Sem resposta HTTP: o painel oferece repetir o mesmo ponto (MAPA-18).
function erroDeRede() {
  return {
    estado: "erro_rede",
    titulo: "Não foi possível consultar",
    mensagem: "A consulta não chegou ao servidor. Verifique a conexão e tente de novo.",
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

function camadaDoLote(lote) {
  return lote?.natureza === "urbano" ? "lote_urbano" : "lote_rural";
}

// Rural em hectares, urbano em m² (MAPA-09). Sem área, devolve null — o painel omite a linha.
function areaFormatada(lote) {
  if (lote?.natureza === "rural" && lote.area_ha != null) {
    return `${FORMATO_HA.format(lote.area_ha)} ha`;
  }
  if (lote?.natureza === "urbano" && lote.area_m2 != null) {
    return `${FORMATO_M.format(lote.area_m2)} m²`;
  }
  return null;
}

function perimetroFormatado(lote) {
  return lote?.perimetro_m != null ? `${FORMATO_M.format(lote.perimetro_m)} m` : null;
}

function tituloDoLote(lote) {
  if (!lote) return "Lote";
  if (lote.natureza === "rural") return lote.codigo_sigef ?? "Lote rural";
  return lote.inscricao_cadastral ?? "Lote urbano";
}
