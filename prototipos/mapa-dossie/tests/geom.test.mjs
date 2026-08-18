/* Testa as funções de geometria extraídas de index.html — fonte única de verdade.
   Rodar: node prototipos/mapa-dossie/tests/geom.test.mjs   (sem dependências) */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(here, "..", "index.html"), "utf8");
const start = html.indexOf("function area(poly)");
const end = html.indexOf("/* ==========================================================\n   3 ·");
if (start < 0 || end < 0) { console.error("Não localizei o bloco de geometria em index.html"); process.exit(2); }
const mod = path.join(here, ".geom.tmp.mjs");
fs.writeFileSync(mod, html.slice(start, end) +
  "\nexport { area, perimeter, inside, bbox, clipConvex, overlapArea, signedArea };\n");
const G = await import("file://" + mod);
fs.unlinkSync(mod);

let fails = 0;
const ok = (nome, got, exp, tol = 1e-6) => {
  const pass = Math.abs(got - exp) <= tol;
  if (!pass) fails++;
  console.log((pass ? "PASS  " : "FALHA ") + nome + "   got=" + got.toFixed(4) + " exp=" + exp.toFixed(4));
};
const eq = (nome, got, exp) => {
  const pass = got === exp;
  if (!pass) fails++;
  console.log((pass ? "PASS  " : "FALHA ") + nome);
};
const sq = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];

ok("área de quadrado 10x10", G.area(sq(0, 0, 10, 10)), 100);
ok("área independe da orientação", G.area(sq(0, 0, 10, 10).slice().reverse()), 100);
ok("perímetro de quadrado 10x10", G.perimeter(sq(0, 0, 10, 10)), 40);

ok("recorte de 50%", G.area(G.clipConvex(sq(0, 0, 10, 10), sq(5, 0, 10, 10))), 50);
ok("recorte com clip horário", G.area(G.clipConvex(sq(0, 0, 10, 10), sq(5, 0, 10, 10).slice().reverse())), 50);
ok("sujeito contido no clip", G.area(G.clipConvex(sq(2, 2, 4, 4), sq(0, 0, 10, 10))), 16);
ok("polígonos disjuntos", G.area(G.clipConvex(sq(0, 0, 10, 10), sq(50, 50, 10, 10))), 0);

const L = [[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]];   /* sujeito côncavo */
ok("L inteiramente dentro", G.area(G.clipConvex(L, sq(-1, -1, 20, 20))), G.area(L));
ok("L cortado em x<5", G.area(G.clipConvex(L, sq(-1, -1, 6, 20))), 44);

ok("overlapArea soma partes", G.overlapArea(sq(0, 0, 10, 10), [sq(0, 0, 5, 10), sq(5, 0, 5, 10)]), 100);
ok("overlapArea sem intersecção", G.overlapArea(sq(0, 0, 10, 10), [sq(99, 99, 5, 5)]), 0);

eq("ponto dentro", G.inside([5, 5], sq(0, 0, 10, 10)), true);
eq("ponto fora", G.inside([15, 5], sq(0, 0, 10, 10)), false);
eq("bbox", JSON.stringify(G.bbox(sq(2, 3, 4, 5))), JSON.stringify([2, 3, 6, 8]));

console.log(fails === 0 ? "\n>>> todos os testes passaram" : "\n>>> " + fails + " falha(s)");
process.exit(fails === 0 ? 0 : 1);
