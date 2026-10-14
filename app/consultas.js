// Controlador de consultas "o último clique vence" (MAPA-11, MAPA-18) — módulo puro, sem DOM.
//
// Cada `consultar` recebe um número de sequência. Só a resposta do número mais recente chega ao
// callback `aoResponder`; uma resposta antiga que chega depois é descartada. O `fetch` é injetado
// para o teste controlar a ordem das respostas. Timeout ou falha de rede viram `erroRede`, com o
// ponto clicado junto, para o painel repetir a mesma consulta.

export const TIMEOUT_PADRAO_MS = 15_000;

export function criarControladorDeConsultas({
  fetchFn,
  baseUrl = "",
  aoIniciar = () => {},
  aoResponder,
  timeoutMs = TIMEOUT_PADRAO_MS,
}) {
  let ultimaSequencia = 0;
  let consultaAtual = null; // AbortController da consulta em andamento

  // Resolve quando a consulta termina — respondida, descartada ou falha. O mapa não espera por isso.
  async function consultar(lat, lon) {
    const sequencia = ++ultimaSequencia;
    const ponto = { lat, lon };
    consultaAtual?.abort();
    const abortador = new AbortController();
    consultaAtual = abortador;
    const maisRecente = () => sequencia === ultimaSequencia;

    aoIniciar(ponto);
    const temporizador = setTimeout(() => abortador.abort(), timeoutMs);
    try {
      const resposta = await fetchFn(`${baseUrl}/dossie?lat=${lat}&lon=${lon}`, {
        credentials: "include",
        signal: abortador.signal,
      });
      const corpo = await resposta.json().catch(() => ({}));
      if (maisRecente()) aoResponder({ status: resposta.status, corpo, ponto });
    } catch {
      if (maisRecente()) aoResponder({ erroRede: true, ponto });
    } finally {
      clearTimeout(temporizador);
      if (consultaAtual === abortador) consultaAtual = null;
    }
  }

  // Esc: nenhuma resposta em andamento pode repintar o painel depois (MAPA-14).
  function cancelar() {
    ultimaSequencia++;
    consultaAtual?.abort();
  }

  return { consultar, cancelar };
}
