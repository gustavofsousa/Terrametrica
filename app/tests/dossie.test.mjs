// Testes do view model do painel (Fatia 7, T8). Rodar: node --test app/tests/*.test.mjs
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

// ---- spec:mapa-do-lote-rj (T13) ----

test("MAPA-05 422 fora do RJ → estado fora_do_rj com o texto do spec", () => {
  const corpo = { tipo: "fora_do_rj", mensagem: "fora da área de cobertura: apenas RJ" };

  const vm = renderDossie({ status: 422, corpo });

  assert.equal(vm.estado, "fora_do_rj");
  assert.equal(vm.titulo, "Fora do estado do Rio de Janeiro");
});

test("MAPA-05 422 de coordenada inválida (traz erro) não vira fora_do_rj", () => {
  const vm = renderDossie({ status: 422, corpo: { erro: "latitude fora de faixa" } });

  assert.equal(vm.estado, "erro");
  assert.equal(vm.mensagem, "latitude fora de faixa");
});

test("MAPA-18 consulta sem resposta HTTP → estado erro_rede", () => {
  const vm = renderDossie({ erroRede: true });

  assert.equal(vm.estado, "erro_rede");
  assert.equal(vm.titulo, "Não foi possível consultar");
});

test("MAPA-09 rural de 12,4 ha mostra '12,4 ha' e o perímetro em m, com a fonte da área", () => {
  const geometria = { type: "Polygon", coordinates: [[[-43.1, -22.9], [-43.0, -22.9], [-43.1, -22.8], [-43.1, -22.9]]] };
  const fonte = { fonte: "SIGEF", data_extracao: "2026-08-20", link_oficial: "https://sigef" };
  const corpo = {
    tipo: "dossie",
    lote: { natureza: "rural", codigo_sigef: "S1", area_ha: 12.4, perimetro_m: 1530.2, geometria },
    restricoes: [],
    proveniencia: { lote_rural: fonte },
  };

  const vm = renderDossie({ status: 200, corpo });

  assert.equal(vm.area, "12,4 ha");
  assert.equal(vm.perimetro, "1.530 m");
  assert.deepEqual(vm.fonteArea, fonte);
  assert.deepEqual(vm.geometria, geometria);
});

test("MAPA-09 urbano mostra a área em m² e a fonte vem da camada lote_urbano", () => {
  const fonte = { fonte: "SIGeo Niterói", data_extracao: "2026-09-30", link_oficial: "https://sigeo" };
  const corpo = {
    tipo: "dossie",
    lote: { natureza: "urbano", inscricao_cadastral: "INSC-99", area_m2: 300, perimetro_m: 70 },
    restricoes: [],
    proveniencia: { lote_urbano: fonte, lote_rural: { fonte: "SIGEF" } },
  };

  const vm = renderDossie({ status: 200, corpo });

  assert.equal(vm.area, "300 m²");
  assert.equal(vm.perimetro, "70 m");
  assert.deepEqual(vm.fonteArea, fonte);
});

test("MUN-03 404 mostra o nome do município, não o código", () => {
  const corpo = {
    tipo: "sem_lote",
    mensagem: "sem lote mapeado neste ponto",
    municipio: "3304557",
    municipio_nome: "Rio de Janeiro",
    cobertura: [],
  };

  const vm = renderDossie({ status: 404, corpo });

  assert.equal(vm.municipioNome, "Rio de Janeiro");
  assert.equal(vm.rotuloMunicipio, "Rio de Janeiro");
});

test("MUN-03 404 com município null → 'Ponto fora de município mapeado'", () => {
  const corpo = {
    tipo: "sem_lote",
    mensagem: "sem lote mapeado neste ponto",
    municipio: null,
    municipio_nome: null,
    cobertura: [],
  };

  const vm = renderDossie({ status: 404, corpo });

  assert.equal(vm.municipioNome, null);
  assert.equal(vm.rotuloMunicipio, "Ponto fora de município mapeado");
  assert.deepEqual(vm.cobertura, []);
});
