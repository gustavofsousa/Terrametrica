# Lote Urbano de Niterói (F1.9) Validation

**Date**: 2026-10-01
**Spec**: `.specs/features/lote-urbano-niteroi/spec.md`
**Diff range**: `ac73131` (F1.9) + `eb09929` (fix: `lote_rural` coverage). `ba6818c` (AD-014) checked
only through its own tests (see Gate Check).
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

No `tasks.md` exists for this feature. Verified against URB-01..URB-08 in `spec.md`.

| Requirement | Behavior | Regression guard (test) | Notes |
| ----------- | -------- | ----------------------- | ----- |
| URB-01 | ✅ Observed | ✅ Discriminating | Click → `LoteUrbano`, area in m² via `geography` |
| URB-02 | ✅ Observed (live base) | ❌ None | `Sobreposicao` with rural + urban candidates |
| URB-03 | ✅ Observed | ✅ Discriminating | `"0"`/empty inscription → `NULL`; door number `0` omitted |
| URB-04 | ✅ Observed | ✅ Discriminating | Feature without polygon not written, counted |
| URB-05 | ✅ Observed (UC half: test; APP/RL half: live base) | ⚠️ Half | Test fixture has no CAR layer, so the APP/RL exclusion is never exercised |
| URB-06 | ✅ Observed | ✅ Discriminating | Provenance `fonte` = "SIGeo Niterói (Prefeitura de Niterói)" |
| URB-07 | ✅ Observed | ✅ Discriminating | `cobertura` (3303302, `lote_urbano`) `tem_dado=true` |
| URB-08 | ✅ Observed (throwaway probe) | ❌ None | 90% guard rejects a version with fewer urban lots, all pointers stay |

---

## Spec-Anchored Acceptance Criteria

| Criterion | Evidence | Result |
| --------- | -------- | ------ |
| URB-01: click inside a published `lote_urbano` → `lote_em` returns `LoteUrbano` with area in m² computed on `geography` | `tests/integration/ingestao/test_lote_urbano_niteroi.py:82-88`: `isinstance(achado, LoteUrbano)`, municipality/inscription/address/bairro exact, `8_000 < area < 14_000`. Mutation M5 (`ST_Area(geom::geography)` → `ST_Area(geom)`) → `assert 8000 < 9.99e-07` **killed**. Live base, read-only: point in `niteroi:1` → `LoteUrbano(lote_id='niteroi:1', municipio='3303302', inscricao_cadastral='1110560060', area=AreaM2(valor=1042.63), ...)`. | ✅ PASS |
| URB-02: click on urban and rural lot simultaneously → `Sobreposicao` with both candidates | **No test.** Mutation M4 (`(*rurais, *urbanos)` → `tuple(rurais) or tuple(urbanos)`, rural wins silently) **survived** `tests/integration/ingestao tests/integration/persistencia tests/integration/api` (54 passed). Behavior observed on the live base (read-only): `lote_em` at (-43.02198, -22.90254) → `Sobreposicao [('LoteRural', '7785df20-…'), ('LoteUrbano', 'niteroi:9574')]`. | ✅ PASS (behavior), ❌ no regression guard |
| URB-03: `tx_insct` `"0"`/empty or door number `0` → `NULL`/omitted | `tests/unit/ingestao/test_lote_urbano_niteroi.py:9-10` (parametrized `None, "", "  ", "0", nan`); integration `:98` `logradouro == "DAS FLORES"`, `:100` `inscricao_cadastral is None`. M3 (`_INSCRICOES_VAZIAS = {""}`) **killed** (`assert '0' is None`); M6 (door number `0` kept) **killed** (`'DAS FLORES, 0' == 'DAS FLORES'`). Live base: 0 rows with inscription `'0'`/`''`, 0 `logradouro` ending in `, 0`; 7,629 NULL inscriptions = 6,545 `"0"` + 339 blank + 745 null in the raw file (exact match). | ✅ PASS |
| URB-04: feature without polygon → not written, counted in report | `test_lote_urbano_niteroi.py:73-74`: `feicoes_gravadas == 3`, `feicoes_sem_geometria == 1`. M7 (stop reporting the count) **killed** (`assert 0 == 1`). Live base: raw file 82,375 features, 170 without geometry; `lote_urbano` = 82,205 rows (= 82,375 − 170). | ✅ PASS |
| URB-05: UC intersecting an urban lot → `intersecoes_de` returns it; APP/RL SHALL NOT be materialized for urban lots | UC half: `test_lote_urbano_niteroi.py:116-117`: `[UNIDADE_CONSERVACAO]` for the lot it touches, `[]` for the other. APP/RL half: **not exercised by any test.** The fixture ingests only UC, so mutation M1 (remove `AND r.tipo NOT IN ('app', 'reserva_legal')`, `intersecoes.py:49`) **survived** `tests/integration/ingestao tests/integration/persistencia` (65 passed). Behavior observed on the live base (read-only): 72 urban lots spatially intersect `reserva_legal`, yet the urban rows in `intersecao_materializada` are only `('unidade_conservacao', 52431)`, with 0 RL. | ✅ PASS (behavior), ⚠️ negative half has no regression guard |
| URB-06: ingested layer → provenance cites "SIGeo Niterói" | `test_lote_urbano_niteroi.py:126-128`: `fonte == FONTE_SIGEO`, `"Niter" in fonte`, date. M9 (`FONTE_SIGEO = "Prefeitura municipal"`) **killed**. Live base: `('lote_urbano', 'SIGeo Niterói (Prefeitura de Niterói)', 2026-09-30, 'https://sig.niteroi.rj.gov.br/.../FeatureServer/30')`. | ✅ PASS |
| URB-07: `semear_cobertura` → declares `lote_urbano` with data for Niterói | `test_lote_urbano_niteroi.py:136`: `cobertura[LOTE_URBANO].tem_dado is True`. M8 (drop the `_SEMEAR_COBERTURA_LOTE_URBANO` execute) **killed** (`KeyError: LOTE_URBANO`). Live base: `cobertura` for 3303302 has `('lote_urbano', True, 2026-09-30)`; it is the only municipality with `lote_urbano`. | ✅ PASS |
| URB-08: `publicar_versao` → 90% guard includes `lote_urbano` (same atomic pointer, AD-008) | **No test.** Mutation M2 (drop `LOTE_URBANO` from `_CAMADAS_PUBLICADAS`) **survived** `test_publicar.py`, `test_lote_urbano_niteroi.py`, and `tests/unit` (151 passed). Throwaway probe (`scratchpad/probe_urb08.py`, ephemeral PostGIS, not committed): v1 with 3 urban lots published → `('lote_urbano', True, 3, None)`; v2 with 1 urban lot → `('lote_urbano', False, 1, 3)`, all 6 pointers stay `v1` → `URB08_REJECTED`. The same probe under M2 → `URB08_NOT_ENFORCED` (v2 published, no `lote_urbano` pointer). So a test like this would discriminate. Live base: `ponteiro_publicado` has `lote_urbano → rj-2026-10-01`. | ✅ PASS (behavior), ❌ no regression guard |

**Status**: 8/8 requirements observed to behave as specified. 5/8 have discriminating automated
tests. URB-02 and URB-08 have none (as the spec's own Status admits), and the APP/RL half of URB-05 is
not exercised either. The spec does **not** list that last gap.

---

## Discrimination Sensor

Each mutation was applied to a tracked file, the targeted tests ran, and the file was reverted with
`git checkout -- <file>`. After every revert, `git status --short --untracked-files=no` was empty.
Harness: throwaway `scratchpad/mutate.py`.

| # | File:line | Mutation | Tests run | Killed? |
| - | --------- | -------- | --------- | ------- |
| M1 | `ingestao/intersecoes.py:49` | stop excluding `app`/`reserva_legal` for urban lots | `tests/integration/ingestao tests/integration/persistencia` → 65 passed | ❌ Survived |
| M2 | `ingestao/publicar.py:30` | drop `LOTE_URBANO` from `_CAMADAS_PUBLICADAS` | `test_publicar.py test_lote_urbano_niteroi.py tests/unit` → 151 passed | ❌ Survived |
| M3 | `ingestao/lote_urbano_niteroi.py:33` | treat inscription `"0"` as real | unit + integration → `assert '0' is None` | ✅ Killed |
| M4 | `persistencia/repositorio_lotes_postgis.py:104` | rural hit hides urban (no `Sobreposicao`) | `tests/integration/{ingestao,persistencia,api}` → 54 passed | ❌ Survived |
| M5 | `persistencia/repositorio_lotes_postgis.py:55` | area in degrees (no `::geography`) | `test_lote_urbano_niteroi.py` → area assert fails | ✅ Killed |
| M6 | `ingestao/lote_urbano_niteroi.py:130` | keep door number `0` | → `'DAS FLORES, 0' == 'DAS FLORES'` | ✅ Killed |
| M7 | `ingestao/lote_urbano_niteroi.py` (report) | do not report `feicoes_sem_geometria` | → `assert 0 == 1` | ✅ Killed |
| M8 | `ingestao/cobertura.py:80` | skip urban coverage seeding | → `KeyError: LOTE_URBANO` | ✅ Killed |
| M9 | `ingestao/lote_urbano_niteroi.py` | drop SIGeo attribution from `fonte` | → `'Niter' in 'Prefeitura municipal'` | ✅ Killed |
| M10 | `ingestao/cobertura.py` (eb09929) | skip `lote_rural` coverage seeding | `test_cobertura.py` → `KeyError: ('3304557', 'lote_rural')` | ✅ Killed |

**Result**: 7/10 killed. The 3 survivors map exactly to URB-02, URB-08, and the APP/RL half of URB-05.

---

## Removed FK on `intersecao_materializada` (migration 0007)

- **Drop is effective.** Live `pg_constraint` lists only `intersecao_materializada_pkey` and
  `..._restricao_id_versao_base_id_fkey`. The `lote_rural` FK is gone, so the auto-generated name
  matched and `DROP ... IF EXISTS` did not silently no-op. The restriction-side FK still holds.
- **Orphans at insert time: no path found.** The table is written only by the two `INSERT ... SELECT`
  statements in `ingestao/intersecoes.py:20-55`, and both draw `lote_id` from `lote_rural` or
  `lote_urbano` rows of the same version. `grep -rniE "delete from|truncate|drop table" src` finds no
  delete of lot tables (only `sessao`). Live check: 0 rows of `rj-2026-10-01` whose `lote_id` is in
  neither table.
- **Residual orphan risk (not a current bug):** any future cleanup that deletes lot rows of a version
  (for example, discarding a draft) now leaves dangling intersections. Before 0007 the FK blocked
  that.
- **ID collision: none today, but not enforced by the DB.** SIGEF ids are `parcela_co` UUIDs
  (`sigef.py:93`); urban ids are `niteroi:<objectid>`. Live check: 0 rural ids contain `:`, and the
  rural × urban id join returns 0 rows. The `INVARIANT` lives only in code (`PREFIXO_ID`). No `CHECK`
  constraint backs it. If a collision ever happened, the impact is concrete: `ON CONFLICT DO NOTHING`
  would silently drop the urban pair, and `intersecoes_de` (which filters by `lote_id` + version only,
  not by type) would return the rural lot's APP/RL intersections for the urban lot. That would
  violate URB-05 with no error.

---

## Live Base Sanity (read-only, `localhost:5433`, `rj-2026-10-01`, session `read_only=True`)

| Check | Result |
| ----- | ------ |
| `lote_urbano` count / distinct ids / municipalities | 82,205 / 82,205 / 1 (`3303302`) ✅ matches the expected 82,205 |
| ids without the `niteroi:` prefix | 0 |
| `proveniencia` rows for the version | `lote_rural` (SIGEF), `lote_urbano` (SIGeo Niterói), `reserva_legal` (CAR/SICAR), `unidade_conservacao` (INEA/MPRJ) |
| `cobertura` 3303302 | `lote_rural` ✓, `lote_urbano` ✓ (2026-09-30), `reserva_legal` ✓, `unidade_conservacao` ✓ |
| `ponteiro_publicado` | all 6 layers → `rj-2026-10-01`, including `lote_urbano` |

---

## Gate Check

| Command | Result |
| ------- | ------ |
| `.venv/bin/ruff check src tests` | `All checks passed!` (exit 0) |
| `.venv/bin/mypy` | `Success: no issues found in 42 source files` (exit 0) |
| `.venv/bin/pytest tests/unit -q` | `138 passed in 1.67s` |
| `.venv/bin/pytest tests/integration/ingestao tests/integration/api -q` | `72 passed, 5 warnings in 87.09s` (Docker/testcontainers) |
| AD-014 (`ba6818c`) | `pytest tests/unit/api/test_identidade.py tests/unit/api/test_configuracao.py` → 21 passed. The e2e tests `test_sem_credenciais_devolve_200_e_loga_conta_anonima_sem_ip` and `test_cota_vale_por_visitante_anonimo` are inside the 72 above. No mutation run (cheap check only). |

---

## Minor Notes (non-blocking)

- `test_lote_urbano_niteroi.py:138` `assert Camada.APP not in cobertura  # CAR é rural...` is
  vacuous. The fixture ingests no CAR layer, so it would pass regardless. `_SEMEAR_COBERTURA`
  (`cobertura.py:27-43`) also UNIONs urban municipalities into the CROSS JOIN with every
  `restricao.tipo`. An urban-only municipality would therefore get APP/RL `tem_dado=true` rows. That
  is harmless for the dossier (`montagem.py:35-43` filters urban lots to the common restrictions), but
  the comment claims a property the code does not have.
- Spec assumption "Inscrição `0`/vazia → 907 casos" is inaccurate. The raw file has 7,629
  (6,545 `"0"` + 339 blank + 745 null), and all 7,629 are stored as NULL. Behavior is correct; only
  the measured number in the doc is wrong.

---

## Gaps (affect requirement guarantees)

1. **URB-02 has no regression test.** M4 survives the whole integration suite.
2. **URB-08 has no regression test.** M2 survives. The throwaway probe shows a test like
   `probe_urb08.py` discriminates.
3. **URB-05 negative half (APP/RL never materialized for urban lots) has no regression test.** The
   fixture has no CAR layer, so M1 survives. The spec's Status omits this gap.
4. **The prefix `INVARIANT` that replaced the FK is not enforced by the DB.** There is no `CHECK` on
   the id format. A collision would silently violate URB-05 (see FK section).

---

## Summary

**Overall**: ✅ PASS on behavior. ⚠️ 3 requirement clauses lack a regression guard.

**Spec-anchored check**: 8/8 URB requirements observed to hold (5 via discriminating tests, 3 via
live-base read-only probes or a throwaway ephemeral-DB probe).
**Sensor**: 7/10 mutations killed. All 3 survivors are the coverage gaps above.
**Gate**: ruff 0, mypy 0, 138 unit + 72 integration passed, 0 failed, 0 skipped.

**Next steps**: add 3 integration tests: a rural + urban overlap → `Sobreposicao`; a fixture with a
CAR RL polygon over an urban lot → no materialized pair; and URB-08 (shape of `probe_urb08.py`).
Optionally add `CHECK (id LIKE 'niteroi:%')` on `lote_urbano.id` (or a per-municipality prefix
check) so the invariant is enforced by the DB.
