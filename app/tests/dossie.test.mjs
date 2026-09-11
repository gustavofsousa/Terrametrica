// Testes do view model do painel (Fatia 7, T8). Rodar: node --test app/tests/
// Fixtures replicam o shape de api/dto.py (dossie_para_dict etc.) para os 4 estados 200/404/409/429.
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderDossie } from "../dossie.js";

test("200 → dossiê com lote, restrições, proveniência e ressalva (PAINEL-08)", () => {
  const corpo = {
    tipo: "dossie",
    lote: { natureza: "rural", codigo_sigef: "SIGEF-001", area_ha: 12.5, municipios: ["Rio"] },
    restricoes: [
      { tipo: "app", nome: "APP curso d'água", pct_do_lote: 8.3, categoria: null,
        grau_suscetibilidade: null },
    ],
    proveniencia: { lote_rural: { fonte: "SIGEF", data_extracao: "2026-08-20" } },
    camadas_ausentes: [],
    ressalva: "Dossiê informativo.",
  };

  const vm = renderDossie({ status: 200, corpo });

  assert.equal(vm.estado, "dossie");
  assert.equal(vm.titulo, "SIGEF-001");
  assert.equal(vm.restricoes.length, 1);
  assert.equal(vm.restricoes[0].nome, "APP curso d'água");
  assert.equal(vm.restricoes[0].pctDoLote, 8.3);
  assert.equal(vm.proveniencia.lote_rural.fonte, "SIGEF");
  assert.equal(vm.ressalva, "Dossiê informativo.");
});

test("200 → lote urbano usa a inscrição cadastral como título", () => {
  const corpo = {
    tipo: "dossie",
    lote: { natureza: "urbano", inscricao_cadastral: "INSC-99", area_m2: 300 },
    restricoes: [],
    proveniencia: {},
    ressalva: null,
  };
  const vm = renderDossie({ status: 200, corpo });
  assert.equal(vm.titulo, "INSC-99");
  assert.deepEqual(vm.restricoes, []);
});

test("404 → sem lote: mensagem + cobertura do município (PAINEL-09)", () => {
  const corpo = {
    tipo: "sem_lote",
    mensagem: "Nenhum lote conhecido aqui.",
    municipio: "Niterói",
    cobertura: [{ camada: "lote_rural", tem_dado: true, data_extracao: "2026-08-20" }],
  };

  const vm = renderDossie({ status: 404, corpo });

  assert.equal(vm.estado, "sem_lote");
  assert.equal(vm.mensagem, "Nenhum lote conhecido aqui.");
  assert.equal(vm.municipio, "Niterói");
  assert.equal(vm.cobertura.length, 1);
  assert.equal(vm.cobertura[0].camada, "lote_rural");
});

test("409 → sobreposição: mensagem + candidatos (PAINEL-10)", () => {
  const corpo = {
    tipo: "sobreposicao",
    mensagem: "Mais de um lote.",
    candidatos: [
      { natureza: "rural", codigo_sigef: "SIGEF-001" },
      { natureza: "rural", codigo_sigef: "SIGEF-002" },
    ],
  };

  const vm = renderDossie({ status: 409, corpo });

  assert.equal(vm.estado, "sobreposicao");
  assert.equal(vm.mensagem, "Mais de um lote.");
  assert.equal(vm.candidatos.length, 2);
  assert.equal(vm.candidatos[1].codigo_sigef, "SIGEF-002");
});

test("429 → cota excedida: mensagem + retry_after (PAINEL-11)", () => {
  const corpo = { erro: "cota de consultas excedida (100/hora)", retry_after_segundos: 1800 };

  const vm = renderDossie({ status: 429, corpo });

  assert.equal(vm.estado, "cota");
  assert.equal(vm.mensagem, "cota de consultas excedida (100/hora)");
  assert.equal(vm.retryAfterSegundos, 1800);
});

test("status inesperado → estado de erro genérico (não quebra a UI)", () => {
  const vm = renderDossie({ status: 500, corpo: {} });
  assert.equal(vm.estado, "erro");
});
