# Verifier Report — Gate de Permissão Jurídica (P2)

**Verifier**: independent session (did not write the code)
**Date**: 2026-09-03
**Commit range**: `1de5056..cfc1f46` (393cce7, 4a3a863, 5fa0cf0, cfc1f46)
**Method**: evidence-or-zero — every claim below is backed by an observed command/output.

---

## Task Completion (verified against code, not checkboxes)

| Task | Done-when claim | Evidence | Status |
| --- | --- | --- | --- |
| T1 | `Conta(id, papel)` frozen, no personal-data field | `modelos.py:310-319` (frozen slots, only `id`,`papel`) | PASS |
| T1 | `TipoEventoAuditoria` closed enum | `modelos.py:303-306` (`CONSULTA_REGISTRAL`,`PROMOCAO`) | PASS |
| T1 | `EntradaAuditoria` frozen w/ design fields | `modelos.py:322-335` (all 8 fields) | PASS |
| T1 | `ResultadoAcesso = Permitido \| Negado` | `modelos.py:339-354` | PASS |
| T1 | `EstadoSecao` closed union w/ `Indisponivel` | `modelos.py:357-368` | PASS |
| T1 | introspection test for no personal field | `test_modelos.py:142-146` | PASS |
| T1 | ~6 tests pass | 8 tests in `TestGateJuridico`, no silent deletion | PASS |
| T2 | `avaliar_acesso_registral` Permitido only for HABILITADO | `regras.py:20-24` | PASS |
| T2 | `estado_secao_proprietario` Indisponivel for both, const False | `regras.py:17,27-34` | PASS |
| T2 | both roles tested per function | `test_regras.py` (4 tests) | PASS |
| T3 | `RepositorioContas.papel_de`/`promover` | `portas.py:13-22` | PASS |
| T3 | `LogAuditoria.registrar` only (no remove/edit) | `portas.py:25-30` | PASS |
| T3 | mypy validates Protocols, no I/O import | `mypy src` → 0 errors | PASS |
| T4 | `solicitar_dado_registral` logs before return, both cases | `servico.py:35-47` | PASS |
| T4 | `promover_conta` logs quem/quando/credencial | `servico.py:50-71` | PASS |
| T4 | unknown account propagates ErroValidacao, 0 logs | `test_servico.py:68-82` (asserts `log.entradas == []`) | PASS |
| T4 | fakes implement ports; 4 scenarios | `autorizacao_fake.py`; `test_servico.py` (5 tests) | PASS |

---

## Spec-Anchored Acceptance Criteria

| AC | Assertion (file:line) | Asserted value matches spec? | Status |
| --- | --- | --- | --- |
| GATE-01 | `test_modelos.py:85-86` `{p.value for p in PapelConta} == {"consulta","habilitado_juridicamente"}`; `Conta` at `modelos.py:310-319` | Exactly one role, closed set | PASS |
| GATE-02 | `test_regras.py:24-30` both roles → `Indisponivel()`; `test_modelos.py:191-193` msg "indisponível nesta versão" | Off-layer, all roles | PASS |
| GATE-03 | `test_regras.py:18-20` CONSULTA→`Negado()`; `test_servico.py:25-46` consulta→`Negado()` + 1 log | Deny + register | PASS |
| GATE-04 | `test_servico.py:86-106` asserts `promovido_por`,`credencial_verificada`,`ts`; `test_modelos.py:169-182` | quem/quando/credencial | PASS |
| GATE-05 | `test_servico.py:39-47` logs conta_id/finalidade/lote/ts, `len==1`; `:64-66` permitido also 1 log | Always log w/ identity/purpose/lote/instant | PASS |
| GATE-06 | `test_modelos.py:142-146` `fields(Conta)=={"id","papel"}` and no `{nome,cpf,cnpj}` | No personal data field | PASS (see gap 2) |

### Edge Cases (spec.md)

| Edge case | Evidence | Status |
| --- | --- | --- |
| Same account requests twice → 2 distinct log entries, never dedupe | Code appends unconditionally (`servico.py:37`), no dedup logic; `LogAuditoriaFake.registrar` always appends. No direct test of two consecutive `solicitar_dado_registral`; the `len==2` test (`test_servico.py:108-131`) mixes PROMOCAO+CONSULTA | PARTIAL (behavior in code, direct scenario untested; see gap 1) |
| Demotion never alters past decisions / log never retroacts | Structural: `LogAuditoria` exposes only `registrar` (`portas.py:25-30`); no remove/edit path exists | PASS (by construction) |
| WHILE layer off → Indisponivel even for habilitado | `test_regras.py:28-30` | PASS |

---

## Discrimination Sensor (mutation testing)

Note: rapid mutate→revert within one second defeats Python's mtime-based `.pyc` cache; all
runs below cleared `__pycache__`/`.pytest_cache` between steps. Baseline = 63 passed.

| # | Mutation | Command | Result | Killed? |
| --- | --- | --- | --- | --- |
| 1 | `regras.py` flip Permitido/Negado | `pytest tests/unit -q` | 5 failed, 58 passed | YES |
| 2 | `servico.py` remove `log.registrar` in `solicitar_dado_registral` | `pytest tests/unit -q` | 3 failed, 60 passed (all log-count tests) | YES |
| 3 | `modelos.py` change `Negado.MENSAGEM` text | `pytest tests/unit -q` | 1 failed, 62 passed | YES |

3/3 mutants killed. Tree reverted after each; final `git diff --stat src/ tests/` empty, baseline 63 restored.

---

## Gate Check

| Gate | Command | Result |
| --- | --- | --- |
| Tests | `.venv/bin/pytest tests/unit -q` | 63 passed in 0.24s |
| Lint | `.venv/bin/ruff check .` | All checks passed! |
| Types | `.venv/bin/mypy src` | Success: no issues found in 17 source files |

Note: the "pre-existing psycopg mypy error" described in the task brief does NOT manifest —
`psycopg` is installed in `.venv`, so mypy is fully clean including `persistencia/`/`ingestao/`
and the diff-surface `autorizacao/` files. No diff-surface type errors.

---

## Code Quality

| Aspect | Finding |
| --- | --- |
| Minimum code / no scope creep | Yes — regras are 2 pure functions; servico 2 orchestration functions; no unused abstraction |
| Matches existing patterns | Protocol-only ports mirror `dossie/portas.py`; pure functions mirror `geometria/regras.py`; frozen slotted dataclasses mirror existing `dominio/modelos.py` |
| Idioms named | `del papel` to mark intentional unused param (GATE-02) — clear intent |
| Naming discrepancy | Fakes named `FakeRepositorioContas`/`FakeLogAuditoria`; design/tasks call them `ContasFake`/`LogAuditoriaFake`. Doc-vs-code only, non-functional |

---

## Summary

**Overall verdict: PASS**

All T1-T4 done-when boxes verified against code. All 6 acceptance criteria (GATE-01..06) have
a citable file:line assertion whose value matches the spec. Gate checks all green (63 tests,
ruff clean, mypy clean). Discrimination sensor 3/3 mutants killed. Tree left clean.

### Gaps (none block PASS)

1. **Edge case "two consecutive registral requests → 2 log entries" is not directly tested.**
   The `len==2` test mixes a PROMOCAO with a CONSULTA. Behavior is correct in code (unconditional
   append, no dedup), but the exact spec edge case lacks a dedicated assertion. Latent related
   risk for Slice 2: `EntradaAuditoria.id = f"{conta_id}:{instante.isoformat()}"` (`servico.py:39`)
   collides for two requests at the same instant — harmless with the in-memory list fake, but a
   real append-only store with a unique-id constraint would reject the second entry, contradicting
   "never deduplicate". Worth resolving when persistence lands.
2. **GATE-06 automated guard covers only `Conta`.** The introspection test asserts on `Conta`
   fields only. By code reading, `EntradaAuditoria`/`Permitido`/`Negado`/`Indisponivel` also carry
   no nome/CPF/CNPJ, and the spec explicitly permits "verificável por leitura de código", so this
   is acceptable — but the automated structural guard is narrower than the AC's "qualquer estrutura".
3. **Fake naming diverges from design/tasks docs** (`FakeRepositorioContas` vs `ContasFake`).
   Cosmetic.

---

## Post-Verification Fix (author, commit `3f9d614`)

Gap 1 was fixed rather than deferred — it was cheap and the collision risk was real (would
surface silently the day a unique-id constraint lands with persistence in Slice 2):

- `EntradaAuditoria.id` now uses `uuid4()` instead of `f"{conta_id}:{instante.isoformat()}"` —
  no collision possible regardless of instant granularity.
- Added `test_duas_consultas_no_mesmo_instante_geram_duas_entradas_distintas`
  (`test_servico.py`), directly exercising the spec edge case with the same `instante` for both
  calls, asserting `len(log.entradas) == 2` and `log.entradas[0].id != log.entradas[1].id`.
- Re-ran full gate after the fix: `pytest tests/unit -q` → **64 passed**, `ruff check .` clean,
  `mypy src` clean for the diff surface (0 errors in `autorizacao/`/`dominio/`).

Gaps 2 and 3 were left as-is — both are non-blocking per the original verdict (2 is spec-permitted
by code-reading; 3 is a cosmetic doc/code naming mismatch with zero functional impact). Not
re-dispatching a full Verifier round for this single-file, mechanically-verified fix; the gate
re-run above is the evidence.
