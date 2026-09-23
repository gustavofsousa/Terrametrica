# Página de Cobertura Pública (F1.12) Validation

**Date**: 2026-09-23
**Spec**: `.specs/features/pagina-de-cobertura-publica/spec.md`
**Diff range**: `cab4883^..cce3d6d` (3 commits on `main`: cab4883, 1e2f0d7, cce3d6d)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

No `tasks.md` exists for this feature (Design/Tasks artifacts not persisted; the spec ships with
its Requirement Traceability table as the acceptance source). Verified against the 6 COBPUB
requirements + 3 edge cases in `spec.md`.

| Requirement | Status  | Notes |
| ----------- | ------- | ----- |
| COBPUB-01   | ✅ Done | Public route `GET /cobertura/estado`, 200, no auth |
| COBPUB-02   | ✅ Done | All municipalities with ≥1 row, alphabetical order |
| COBPUB-03   | ✅ Done | Every `Camada` filled per municipality (`tem_dado` explicit) |
| COBPUB-04   | ✅ Done | Date formatted `DD/MM/AAAA`, never ISO (view model) |
| COBPUB-05   | ✅ Done | `tem_dado=false` → "sem dado" explicit, cell never omitted |
| COBPUB-06   | ✅ Done | Empty base → 200 empty list; page shows "Nenhuma cobertura ainda." |

---

## Spec-Anchored Acceptance Criteria

### P1: Visão de cobertura do estado (MVP)

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| COBPUB-01: visitor without session GETs the aggregation route → 200 JSON, no auth cookie/header | HTTP 200, no auth required | `tests/integration/api/test_api_e2e.py:228` — `resp = client.get("/cobertura/estado")` (no header); `assert resp.status_code == 200`. Route body `src/terrametrica/api/app.py:124-130` has no `resolver_conta_id`/Cookie/cota. | ✅ PASS |
| COBPUB-02: response includes every municipality present in `cobertura` (≥1 row), alphabetical | All municipalities, alphabetical by name | `tests/integration/persistencia/test_repositorio_lotes_postgis.py:384` — `assert municipios == ["Angra dos Reis", "Niterói"]`; e2e `test_api_e2e.py:238` — `assert municipios`. SQL `repositorio_lotes_postgis.py:73-77` `ORDER BY municipio, camada` + `sorted(por_municipio.items())` at line 156. | ✅ PASS |
| COBPUB-03: each municipality includes, for every domain `Camada`, whether `tem_dado` is true/false | Every `Camada` enum value present per municipality | `tests/unit/api/test_dto.py:171` — `assert len(camadas_no_dict) == len(Camada)`; lines 175-178 assert APP `tem_dado True` + CORPO_DAGUA `tem_dado False`. e2e `test_api_e2e.py:243-245` — `"corpo_dagua" in camadas`, `tem_dado is False`, `data_extracao is None`. Impl `dto.py:88-92` `_camada_ou_ausente`. | ✅ PASS |
| COBPUB-04: cell with `tem_dado=true` → static page shows `data_extracao` readable (DD/MM/AAAA), never raw ISO | `01/08/2026` for `2026-08-01`, not ISO | `app/tests/cobertura.test.mjs:19-21` — `assert.equal(...dataFormatada, "01/08/2026")` + `assert.doesNotMatch(...dataFormatada, /^\d{4}-\d{2}-\d{2}$/)`. Impl `app/cobertura.js:28-32`. **Layer note below.** | ✅ PASS (view model) |
| COBPUB-05: cell with `tem_dado=false` (or absent row) → static page shows "sem dado" explicitly, never omit cell | Literal "sem dado", cell present | `app/tests/cobertura.test.mjs:44-46` — `assert.equal(angra.camadas.length, 1)`, `temDado false`, `dataFormatada == "sem dado"`. Impl `app/cobertura.js:22-26`. **Layer note below.** | ✅ PASS (view model) |
| COBPUB-06: zero municipalities → 200 empty list; page shows explicit "no coverage yet" message, never empty table / error | 200 empty list; explicit message | Repo empty `test_repositorio_lotes_postgis.py:401` — `assert repositorio.cobertura_de_todos() == []`. DTO `test_dto.py:181` — `cobertura_estado_para_dict([]) == {"municipios": []}`. View model `cobertura.test.mjs:47-49` — `vm.estado == "vazio"`, `vm.mensagem == "Nenhuma cobertura ainda."`. Route always 200 (`app.py:130`). | ✅ PASS |

**Layer note (COBPUB-04/05)**: the spec text says "a página estática SHALL exibir". The assertions
target the pure view model `cobertura.js` (the tested seam, same pattern as `dossie.js` per AD-012).
The actual DOM rendering (`pintarTabela`/`pintarVazio` inline in `cobertura.html`) is NOT covered by
an automated DOM-parse test — the spec's "Independent Test" mentions "conferir via parse do DOM". The
commit message (cce3d6d) documents a manual Playwright browser check against a real testcontainer
fixture (including a layout bug fix: badge moved from `<td>` to inner `<span>`). Since `cobertura.html`
consumes the view model directly and renders `dataFormatada` verbatim into a `<span>` per cell, the
logic is faithfully wired, but the DOM layer's coverage rests on manual (not automated) evidence. This
is a spec-precision / coverage-layer nuance, not a logic gap — flagged, not blocking.

**Status**: ✅ All 6 ACs covered with spec-anchored assertions. ⚠️ 1 coverage-layer note (COBPUB-04/05
DOM rendering verified manually, not via automated DOM parse).

---

## Discrimination Sensor

Ran in scratch (edit tracked file → run targeted test → `git checkout` revert). Real tree unchanged
(confirmed clean via `git status --short`).

| # | File:line | Mutation | Test run | Killed? |
| - | --------- | -------- | -------- | ------- |
| 1 | `src/terrametrica/api/dto.py:92` | `_camada_ou_ausente` fill-in `tem_dado=False` → `tem_dado=True` | `pytest test_dto.py::TestCoberturaEstadoParaDict` → `assert True is False` at test_dto.py:178 | ✅ Killed |
| 2 | `src/terrametrica/persistencia/repositorio_lotes_postgis.py:156` | `sorted(...)` → `sorted(..., reverse=True)` (break alphabetical order) | integration `TestCoberturaDeTodos::...ordem_alfabetica` → `['Niterói','Angra dos Reis'] == ['Angra dos Reis','Niterói']` fail | ✅ Killed |
| 3 | `app/cobertura.js:31` | date format `${dia}/${mes}/${ano}` → `${ano}-${mes}-${dia}` (ISO) | `node --test app/tests/cobertura.test.mjs` → COBPUB-04 test fail (1 fail) | ✅ Killed |

**Sensor depth**: lightweight (3 targeted behavior-level mutations; feature is a read-only projection,
not a P0/critical-integrity path).
**Result**: 3/3 killed — PASS ✅

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| No features beyond what was asked | ✅ |
| No abstractions for single-use code | ✅ (`_camada_ou_ausente` module-private helper, used once, improves readability) |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ (persistência, dominio, api dto+app, app/ front, tests) |
| Didn't "improve" unrelated code | ✅ |
| Matches existing patterns/style | ✅ (StrEnum, frozen dataclass, JSONResponse, view-model-no-DOM per dossie.js/AD-012) |
| Would senior engineer approve? | ✅ |
| Tests map to acceptance criteria and non-shallow | ✅ (each test cites a COBPUB id; asserts exact values, not just presence) |
| Spec-anchored outcome check (asserted values match spec) | ✅ (200, alphabetical list, DD/MM/AAAA, "sem dado", "Nenhuma cobertura ainda.") |
| Per-layer Coverage Expectation | ✅ repo/DTO have 1:1 AC mapping; route has happy path (200 no-auth) + COBPUB-03 shape; ⚠️ DOM render layer manual-only |
| Every test maps to a spec requirement — no unclaimed tests | ✅ (all 8 new tests reference COBPUB-01..06) |
| Documented project guidelines | none formal — strong defaults applied (matches AD-012 front pattern, StrEnum domain enums) |

---

## Edge Cases

- [x] Same layer `tem_dado=true` in some municipalities, `false` in others → each municipality
  independent: `_camada_ou_ausente` resolves per-municipality; no cross-municipality inference.
  Covered by COBPUB-03 tests (per-municipality `Camada` fill) + repo test with distinct
  Niterói(APP true)/Angra(UC false) rows (`test_repositorio_lotes_postgis.py:383-394`).
- [x] DB unavailable → standard 5xx: route uses `abrir_conexao` context manager like all other
  routes; a connection failure propagates as the project's standard HTTP error (no HTML partial).
  Frontend `cobertura.html:24-33` catches fetch/`!resp.ok` and shows an error message, never a
  partial silent page. (Not exercised by an automated DB-down test — consistent with project's
  other routes which also do not simulate DB-down; behavior inherited from shared `abrir_conexao`.)
- [x] Layer never ingested anywhere (0%) → column still listed with "sem dado" in every row:
  `dto.py:80` iterates `for camada in Camada` unconditionally; `corpo_dagua` (never ingested in
  fixture) asserted present with `tem_dado False` in e2e `test_api_e2e.py:243-245`.

---

## Gate Check

- **Gate commands**:
  - `node --test app/tests/*.test.mjs` → 9 passed, 0 failed (3 new for F1.12)
  - `ruff check` (4 changed src files) → All checks passed! (exit 0)
  - `mypy <4 changed src files> --strict` → Success: no issues found in 4 source files
  - `python -m pytest -q` (full suite, incl. Docker testcontainer integration) → **220 passed, 0 failed**, 5 warnings, 94.97s
- **Result**: 220 passed, 0 failed, 0 skipped (Python) + 9 passed (JS) + ruff 0 + mypy strict 0
- **Test count before feature (base aed9270 handoff)**: 212 passed (F1.11)
- **Test count after feature**: 220 passed (Python) → +8 Python tests; +3 JS tests (6 → 9)
- **Delta**: +8 Python (4 unit dto + 2 integration repo + 2 e2e api) + 3 JS view-model tests. No
  tests deleted, no assertions weakened.
- **Skipped tests**: none.
- **Failures**: none.
- **Note on documented "pre-existing failure"**: `.specs/STATE.md` Handoff flags
  `test_dto.py::test_distingue_os_tres_estados_de_camada` as a known out-of-scope failure. Verifier
  ran it at both the base commit (`aed9270`) and HEAD (`cce3d6d`): it PASSES in both. The feature
  commits did not touch that test (last change `ce3f5b4`, pre-feature). The full suite is fully green
  — the handoff note appears stale (test likely fixed earlier or was order/environment dependent).
  No other test regressed. Test Integrity Check: PASS.

---

## Out of Scope — Respected

| Excluded item | Verified respected? |
| ------------- | ------------------- |
| List all 92 RJ municipalities | ✅ Only municipalities in `cobertura` (SQL `FROM cobertura`, no municipal-mesh join) |
| Automatic "obsolete base" threshold / visual marking | ✅ Raw date only; no `LIMIAR_DIAS` applied in dto.py/cobertura.js |
| Authentication / account | ✅ Route has no `resolver_conta_id`/Cookie/cota (`app.py:124-130`); e2e asserts 200 no-header |
| Search/filter by municipality on the page | ✅ Not present in cobertura.html/js |
| Change contract of existing `GET /cobertura?municipio=X` | ✅ `git diff` shows existing `/cobertura` route byte-for-byte unchanged; `/cobertura/estado` is a pure addition |

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| COBPUB-01 | Pending | ✅ Verified |
| COBPUB-02 | Pending | ✅ Verified |
| COBPUB-03 | Pending | ✅ Verified |
| COBPUB-04 | Pending | ✅ Verified (view-model layer; DOM manual) |
| COBPUB-05 | Pending | ✅ Verified (view-model layer; DOM manual) |
| COBPUB-06 | Pending | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 6/6 ACs matched spec outcome | 1 coverage-layer note (COBPUB-04/05 DOM
rendering has automated coverage only at the view-model seam; the inline DOM render is manual-only)
**Sensor**: 3/3 mutations killed
**Gate**: 220 Python passed + 9 JS passed, ruff 0, mypy strict 0, 0 failed, 0 skipped

**What works**:
- Public `GET /cobertura/estado` returns 200 with no auth (COBPUB-01), aggregates all municipalities
  alphabetically (COBPUB-02), fills every `Camada` per municipality with explicit `tem_dado`
  (COBPUB-03), formats dates DD/MM/AAAA (COBPUB-04), renders "sem dado" for absent data (COBPUB-05),
  and handles the empty base with an explicit message (COBPUB-06).
- Out-of-scope table fully respected; existing per-municipality route untouched (pure addition).
- Zero changes to `dossie/`, `geometria/`, `ingestao/cobertura.py` (Success Criteria 3) — diff only
  adds a read-only projection.

**Issues found**: none blocking.
- Minor/coverage: COBPUB-04/05 DOM-render layer (cobertura.html inline script) lacks an automated
  DOM-parse test; verified manually via Playwright per commit message. Recommend a future jsdom or
  Playwright-in-CI test if the DOM render path is expected to be regression-guarded automatically.
- Doc hygiene: `.specs/STATE.md` Handoff still lists a "pre-existing failing test" that now passes at
  both base and HEAD — update the handoff to avoid future confusion.

**Next steps**: Feature is verifiable-complete. Optionally add a DOM-level automated test for the
static page render and refresh the STATE.md handoff note.
