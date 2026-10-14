// Testes da seleção na URL (T15). Rodar: node --test app/tests/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { lerSelecao, escreverSelecao } from "../url.js";

test("MAPA-13 lat e lon válidos dentro do RJ → ponto", () => {
  assert.deepEqual(lerSelecao("?lat=-22.9&lon=-43.1"), { lat: -22.9, lon: -43.1 });
});

test("MAPA-13 sem o '?' inicial também lê", () => {
  assert.deepEqual(lerSelecao("lat=-22.9&lon=-43.1"), { lat: -22.9, lon: -43.1 });
});

test("MAPA-13 texto, vazio e NaN → null", () => {
  assert.equal(lerSelecao("?lat=abc&lon=-43.1"), null);
  assert.equal(lerSelecao("?lat=&lon=-43.1"), null);
  assert.equal(lerSelecao("?lat=NaN&lon=-43.1"), null);
  assert.equal(lerSelecao("?lat=-22.9&lon=Infinity"), null);
  assert.equal(lerSelecao("?lat=1e1&lon=-43.1"), null);
});

test("MAPA-13 fora do bbox do RJ → null (São Paulo, hemisfério errado)", () => {
  assert.equal(lerSelecao("?lat=-23.5505&lon=-46.6333"), null);
  assert.equal(lerSelecao("?lat=22.9&lon=-43.1"), null);
  assert.equal(lerSelecao("?lat=-22.9&lon=43.1"), null);
});

test("MAPA-13 falta um dos parâmetros → null", () => {
  assert.equal(lerSelecao("?lat=-22.9"), null);
  assert.equal(lerSelecao("?lon=-43.1"), null);
  assert.equal(lerSelecao(""), null);
});

test("MAPA-14 a escrita usa 6 casas", () => {
  assert.equal(escreverSelecao(-22.9, -43.1), "?lat=-22.900000&lon=-43.100000");
  assert.equal(escreverSelecao(-22.12345678, -43.98765432), "?lat=-22.123457&lon=-43.987654");
});

test("MAPA-14 o que se escreve volta igual na leitura", () => {
  const ponto = lerSelecao(escreverSelecao(-22.123457, -43.987654));
  assert.deepEqual(ponto, { lat: -22.123457, lon: -43.987654 });
});
