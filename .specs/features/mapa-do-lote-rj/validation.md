# Mapa do Lote no RJ (F1.8 + F1.13) Validation

**Date**: 2026-10-14
**Spec**: `.specs/features/mapa-do-lote-rj/spec.md`
**Diff range**: `646dc17..2113479` (25 task commits T1..T25 + 3 fix commits `d563f85`, `038f158`, `2113479`)
**Iterations**: 1 (at `9c8dbb3`): FAIL, 11/13 mutants killed. 2 (at `2113479`): PASS, see "Re-verification (iteration 2)".
**Verifier**: independent sub-agent (author != verifier)
**Verdict**: **PASS** (iteration 2). All 29 ACs and all 5 edge cases have spec-anchored tests. The two
mutants that survived iteration 1 are now killed (sensor 13/13), and 3 extra mutants against the new
tests are killed too. The iteration-1 text below is kept as history, and each closed gap is marked.

---

## Re-verification (iteration 2, HEAD `2113479`)

### Gates (re-run in the real tree)

| Gate | Result |
| --- | --- |
| `.venv/bin/ruff check src tests` | exit 0 |
| `.venv/bin/mypy` | exit 0, 43 files |
| `.venv/bin/pytest tests/unit tests/integration -q` | exit 0, **294 passed** (+2) |
| `node --test app/tests/*.test.mjs` | exit 0, **50 pass**, 0 fail |
| `.venv/bin/pytest tests/navegador -m navegador -q` | exit 0, **29 passed** (+2) |

### Sensor re-run (scratch worktree at `2113479`, removed afterwards)

| # | Mutation | Killed by | Result |
| --- | --- | --- | --- |
| M9 | `duration: 600` always (reduced-motion branch removed) | `tests/navegador/test_mapa.py:158` `duracoes_dos_enquadramentos(pagina) == [0]` | Killed, 2/2 runs |
| M13a | `maxZoom: 18` (the pre-fix value) | `test_mapa.py:183` `assert zoom == maximo` | Killed |
| M13b | `maxZoom: 10` | `test_mapa.py:183` | Killed |
| M14 | `dragend` also calls `consultas.consultar` | `test_mapa.py:92` `assert not [u ... "/dossie?" in u]` | Killed |
| M15 | `ST_SimplifyPreserveTopology` in `geometrias_de` | `tests/integration/api/test_api_e2e.py:253` `len(_vertices(...)) == 2301` | Killed |
| M16 | rollback also runs `DELETE FROM limite_estado` | `tests/integration/persistencia/test_migracao_municipio.py:181` `status_code == 200` | Killed |

Unmutated control: `-k "mapa08 or edge_lote"` → 4 passed.
**Sensor total**: the 13 original mutants are now all killed (13/13), plus 3/3 new ones.

### Gaps from iteration 1

| Gap | Fix | Evidence | Status |
| --- | --- | --- | --- |
| 1. MAPA-08 reduced-motion test did not discriminate | `d563f85`: spy on the `fitBounds` `duration` | `test_mapa.py:158` `== [0]` with reduce; mirror `test_mapa.py:170` `duracoes[0] > 0` without; M9 killed | Closed |
| 2. Tiny lot: fixed `maxZoom: 18`, no test | `d563f85`: `app/mapa.js:264` `maxZoom: mapa.getMaxZoom()`; seeded `TINY-1` (~1 m) | `test_mapa.py:172-184` zoom == `getMaxZoom()` and lot selected; M13a/b killed | Closed. NOTE: `getMaxZoom()` is the map's camera max (22, default). The positron style sets no root max zoom, so this is the correct reading of "the style's max zoom" |
| 3a. Drag without click: no assertion | `038f158` | `test_mapa.py:91-92`; M14 killed | Closed |
| 3b. Largest lot (2,301 vertices): no suite test | `038f158` | `test_api_e2e.py:221-253` via `/dossie`; M15 killed | Closed |
| 4. MUN-09: no `/dossie` after rollback; wording | `2113479`: new test; spec MUN-09 now names the `municipio` pointer row and `proveniencia.sha256` | `test_migracao_municipio.py:164-182` 200 + `lote_id == "L1"`; spec.md MUN-09 row; M16 killed | Closed |
| 5. MAPA-01 proven only by the verifier's live probe | Accepted by the coordinator: the suite intercepts the style on purpose | Iteration-1 probe output (below) | Accepted, not a gap |

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1..T25 | Done | 25 commits in range; all `Done when` boxes in `tasks.md` are checked |

---

## Gate Check

| Gate | Command | Result |
| --- | --- | --- |
| Lint | `.venv/bin/ruff check src tests` | exit 0, "All checks passed!" |
| Types | `.venv/bin/mypy` | exit 0, "no issues found in 43 source files" |
| Python | `.venv/bin/pytest tests/unit tests/integration -q` | **292 passed**, 0 failed, 0 skipped (156 s) |
| JS | `node --test app/tests/*.test.mjs` | exit 0, **50 pass**, 0 fail |
| Browser | `.venv/bin/pytest tests/navegador -m navegador -q` | **27 passed**, 0 failed (58 s) |

- **Test count before feature** (`646dc17`, collect-only): 250 Python, 9 JS, 0 browser.
- **After**: 292 Python (+42), 50 JS (+41), 27 browser (+27).
- **Removed tests**: `test_levanta_not_implemented_citando_td_001` (TD-001 closed by MUN-02, replaced by
  `test_mun02_*`) and `test_agrega_todos_os_municipios_em_ordem_alfabetica` (replaced by
  `test_mun08_agrega_os_municipios_da_malha_com_nome_em_ordem_alfabetica`). Both removals follow the spec.

---

## Spec-Anchored Acceptance Criteria

| AC | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| MAPA-01 | MapLibre 6.14.0 + OpenFreeMap positron; attribution OSM + OpenFreeMap; no `tile.openstreetmap.org` | `tests/navegador/test_mapa.py:56` `assert not [u ... "tile.openstreetmap.org" in u]`; `:63-64` `to_contain_text("OpenStreetMap"/"OpenFreeMap")` | PASS. NOTE: the suite stubs the style and injects the attribution text itself. Verifier probe on the real network: hosts = 127.0.0.1, fonts, `tiles.openfreemap.org` (8 `.pbf`), `unpkg.com/maplibre-gl@6.14.0`; 0 OSM tile requests; attribution "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" |
| MAPA-02 | camera frames RJ bbox; drag not locked | `test_mapa.py:73-75` centre in bbox, `getMaxBounds() is None`; `:86` centre moves after drag | PASS |
| MAPA-03 | style fails → "Mapa base indisponível" | `test_mapa.py:109` `to_have_text("Mapa base indisponível")`, `:112` click still answers | PASS |
| MAPA-04 | RJ outline from published version + dim outside | `tests/integration/api/test_api_e2e.py:267-290` 200 Feature/MultiPolygon, ETag, 304; `test_repositorio_lotes_postgis.py:593` valid MultiPolygon, fewer vertices; `app/tests/geometria.test.mjs:46-78` mask holes; `test_mapa.py:97-101` layer order + `0<opacity<1`; `test_versao.py:82` 503 without version | PASS |
| MAPA-05 | 422 → `fora_do_rj`, "Fora do estado do Rio de Janeiro", never "Erro inesperado" | `app/tests/dossie.test.mjs:101-102`; `test_mapa.py:160-161` | PASS |
| MAPA-06 | 200 body `lote.geometria` Polygon/MultiPolygon, `[lon,lat]`, <= 6 decimals | `test_api_e2e.py:176-183` type, lon in [-43.105,-43.095], lat in [-22.905,-22.895], decimals <= 6; `test_repositorio_lotes_postgis.py:542` | PASS (mutant M1 lon/lat swap killed) |
| MAPA-07 | 409: every candidate has `geometria` | `test_api_e2e.py:213-217` ids == {OVL-1,OVL-2}, each has type + >= 4 vertices | PASS |
| MAPA-08 | draw lot as selected, frame it with padding outside the panel; no animation under reduced motion | `test_mapa.py:124-140` selected ids, corners inside free canvas; `:151` `isMoving() is False` | **PARTIAL**: framing PASS; reduced-motion test does NOT discriminate (mutant M9 survived 3/3). Probe proves the code is right: `isMoving` right after result = False (reduce) / True (normal) |
| MAPA-09 | area ha (rural) / m² (urbano), perimeter m, with source + date | `dossie.test.mjs:131-133,148-150`; `painel.test.mjs:69-72` `<dd>12,4 ha</dd>`, `1.530 m`, "SIGEF · 20/08/2026" | PASS |
| MAPA-10 | `consulta_log` keeps the same columns, no geometry | `test_api_e2e.py:264` `colunas == {"id","ts","conta_id","lote_id","camadas","latencia_ms"}` | PASS (verifier re-checked: migration 0008 does not touch `consulta_log`) |
| MAPA-11 | only the last click's answer reaches map/panel | `app/tests/consultas.test.mjs:34-36,50-56` | PASS (mutant M6 killed) |
| MAPA-12 | all candidates drawn distinguishably, not as selected; list highlights hovered | `test_mapa.py:248-253` ids, selected empty, dasharray; `:265-269` hover state + `is-hover`; `painel.test.mjs:134-137` distinct colour vars | PASS |
| MAPA-13 | valid in-bbox params → query; invalid/out-of-bbox → ignored, no request | `app/tests/url.test.mjs:7-31`; `test_mapa.py:286` lot selected from URL; `:296` no `/dossie?` request | PASS (mutant M7 killed) |
| MAPA-14 | URL `?lat=&lon=` 6 decimals via replaceState; Esc clears | `url.test.mjs:35-41`; `test_mapa.py:309-311` `history.length` unchanged + URL suffix; `:323-326` Esc clears | PASS |
| MAPA-15 | <= 640 px → bottom sheet <= 50% height, map full width, lot above sheet | `test_mapa.py:344-356` height <= 422, bottom 844, width 390, corners above sheet | PASS |
| MAPA-16 | map receives taps in the visible area | `test_mapa.py:380` `elementFromPoint == "CANVAS"`, `:384` tap answers | PASS |
| MAPA-17 | `aria-busy="true"` + "Consultando o lote…"; previous lot not selected while waiting | `test_mapa.py:437-440`; `painel.test.mjs:111` | PASS (mutant M10 killed) |
| MAPA-18 | network failure → message + "Tentar de novo" repeats the same point | `test_mapa.py:454-464` two identical `/dossie?` URLs; `consultas.test.mjs:74,89` | PASS |
| MAPA-19 | focus to panel title + `aria-live`; never steal focus mid-drag | `test_mapa.py:473-476`; `:496` focus not moved during drag | PASS |
| MUN-01 | 92 municipalities (code + name + geom) in the building version | `tests/integration/ingestao/test_municipios_rj.py:80-88`; `test_publicar_municipio.py:62` | PASS |
| MUN-02 | `municipio_em` returns the containing municipality's IBGE code, version-scoped | `test_repositorio_lotes_postgis.py:469,486,498,520` | PASS (mutant M4 killed) |
| MUN-03 | 404 has `municipio`, `municipio_nome`, municipality coverage; panel shows the name | `test_api_e2e.py:229-231`; `tests/unit/dossie/test_montagem.py:112-114`; `dossie.test.mjs:164-165`; `painel.test.mjs:94-95` | PASS. Note: the API test only asserts `isinstance(cobertura, list)`; the unit test carries the value check (mutant M11 killed there) |
| MUN-04 | != 92, non-`33` code, empty geometry → fail with count; version not published | `tests/unit/ingestao/test_municipios_rj.py:16-48`; `test_municipios_rj.py:124-130` (int) "91 feições" + 0 rows; `test_publicar_municipio.py:75` | PASS (mutants M2, M3 killed) |
| MUN-05 | provenance: "IBGE — Malha Municipal", year, extraction date, SHA-256 of canonical GeoJSON | int `test_municipios_rj.py:117-119` tuple equality; unit `:50-59` order-independent + content-sensitive SHA | PASS |
| MUN-06 | ingest twice → 92 rows | int `test_municipios_rj.py:90-102` 92 rows + 1 provenance row | PASS |
| MUN-07 | one row per municipality × layer, `tem_dado=false` where no data | `tests/integration/ingestao/test_cobertura.py:248-288,290-` exact dict equality | PASS (3-municipality fixture; logic is set-generic; the 92 count is asserted at the API, `test_api_e2e.py:424`) |
| MUN-08 | 92 municipalities by name, alphabetical | `test_api_e2e.py:430-435` `len == 92`, `nomes == sorted(nomes)`; `test_repositorio_lotes_postgis.py:375,431`; `app/tests/cobertura.test.mjs:63-66` | PASS |
| MUN-09 | rollback removes only the malha table + its provenance rows; previous versions keep serving `/dossie` 200 | `tests/integration/persistencia/test_migracao_municipio.py:133-152` counts unchanged, table gone | PASS with gap: the suite never calls `/dossie` after rollback (the spec's stated verification). Verifier probe: `/dossie` at the seeded lot = 200 before and after rollback. Mutant M12 (rollback deletes `lote_rural`) killed |
| DOC-01 | README "Estado atual" lists API, panel, coverage page, deploy, this feature; no "zero código" | `README.md:13-32` (manual review); `grep "zero código\|camada HTTP" README.md` → no match | PASS |

**Status** (iteration 1): all 29 ACs have evidence; MAPA-08 partial. **Iteration 2**: MAPA-08 PASS (gap 1 closed), so 29/29.

---

## Edge Cases

- [x] Click in the sea inside RJ → 404 `municipio: null`, "Ponto fora de município mapeado":
  `test_api_e2e.py:245-247`, `dossie.test.mjs:179-181`, `painel.test.mjs:96`.
- [x] MultiPolygon with distant parts → bbox covers all: `app/tests/geometria.test.mjs:15-24`.
- [x] (closed in iteration 2: `test_mapa.py:172-184`) Lot smaller than one pixel → zoom to the style's max zoom: **no test**. Code caps at a fixed
  `maxZoom: 18` (`app/mapa.js:264`), not the style's max zoom. Mutant M13 (`maxZoom: 10`) survived.
- [x] (closed in iteration 2: `test_api_e2e.py:221-253`) Largest SIGEF lot (2,301 vertices) → full geometry, not simplified: **no test in the suite**.
  Verifier probe: a 2,301-vertex polygon came back from `geometrias_de` with 2,301 vertices.
- [x] (closed in iteration 2: `test_mapa.py:91-92`) Drag without click → no query: **no assertion in the suite**. The MAPA-02 drag test does not
  check requests. Verifier probe (real network): 0 `/dossie?` requests after a drag.

---

## Discrimination Sensor

Run in a scratch `git worktree` at HEAD (removed afterwards; real tree unchanged). Targeted tests per mutant.

| # | File | Mutation | Killed? |
| --- | --- | --- | --- |
| M1 | `persistencia/repositorio_lotes_postgis.py` | `ST_FlipCoordinates` in `geometrias_de` (lat/lon swap) | Killed (`test_mapa06_lote_rural_e_urbano...`) |
| M2 | `ingestao/publicar.py` | drop `CAMADA_MUNICIPIO` from `_CAMADAS_PUBLICADAS` | Killed (2 tests in `test_publicar_municipio.py`) |
| M3 | `ingestao/municipios_rj.py` | `TOTAL_MUNICIPIOS_RJ = 91` | Killed (2 unit tests) |
| M4 | `persistencia/repositorio_lotes_postgis.py` | `municipio_em` ignores `versao_base_id` | Killed (`test_mun02_mesma_coordenada_em_duas_versoes...`) |
| M5 | `persistencia/repositorio_lotes_postgis.py` | drop `ST_Multi` in contorno | Killed (`test_mapa04_contorno_e_multipolygon...`) |
| M6 | `app/consultas.js` | `maisRecente = () => true` | Killed |
| M7 | `app/url.js` | remove bbox checks in `lerSelecao` | Killed |
| M8 | `app/painel.js` | `esc()` returns input unchanged | Killed |
| M9 | `app/mapa.js` | `duration: 600` always (no reduced-motion branch) | **Survived** (3/3 runs) |
| M10 | `app/mapa.js` | drop `aria-busy="true"` on query start | Killed (`test_mapa17_...`) |
| M11 | `dossie/montagem.py` | `SemLote` with empty coverage even with a municipality | Killed (unit `test_sem_lote_devolve_municipio...`) |
| M12 | `migracoes/rollback/0008...down.sql` | rollback also `DELETE FROM lote_rural` | Killed (`test_mun09_rollback...`) |
| M13 | `app/mapa.js` | `maxZoom: 18` → `10` | **Survived** (edge case uncovered) |

**Sensor depth**: expanded (13 manual mutants). **Result (iteration 1)**: 11/13 killed — FAIL. **Iteration 2**: M9 and M13 killed, 13/13 — PASS.

Why M9 survives: `test_mapa08_com_movimento_reduzido_o_enquadramento_nao_anima` waits for the panel
text with Playwright's polling (100/250/500 ms steps). The 600 ms animation has usually finished
before `isMoving()` is read. A probe that waits with `polling="raf"` discriminates: `isMoving()` =
False with reduce, True without.

---

## Author-declared deviations (`.specs/STATE.md` Handoff) — judgement

- JS gate uses the glob form: accepted (verified exit 0, 50 tests).
- T6 touched `api/dto.py` and two existing tests: accepted, forced by the `SemLote.municipio` type change.
- Three e2e fixtures seed the malha: accepted, no assertion weakened (diff shows only added lines there).
- T9 `JOIN` with the published malha: accepted, it is what MUN-08 asks (names from the malha).
- T13 422 with `erro` → `erro` state: accepted; MAPA-05 is about "fora do RJ", not invalid input.
- MAPA-12 only `hover`: accepted; the spec asks for highlight under the cursor, not a selected state.
- Synthetic RJ limit in the browser DB: accepted, but it means MAPA-01 is proven against the real
  OpenFreeMap style only by the verifier probe, not by the suite.
- **Not declared**: the rollback also deletes the `municipio` row of `ponteiro_publicado` and drops
  `proveniencia.sha256`. MUN-09 says "remove só a tabela da malha e as linhas da malha em
  `proveniencia`" and lists `ponteiro_publicado` under "must not alter". Removing the pointer of a
  dropped layer is the coherent choice; the spec wording needs a one-line clarification.

---

## Code Quality (spot-check)

| Check | Status |
| --- | --- |
| Minimum code / surgical changes | OK — changes stay within the feature surface |
| Spec-anchored asserted values | OK except MAPA-08 reduced motion |
| Per-layer coverage (routes happy + edge + error) | OK for `/mapa/contorno` (200, 304, 503) and `/dossie` 200/404/409/422 |
| Every new test maps to an AC / edge / Done-when | OK (spec IDs in names) |
| Guidelines followed | `~/.claude/CLAUDE.md`, `pyproject.toml` (ruff, mypy strict) |

---

## Fix Plans

### Fix 1: make the reduced-motion test discriminate (MAPA-08) — Minor
- **Root cause**: the test reads `isMoving()` after a polling wait that outlasts the 600 ms animation.
- **Fix task**: wait for the panel title with `wait_for_function(..., polling="raf")` (or hold
  `/dossie` with `page.route` and read `isMoving()` in the same frame as the result). Add the mirror
  assertion (`isMoving() is True` without reduced motion) so the test proves it can see motion.
- **Done when**: mutant M9 (`duration: 600` always) fails the test.

### Fix 2: cover the three uncovered edge cases — Minor
- Drag without click: add `assert not [u for u in requisicoes if "/dossie?" in u]` after the drag in
  `test_mapa02_...`.
- Largest lot: integration test that stores a 2,301-vertex polygon and asserts `geometrias_de`
  returns 2,301 vertices.
- Tiny lot: decide the rule. Either use the style's max zoom (spec text) or amend the spec to the
  fixed cap of 18. Then add an e2e that clicks a sub-pixel lot and asserts `getZoom()` equals it.

### Fix 3: MUN-09 suite gap + wording — Cosmetic
- Add `/dossie` 200 after rollback to `test_migracao_municipio.py` (the spec's stated verification).
- Amend MUN-09 wording to allow removing the `municipio` pointer row and the `sha256` column.

---

## Summary

**Overall (iteration 2)**: Ready. 29/29 ACs, 5/5 edge cases, sensor 13/13 (+3/3 new), gates 294 + 50 + 29 passed.

**Iteration 1 summary (history)**: Issues (test gaps only; no product defect observed).
**Spec-anchored check**: 28/29 ACs fully matched; MAPA-08 partial; 3/5 edge cases lack suite tests.
**Sensor**: 11/13 killed (M9, M13 survived).
**Gate**: ruff 0, mypy 0, 292 + 50 + 27 passed, 0 failed.
**Not proven by this run**: the production deploy path (the production base has no `municipio`
layer yet — see the WARNING in the STATE handoff).
