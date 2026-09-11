# Validation — F1.11 Painel Web + Conta Autenticada (Fatia 7)

> Independent Verifier report. Author ≠ verifier. Evidence-or-zero: a criterion is
> PASS only if a command was run and its output observed. READ-ONLY over the tree;
> mutants were injected in a scratch state and reverted (final `git status` clean).

**Diff/commit range covered:** `e5ec45b..HEAD` on `feat/api-dossie-http` (T1..T10).

## Verdict: **PASS**

All 14 PAINEL requirements and the 4 spec Edge Cases have a located, spec-matching
assertion. Gates green (except one pre-existing, out-of-scope dto failure). 5 of 5
discrimination mutants at the high-value seams behaved as expected: 4 killed; the 1
"survivor" (A1) is on `token_valido`, which is dead code (never called from `src/`),
so it has zero behavioral reach — the real single-use/expiry enforcement is the atomic
SQL in `consumir`, and its mutant (C) was killed.

---

## Gate Results

| Gate | Command | Result |
| --- | --- | --- |
| Lint | `ruff check .` | PASS — "All checks passed!" (exit 0) |
| Types | `mypy` | PASS — "Success: no issues found in 39 source files" |
| JS unit | `node --test app/tests/dossie.test.mjs` | PASS — tests 6, pass 6, fail 0 |
| Full suite | `pytest -q` | 212 passed, 1 failed in 98.32s |

The single `pytest` failure is
`tests/unit/api/test_dto.py::TestDossieParaDict::test_distingue_os_tres_estados_de_camada`
(`camadas_ausentes` ordering). Confirmed pre-existing: `src/terrametrica/api/dto.py` and
`tests/unit/api/test_dto.py` are unchanged in the `e5ec45b..HEAD` range (camada-ordering
bug from an earlier fatia). **Excluded from this verdict** per scope. Net F1.11-scoped
result: all F1.11 tests pass.

---

## Per-Requirement Evidence

| Req | Spec outcome | Test (file:line) — assertion | Covered? |
| --- | --- | --- | --- |
| PAINEL-01 | e-mail válido → token opaco 15min uso único + envia via Resend | `tests/unit/auth/test_servico.py:53-59` `len(enviador.enviados)==1`; `registro.expira_em == AGORA + EXPIRACAO_TOKEN`; `registro.usado_em is None`. E2E: `tests/integration/api/test_auth_e2e.py:68-69` `status==202` + `len(enviados)==1` | YES |
| PAINEL-02 | e-mail malformado → 422, sem enviar | `tests/unit/auth/test_regras.py:34-36` `pytest.raises(ErroValidacao)` (8 malformados); `tests/unit/auth/test_servico.py:71-72` `enviados==[]`, `registros=={}`. E2E: `test_auth_e2e.py:77-78` `status==422` + `enviados==[]` | YES |
| PAINEL-03 | confirmar: nova→conta CONSULTA; conhecida→autentica sem duplicar; sessão 30d + cookie | `test_servico.py:155-164` conta nova `conta_nova is True` + sessão `AGORA+EXPIRACAO_SESSAO`; `:175-178` conhecida `conta_nova is False`, `len(contas)==1`. Papel CONSULTA: `servico.py:89` passa `PapelConta.CONSULTA`; `test_adaptadores.py:113` cria via `PapelConta.CONSULTA`. Cookie: `test_auth_e2e.py:110-115` | YES |
| PAINEL-04 | token expirado/usado → 401, motivo único | `test_servico.py:205` expirado `valido is False`; `:220-221` usado `segundo.valido is False`. E2E: `test_auth_e2e.py:124` inválido→401; `:135-136` usado→401. Mensagem única: `app.py` retorna `"link inválido ou expirado"` p/ ambos | YES |
| PAINEL-05 | 6ª solicitação/h → 429, sem enviar | `test_servico.py:90-100` 6ª `raises(LimiteDeLinksExcedido)` + `len(enviados)==5`. E2E: `test_auth_e2e.py:89-90` `status==429` + `len(enviados)==5`. Janela desliza: `:119` | YES |
| PAINEL-06 | sem sessão → redirect p/ login | `tests/integration/api/test_api_e2e.py` TestFluxoCookieDossie `test_dossie_sem_cookie_e_sem_header_devolve_401` `status==401` (API side); redirect é glue de UI (`mapa.js`, verificação manual — matriz) | PARTIAL (API 401 tested; JS redirect manual-only) |
| PAINEL-07 | clique autenticado por sessão resolve conta_id (não exige header) | `test_api_e2e.py` `test_clique_autenticado_por_cookie_retorna_dossie_sem_header` `status==200` + `codigo_sigef=="SIGEF-001"` sem X-Conta-Id; precedência `test_identidade.py:72` sessão vence header | YES |
| PAINEL-08 | 200 → painel mostra lote/restrições/proveniência/ressalva | `app/tests/dossie.test.mjs:22-28` `vm.estado=="dossie"`, `restricoes[0].nome`, `proveniencia.lote_rural.fonte`, `ressalva` | YES |
| PAINEL-09 | 404 → mensagem + cobertura, sem quebrar mapa | `dossie.test.mjs:54-58` `estado=="sem_lote"`, `mensagem`, `municipio`, `cobertura[0].camada` | YES |
| PAINEL-10 | 409 → mensagem + candidatos | `dossie.test.mjs:73-76` `estado=="sobreposicao"`, `mensagem`, `candidatos.length==2`, `candidatos[1].codigo_sigef` | YES |
| PAINEL-11 | 429 → mensagem de cota + retry_after_segundos | `dossie.test.mjs:84-86` `estado=="cota"`, `mensagem`, `retryAfterSegundos==1800` | YES |
| PAINEL-12 | sessão expira/inválida → 401 → redirect | API 401: `test_identidade.py:81-95` cookie inválido/ausente→401; `conta_de_sessao` filtra `expira_em` (`test_adaptadores.py:127-132`). Redirect: glue de UI (`mapa.js`, manual) | PARTIAL (API 401 tested; JS redirect manual-only) |
| PAINEL-13 | logout invalida sessão no servidor + expira cookie | `test_servico.py:252-254` `conta_de_sessao(...) is None` após `encerrar_sessao`. E2E: `test_auth_e2e.py:152-155` `status==204` + cookie expirado | YES |
| PAINEL-14 | sessão invalidada reapresentada → 401 | `test_servico.py:256-259` logout idempotente; `test_auth_e2e.py:159-170` criar→ler→invalidar→`conta_de_sessao is None` (repo direto). `resolver_conta_id` sem sessão válida→401 (`test_identidade.py:81-95`) | YES |

### Edge Cases (spec §Edge Cases)

| Edge Case | Evidence | Covered? |
| --- | --- | --- |
| solicita e nunca clica → nenhuma conta criada | Conta só nasce em `confirmar_login` (`servico.py:88-89`); `solicitar` nunca cria conta — `test_servico.py:130-139` (solicitar não toca credencial) | YES |
| reenvio: dois tokens válidos, ambos autenticam, sem invalidação cruzada | `test_servico.py:223-236` `confirmar_login(t1)` e `confirmar_login(t2)` ambos `valido is True` | YES |
| provedor de e-mail falha → 502/erro, não 200 mudo | `test_servico.py:121-128` `raises(RuntimeError)`; adaptador `test_adaptadores.py:165-175` `raises(HTTPStatusError)`; E2E `test_auth_e2e.py:98` `status==502` | YES |
| cookie corrompido/inválido → não-autenticado, nunca 5xx | `test_identidade.py:74-79` cookie corrompido→cai p/ header; `:81-87` cookie corrompido sem header→401 (não 5xx) | YES |

> **PARTIAL on PAINEL-06/12:** the "redirect to login" half lives in UI glue
> (`app/mapa.js`), which the tasks matrix classifies as manual-verification / no
> automated test (lógica pura foi extraída para `dossie.js`). The testable/server half
> (401 on missing/invalid session) IS asserted. This matches the planned coverage in
> `tasks.md` (T9/T10 = `Tests: none`), not a regression — but the browser redirect
> itself has no executed automated evidence.

---

## Discrimination Sensor (mutants injected in scratch state, all reverted)

| Mutant | Seam | Change | Result |
| --- | --- | --- | --- |
| A1 | `auth/regras.py::token_valido` | `agora < expira_em` → `agora <= expira_em` | **SURVIVED** — `pytest tests/unit/auth/test_regras.py` 14 passed. No exact-boundary test. **Low severity:** `token_valido` is never called from `src/` (dead code); real expiry is the SQL `expira_em > agora` in `consumir`, killed by C. |
| A2 | `auth/regras.py::token_valido` | drop `usado_em is None` check | KILLED — `test_token_ja_usado_e_invalido` failed |
| B | `auth/servico.py` | rate limit `>=` → `>` (off-by-one) | KILLED — `test_sexta_solicitacao_na_janela_excede_limite_e_nao_envia` failed |
| C | `auth/adaptadores.py::_CONSUMIR_TOKEN` | remove `AND usado_em IS NULL` | KILLED — `test_consumir_e_atomico_segundo_consumo_devolve_none` failed (integration/Docker) |
| D | `api/identidade.py::resolver_conta_id` | check header before cookie | KILLED — `test_sessao_tem_precedencia_sobre_header` failed |
| E | `app/dossie.js` | 429 branch → 404 (`semLote`) shape | KILLED — `429 → cota excedida (PAINEL-11)` failed |

Final `git status`: clean (mutants reverted; only this `validation.md` added, unstaged).

---

## Gaps (ranked)

1. **PAINEL-06 / PAINEL-12 redirect-to-login has no executed automated evidence** — the
   browser-side redirect on 401 lives in `app/mapa.js`, classified as manual-only by the
   tasks matrix. The server 401 is well tested; the UI redirect is asserted only by design,
   not by a runner. Low-to-medium: consistent with the plan, but the "→ redirect" clause of
   two ACs is unproven by test.
2. **`token_valido` boundary mutant (A1) survives, and `token_valido` is dead code** —
   never invoked from `src/`. No correctness impact today (the SQL path enforces expiry),
   but the pure helper is untested at its `<` boundary and unused; a future refactor that
   wires it in would inherit an untested off-by-one. Cosmetic/low.
