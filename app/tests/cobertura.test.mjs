// Testes do view model da página de cobertura pública (F1.12). Rodar: node --test app/tests/
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderCoberturaEstado } from "../cobertura.js";

test("município com dado exibe data formatada, nunca ISO crua (COBPUB-04)", () => {
  const corpo = {
    municipios: [
      {
        municipio: "Niterói",
        cobertura: [{ camada: "app", tem_dado: true, data_extracao: "2026-08-01" }],
      },
    ],
  };

  const vm = renderCoberturaEstado(corpo);

  assert.equal(vm.estado, "cobertura");
  const [niteroi] = vm.municipios;
  assert.equal(niteroi.municipio, "Niterói");
  assert.equal(niteroi.camadas[0].temDado, true);
  assert.equal(niteroi.camadas[0].dataFormatada, "01/08/2026");
  assert.doesNotMatch(niteroi.camadas[0].dataFormatada, /^\d{4}-\d{2}-\d{2}$/);
});

test("célula sem dado exibe 'sem dado' explícito, nunca omitida (COBPUB-05)", () => {
  const corpo = {
    municipios: [
      {
        municipio: "Angra dos Reis",
        cobertura: [{ camada: "corpo_dagua", tem_dado: false, data_extracao: null }],
      },
    ],
  };

  const vm = renderCoberturaEstado(corpo);

  const [angra] = vm.municipios;
  assert.equal(angra.camadas.length, 1);
  assert.equal(angra.camadas[0].temDado, false);
  assert.equal(angra.camadas[0].dataFormatada, "sem dado");
});

test("resposta sem municípios vira estado 'vazio' com mensagem explícita (COBPUB-06)", () => {
  const vm = renderCoberturaEstado({ municipios: [] });

  assert.equal(vm.estado, "vazio");
  assert.equal(vm.mensagem, "Nenhuma cobertura ainda.");
});
