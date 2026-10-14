// Testes de geometria no cliente (T16). Rodar: node --test app/tests/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { bboxDe, mascaraFora } from "../geometria.js";

const quadrado = (oeste, sul, leste, norte) =>
  [[oeste, sul], [leste, sul], [leste, norte], [oeste, norte], [oeste, sul]];

test("MAPA-08 bboxDe de um Polygon", () => {
  const poligono = { type: "Polygon", coordinates: [quadrado(-43.2, -22.95, -43.1, -22.9)] };

  assert.deepEqual(bboxDe(poligono), [[-43.2, -22.95], [-43.1, -22.9]]);
});

test("MAPA-08 bboxDe de um MultiPolygon com partes distantes cobre todas elas", () => {
  const multi = {
    type: "MultiPolygon",
    coordinates: [
      [quadrado(-43.2, -22.95, -43.1, -22.9)],
      [quadrado(-41.5, -21.6, -41.4, -21.5)],
    ],
  };

  assert.deepEqual(bboxDe(multi), [[-43.2, -22.95], [-41.4, -21.5]]);
});

test("MAPA-08 bboxDe aceita um Feature e uma FeatureCollection (candidatos do 409)", () => {
  const a = { type: "Polygon", coordinates: [quadrado(-43.2, -22.95, -43.1, -22.9)] };
  const b = { type: "Polygon", coordinates: [quadrado(-43.0, -22.8, -42.9, -22.7)] };
  const colecao = {
    type: "FeatureCollection",
    features: [{ type: "Feature", properties: {}, geometry: a },
               { type: "Feature", properties: {}, geometry: b }],
  };

  assert.deepEqual(bboxDe({ type: "Feature", properties: {}, geometry: a }),
    [[-43.2, -22.95], [-43.1, -22.9]]);
  assert.deepEqual(bboxDe(colecao), [[-43.2, -22.95], [-42.9, -22.7]]);
});

test("bboxDe de geometria sem coordenadas ou de tipo desconhecido falha alto", () => {
  assert.throws(() => bboxDe({ type: "Polygon", coordinates: [] }), /sem coordenadas/);
  assert.throws(() => bboxDe({ type: "Point", coordinates: [0, 0] }), /não suportada/);
});

test("MAPA-04 máscara: retângulo do mundo com 1 furo para o RJ de uma parte só", () => {
  const rj = { type: "Polygon", coordinates: [quadrado(-44.9, -23.4, -40.9, -20.7)] };

  const mascara = mascaraFora(rj);

  assert.equal(mascara.geometry.type, "Polygon");
  const [mundo, ...furos] = mascara.geometry.coordinates;
  assert.deepEqual(mundo[0], [-180, -90]);
  assert.deepEqual(mundo[2], [180, 90]);
  assert.deepEqual(furos, [quadrado(-44.9, -23.4, -40.9, -20.7)]);
});

test("MAPA-04 máscara: N partes do RJ viram N furos (ilhas), só com o anel externo", () => {
  const anelInterno = quadrado(-43.15, -22.93, -43.12, -22.91);
  const rj = {
    type: "Feature",
    properties: { versao: "v1" },
    geometry: {
      type: "MultiPolygon",
      coordinates: [
        [quadrado(-44.9, -23.4, -40.9, -20.7), anelInterno],
        [quadrado(-41.0, -23.0, -40.95, -22.95)],
        [quadrado(-44.0, -23.3, -43.95, -23.25)],
      ],
    },
  };

  const mascara = mascaraFora(rj);

  const aneis = mascara.geometry.coordinates;
  assert.equal(aneis.length, 1 + 3); // mundo + 3 partes
  assert.deepEqual(aneis[1], quadrado(-44.9, -23.4, -40.9, -20.7));
  assert.ok(!aneis.some((anel) => anel === anelInterno)); // buraco interno não vira furo
});
