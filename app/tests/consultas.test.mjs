// Testes do controlador "o último clique vence" (T14). Rodar: node --test app/tests/*.test.mjs
import { test, mock } from "node:test";
import assert from "node:assert/strict";
import { criarControladorDeConsultas } from "../consultas.js";

// fetch fake: cada chamada fica pendente até o teste resolvê-la, na ordem que quiser.
function criarFetchControlado() {
  const chamadas = [];
  const fetchFn = (url, opcoes) =>
    new Promise((resolve, reject) => {
      chamadas.push({ url, opcoes, resolve, reject });
      opcoes.signal.addEventListener("abort", () =>
        reject(new DOMException("abortado", "AbortError")));
    });
  return { fetchFn, chamadas };
}

const resposta = (status, corpo) => ({ status, json: async () => corpo });

test("MAPA-11 clique A lento + clique B rápido → só B chega ao painel", async () => {
  const { fetchFn, chamadas } = criarFetchControlado();
  const entregas = [];
  const { consultar } = criarControladorDeConsultas({
    fetchFn, aoResponder: (r) => entregas.push(r),
  });

  const a = consultar(-22.9, -43.1);
  const b = consultar(-22.8, -43.2);
  chamadas[1].resolve(resposta(200, { tipo: "B" }));
  await b;
  chamadas[0].resolve(resposta(200, { tipo: "A" })); // chega depois e é descartada
  await a;

  assert.equal(entregas.length, 1);
  assert.deepEqual(entregas[0].corpo, { tipo: "B" });
  assert.deepEqual(entregas[0].ponto, { lat: -22.8, lon: -43.2 });
});

test("MAPA-11 B lento + A já substituída → só B chega, mesmo se A responde antes", async () => {
  const { fetchFn, chamadas } = criarFetchControlado();
  const entregas = [];
  const { consultar } = criarControladorDeConsultas({
    fetchFn, aoResponder: (r) => entregas.push(r),
  });

  const a = consultar(-22.9, -43.1);
  const b = consultar(-22.8, -43.2);
  chamadas[0].resolve(resposta(200, { tipo: "A" })); // A responde primeiro, mas já foi superada
  await a;
  assert.equal(entregas.length, 0);
  chamadas[1].resolve(resposta(404, { tipo: "B" }));
  await b;

  assert.equal(entregas.length, 1);
  assert.equal(entregas[0].status, 404);
  assert.deepEqual(entregas[0].corpo, { tipo: "B" });
});

test("MAPA-18 fetch que nunca resolve → erroRede após 15 s, com o ponto preservado", async () => {
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const { fetchFn } = criarFetchControlado();
    const entregas = [];
    const { consultar } = criarControladorDeConsultas({
      fetchFn, aoResponder: (r) => entregas.push(r),
    });

    const pendente = consultar(-22.9, -43.1);
    mock.timers.tick(14_999);
    assert.equal(entregas.length, 0);
    mock.timers.tick(1);
    await pendente;

    assert.deepEqual(entregas, [{ erroRede: true, ponto: { lat: -22.9, lon: -43.1 } }]);
  } finally {
    mock.timers.reset();
  }
});

test("MAPA-18 fetch que rejeita (rede caiu) → erroRede com o ponto", async () => {
  const entregas = [];
  const { consultar } = criarControladorDeConsultas({
    fetchFn: () => Promise.reject(new TypeError("Failed to fetch")),
    aoResponder: (r) => entregas.push(r),
  });

  await consultar(-22.9, -43.1);

  assert.deepEqual(entregas, [{ erroRede: true, ponto: { lat: -22.9, lon: -43.1 } }]);
});

test("a consulta usa a base da API, as coordenadas e o cookie de sessão", async () => {
  const { fetchFn, chamadas } = criarFetchControlado();
  const { consultar } = criarControladorDeConsultas({
    fetchFn, baseUrl: "https://api.exemplo", aoResponder: () => {},
  });

  const p = consultar(-22.9, -43.1);
  assert.equal(chamadas[0].url, "https://api.exemplo/dossie?lat=-22.9&lon=-43.1");
  assert.equal(chamadas[0].opcoes.credentials, "include");
  chamadas[0].resolve(resposta(200, {}));
  await p;
});

test("MAPA-17 aoIniciar avisa o ponto assim que a consulta começa", async () => {
  const { fetchFn, chamadas } = criarFetchControlado();
  const inicios = [];
  const { consultar } = criarControladorDeConsultas({
    fetchFn, aoIniciar: (p) => inicios.push(p), aoResponder: () => {},
  });

  const p = consultar(-22.9, -43.1);
  assert.deepEqual(inicios, [{ lat: -22.9, lon: -43.1 }]);
  chamadas[0].resolve(resposta(200, {}));
  await p;
});

test("corpo que não é JSON vira {} em vez de quebrar (erro HTTP sem corpo)", async () => {
  const entregas = [];
  const { consultar } = criarControladorDeConsultas({
    fetchFn: async () => ({ status: 502, json: async () => { throw new SyntaxError("x"); } }),
    aoResponder: (r) => entregas.push(r),
  });

  await consultar(-22.9, -43.1);

  assert.equal(entregas[0].status, 502);
  assert.deepEqual(entregas[0].corpo, {});
});
