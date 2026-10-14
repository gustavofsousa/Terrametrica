// Seleção do ponto na URL (MAPA-13, MAPA-14) — módulo puro, sem DOM.
//
// `lerSelecao` valida o que veio do `location.search`: número decimal, dentro da caixa do RJ.
// Qualquer outra coisa vira `null` e o painel ignora o parâmetro, sem fazer request.

import { BBOX_RJ } from "./config.js";

const CASAS_DECIMAIS = 6;
const NUMERO_DECIMAL = /^-?\d+(\.\d+)?$/;

export function lerSelecao(search) {
  const parametros = new URLSearchParams(search);
  const lat = lerNumero(parametros.get("lat"));
  const lon = lerNumero(parametros.get("lon"));
  if (lat === null || lon === null) return null;
  if (lat < BBOX_RJ.sul || lat > BBOX_RJ.norte) return null;
  if (lon < BBOX_RJ.oeste || lon > BBOX_RJ.leste) return null;
  return { lat, lon };
}

// Devolve a query string (`?lat=…&lon=…`) com 6 casas, para `history.replaceState`.
export function escreverSelecao(lat, lon) {
  return `?lat=${lat.toFixed(CASAS_DECIMAIS)}&lon=${lon.toFixed(CASAS_DECIMAIS)}`;
}

function lerNumero(texto) {
  if (texto === null || !NUMERO_DECIMAL.test(texto)) return null;
  return Number(texto);
}
