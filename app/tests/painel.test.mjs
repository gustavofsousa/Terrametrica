// Testes da renderização do painel (T17). Rodar: node --test app/tests/*.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { htmlPainel, htmlCarregando, esc } from "../painel.js";
import { renderDossie } from "../dossie.js";

const ATAQUE = `<script>alert("x")</script>`;

test("esc troca os cinco caracteres perigosos", () => {
  assert.equal(esc(`<a href="x">'&'</a>`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;");
});

test("SECURITY nome com <script> em restrição, título e proveniência sai escapado", () => {
  const vm = renderDossie({
    status: 200,
    corpo: {
      lote: { natureza: "rural", codigo_sigef: ATAQUE, area_ha: 1, perimetro_m: 10 },
      restricoes: [{ tipo: "app", nome: ATAQUE, pct_do_lote: 1, categoria: ATAQUE }],
      proveniencia: { lote_rural: { fonte: ATAQUE, data_extracao: "2026-08-20" } },
      ressalva: ATAQUE,
    },
  });

  const html = htmlPainel(vm);

  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("SECURITY nome de município e de cobertura com <script> sai escapado no 404", () => {
  const vm = renderDossie({
    status: 404,
    corpo: {
      mensagem: ATAQUE, municipio: "1", municipio_nome: ATAQUE,
      cobertura: [{ camada: ATAQUE, tem_dado: true }],
    },
  });

  assert.ok(!htmlPainel(vm).includes("<script>"));
});

test("SECURITY link_oficial com javascript: não vira href", () => {
  const vm = renderDossie({
    status: 200,
    corpo: {
      lote: { natureza: "rural", codigo_sigef: "S1", area_ha: 1, perimetro_m: 10 },
      restricoes: [],
      proveniencia: { lote_rural: { fonte: "SIGEF", data_extracao: "2026-08-20",
                                    link_oficial: "javascript:alert(1)" } },
    },
  });

  assert.ok(!htmlPainel(vm).includes("href="));
});

test("MAPA-09 dossiê mostra área, perímetro, fonte e data formatada", () => {
  const vm = renderDossie({
    status: 200,
    corpo: {
      lote: { natureza: "rural", codigo_sigef: "S1", area_ha: 12.4, perimetro_m: 1530.2 },
      restricoes: [],
      proveniencia: { lote_rural: { fonte: "SIGEF", data_extracao: "2026-08-20",
                                    link_oficial: "https://sigef.incra.gov.br" } },
    },
  });

  const html = htmlPainel(vm);

  assert.match(html, /<dt>Área<\/dt><dd>12,4 ha<\/dd>/);
  assert.match(html, /<dt>Perímetro<\/dt><dd>1\.530 m<\/dd>/);
  assert.match(html, /Fonte da medida: <a href="https:\/\/sigef\.incra\.gov\.br"[^>]*>SIGEF · 20\/08\/2026<\/a>/);
  assert.ok(!html.includes("2026-08-20")); // data nunca em ISO cru
});

test("MAPA-18 erro_rede tem a mensagem e o botão 'Tentar de novo'", () => {
  const html = htmlPainel(renderDossie({ erroRede: true }));

  assert.match(html, /Não foi possível consultar/);
  assert.match(html, /<button type="button" data-acao="tentar-de-novo">Tentar de novo<\/button>/);
});

test("MAPA-05 fora_do_rj mostra o texto do spec", () => {
  const html = htmlPainel(renderDossie({ status: 422, corpo: { tipo: "fora_do_rj" } }));

  assert.match(html, /Fora do estado do Rio de Janeiro/);
});

test("MUN-03 sem lote mostra o nome do município, ou o aviso quando é null", () => {
  const nome = htmlPainel(renderDossie({ status: 404, corpo: {
    mensagem: "sem lote", municipio: "3304557", municipio_nome: "Rio de Janeiro", cobertura: [] } }));
  const nulo = htmlPainel(renderDossie({ status: 404, corpo: {
    mensagem: "sem lote", municipio: null, municipio_nome: null, cobertura: [] } }));

  assert.match(nome, /Município: Rio de Janeiro/);
  assert.ok(!nome.includes("3304557"));
  assert.match(nulo, /Município: Ponto fora de município mapeado/);
});

test("MAPA-19 todo resultado tem um título focável (h2 tabindex=-1)", () => {
  for (const vm of [
    renderDossie({ status: 409, corpo: { mensagem: "m", candidatos: [] } }),
    renderDossie({ status: 429, corpo: { erro: "cota", retry_after_segundos: 120 } }),
    renderDossie({ status: 500, corpo: {} }),
    renderDossie({ erroRede: true }),
  ]) {
    assert.match(htmlPainel(vm), /<h2 id="titulo-painel" tabindex="-1">/);
  }
});

test("MAPA-17 o texto de espera é 'Consultando o lote…' com role=status", () => {
  assert.equal(htmlCarregando(), `<p class="dica" role="status">Consultando o lote…</p>`);
});

test("429 mostra a espera em minutos", () => {
  const html = htmlPainel(renderDossie({ status: 429, corpo: { erro: "cota", retry_after_segundos: 1800 } }));

  assert.match(html, /Tente novamente em ~30 min\./);
});
