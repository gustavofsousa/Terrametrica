# Painel Web + Conta Autenticada (F1.11) Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/painel-web-conta/design.md`
**Spec**: `.specs/features/painel-web-conta/spec.md`
**Status**: Done

> Nomenclatura: esta é a **Fatia 7** na sequência de execução do repo (após Fatia 6 = F1.10 API HTTP).
> A migração segue o padrão de nome do repo: `0006_fatia7_auth.sql`.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec — confirm before Execute.
> **Guidelines found:** `~/.claude/CLAUDE.md` (AGENTS.md — "tests derive from acceptance criteria,
> não espelham implementação"; "match the codebase you're in"), `pyproject.toml` (ruff select E/F/I/UP/B,
> mypy strict, pytest `testpaths=tests`). Nenhum threshold de cobertura configurado → aplica-se o forte
> default (toda AC + todo edge case), limitado pela convenção do repo (testes por camada técnica —
> divergência consciente de `domain-first-structure §5` já registrada no design, seção Testing Seams).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| `auth/regras.py` (funções puras) | unit | Todas as branches; 1:1 com ACs de validação/token (PAINEL-02/04); edge de e-mail malformado | `tests/unit/auth/test_regras.py` | `pytest tests/unit` |
| `auth/servico.py` (orquestração) | unit (com fakes das ports) | 1:1 com ACs P1/P2; todos os edge cases da spec (reenvio, expirado/usado, falha do enviador, conta nova vs conhecida) | `tests/unit/auth/test_servico.py` | `pytest tests/unit` |
| `auth/adaptadores.py` (Postgres + Resend) | integration | Caminhos-chave de query (consumir atômico, contar janela, criar/ler sessão) + erro; `EnviadorResend` com transporte fake | `tests/integration/auth/test_adaptadores.py` | `pytest tests/integration` |
| `api/identidade.py` (dependency estendida) | integration (e2e via TestClient) | cookie válido→conta; sem cookie→header; nenhum→401; **header sozinho ainda funciona** (retrocompat F1.10) | `tests/integration/api/test_identidade_sessao.py` | `pytest tests/integration` |
| Rotas `/auth/*` (`api/app.py`) | integration (e2e via TestClient) | Toda rota: happy + edge + error — 202/422/429/502 (solicitar); 302+Set-Cookie vs 401 (confirmar); 204+cookie expirado (logout); clique autenticado por cookie retorna dossiê | `tests/integration/api/test_auth_e2e.py` | `pytest tests/integration` |
| Migração `0006_fatia7_auth.sql` | integration | Idempotência (aplicar 2×) + tabelas/índices criados | reusa `tests/integration/persistencia/test_migrar.py` | `pytest tests/integration` |
| Módulos JS do front (`app/dossie.js`) | unit (`node --test`) | render de 200/404/409/429 a partir de JSON fixo de `dossie_para_dict` | `app/tests/dossie.test.mjs` | `node --test app/tests/` |
| Front HTML/CSS/glue (`login.html`, `index.html`, `mapa.js`) | none — verificação manual + UX DoD | — (sem lógica pura testável; UX DoD no `Done when`) | `app/` | verificação manual |

**Coverage Expectation** setado pelo forte default (sem threshold configurado no repo), respeitando a
convenção de camada técnica já existente em `tests/unit/<modulo>` e `tests/integration/api`.

## Parallelism Assessment

> Generated from codebase — confirm before Execute.

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --------- | -------------- | --------------- | -------- |
| unit (auth regras/servico) | Yes | Fakes em memória por teste, sem estado global compartilhado | `tests/fakes/autorizacao_fake.py` (fakes por instância); `tests/unit/autorizacao/test_servico.py` |
| unit JS (`node --test`) | Yes | Módulo puro, entrada por argumento | `prototipos/mapa-dossie/tests/geom.test.mjs` |
| integration (Postgres via `TestContainers`) | No | `PostgresContainer` por módulo + migrações compartilhadas; estado de banco compartilhado dentro do módulo | `tests/integration/api/test_api_e2e.py` (container `scope=module`, fixtures compartilhadas) |

**Regra aplicada:** tasks cujo tipo de teste é integration → `[P]` removido (rodam sequencial). Só
tasks de unit (auth puro, JS) podem levar `[P]`.

## Gate Check Commands

> Generated from codebase — confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks só com unit (auth regras/servico) | `pytest tests/unit -q` |
| Full | Após tasks com integration (adaptadores, identidade, rotas) | `pytest -q` (roda unit + integration; exige Docker p/ TestContainers) |
| Build | Após conclusão de fase / tasks de config/migração | `ruff check . && mypy && pytest -q` |
| JS | Após tasks do front com módulo JS | `node --test app/tests/` |

> `mypy` lê `files=["src"]` do `pyproject.toml`; `ruff check .` cobre `src` + `tests`.

---

## Execution Plan

### Phase 1: Fundação — schema + deps + regras puras (Sequential)

Base sem I/O de rede/banco de aplicação. Migração, promoção de `httpx`, regras puras e contratos.

```
T1 → T2 → T3
```

### Phase 2: Núcleo de auth — serviço + adaptadores (Sequential*)

O serviço orquestra regras+ports (fakes); os adaptadores implementam as ports contra Postgres/Resend.
`*` sequencial porque T5 (adaptadores) usa integration (não parallel-safe) e T4 é pré-req conceitual
de bootstrap, mas T4/T5 tocam arquivos distintos — ver mapa.

```
T3 → T4 → T5
```

### Phase 3: Integração na API — identidade + rotas (Sequential)

Nova via de identidade (sessão OU header) e as 3 rotas finas de auth, provadas por e2e via `TestClient`.

```
T5 → T6 → T7
```

### Phase 4: Front vanilla — login + mapa + painel (Parallel parcial)

Evolui `prototipos/mapa-dossie/`. `dossie.js` é módulo puro testável (`[P]`); o resto é glue manual.

```
T7 ──┬→ T8  (dossie.js render + node --test) [P]
     ├→ T9  (login.html + solicitar) [P]
     └→ T10 (index.html + mapa.js + fetch autenticado) → depende de T8
```

---

## Task Breakdown

### T1: Migração `0006_fatia7_auth.sql` + promover `httpx` a runtime

**What**: Criar a migração idempotente com `credencial_login`, `login_token`, `sessao` (+ índices) e mover `httpx` de `optional.dev` para `dependencies` no `pyproject.toml`.
**Where**: `src/terrametrica/persistencia/migracoes/0006_fatia7_auth.sql` (novo), `pyproject.toml` (modify)
**Depends on**: None
**Reuses**: padrão idempotente `IF NOT EXISTS` de `0005_fatia6_consulta_log.sql`; harness `tests/integration/persistencia/test_migrar.py`
**Requirement**: PAINEL-01/03/05 (schema que os requisitos precisam)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] As 3 tabelas + 2 índices do design (design.md §Data Models) criados exatamente como especificado (PII isolada de `Conta`, hash de token/sessão, nunca o valor)
- [ ] Migração é idempotente: `test_migrar.py` prova aplicar 2× sem erro (estende o teste existente para incluir a `0006`)
- [ ] `httpx` aparece em `[project.dependencies]` (não mais só em `dev`)
- [ ] Gate check passes: `ruff check . && mypy && pytest tests/integration/persistencia/test_migrar.py -q`
- [ ] Test count: teste de migração passa incluindo a nova migração

**Tests**: integration
**Gate**: build
**Commit**: `feat(auth): migração 0006 (credencial_login/login_token/sessao) + httpx runtime (Fatia 7, T1)`

---

### T2: `auth/regras.py` — regras puras de auth

**What**: Funções puras sem I/O: `validar_email`, `gerar_token_opaco`, `hash_token`, `token_valido`, `Email` value object.
**Where**: `src/terrametrica/auth/regras.py` (novo), `src/terrametrica/auth/__init__.py` (novo)
**Depends on**: None
**Reuses**: padrão de value object validado do `dominio` (`Coordenada`/`ErroValidacao` em `dominio/modelos.py`); `secrets`, `hashlib` (stdlib)
**Requirement**: PAINEL-02 (e-mail malformado→422), PAINEL-04 (token expirado/usado)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `validar_email(bruto)` normaliza (lower/trim) e levanta `ErroValidacao` em e-mail malformado (narrow no boundary)
- [ ] `gerar_token_opaco()` usa `secrets.token_urlsafe` (alta entropia); `hash_token` é determinístico (sha256)
- [ ] `token_valido(registro, agora)` = não expirado E não usado
- [ ] Testes unit cobrem: e-mail válido normalizado, e-mail malformado→`ErroValidacao`, token expirado→inválido, token usado→inválido, token novo→válido (1:1 com ACs)
- [ ] Gate check passes: `pytest tests/unit/auth/test_regras.py -q`
- [ ] Test count: ≥6 testes passam (no silent deletions)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(auth): regras puras de auth (validar_email/token) (Fatia 7, T2)`

---

### T3: `auth/portas.py` — contratos de I/O (Protocol)

**What**: Protocols `RepositorioCredencial`, `RepositorioToken`, `RepositorioSessao`, `EnviadorEmail`. Só interfaces.
**Where**: `src/terrametrica/auth/portas.py` (novo)
**Depends on**: T2 (usa `Email`)
**Reuses**: estilo `autorizacao/portas.py` (Protocol puro, sem I/O importado)
**Requirement**: PAINEL-01/03/05/13 (contratos que o serviço consome)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Protocols com as assinaturas exatas do design (design.md §Components 2): `conta_de_email`, `criar_conta_para_email`, `salvar`, `consumir` (atômico), `contar_na_janela`, `criar` (sessão), `conta_de_sessao`, `invalidar`, `enviar_magic_link`
- [ ] Nenhuma implementação, nenhum I/O importado (só `typing.Protocol` + `dominio`)
- [ ] Gate check passes: `ruff check . && mypy` (é arquivo de tipos — build gate)
- [ ] Test count: N/A (Protocol puro — matriz diz gate de build)

**Tests**: none (matriz: camada de contrato/tipo = build gate)
**Gate**: build
**Commit**: `feat(auth): contratos de I/O (RepositorioCredencial/Token/Sessao/EnviadorEmail) (Fatia 7, T3)`

---

### T4: `auth/servico.py` — orquestração dos 3 casos de uso

**What**: `solicitar_magic_link`, `confirmar_login`, `encerrar_sessao` — coreografam regras+ports. `ResultadoLogin` como tipo-resultado.
**Where**: `src/terrametrica/auth/servico.py` (novo); fakes em `tests/fakes/auth_fake.py` (novo)
**Depends on**: T3
**Reuses**: padrão `autorizacao/servico.py` (orquestra ports+regras, I/O nas ports); fakes em memória no estilo `tests/fakes/autorizacao_fake.py`
**Requirement**: PAINEL-01, PAINEL-02, PAINEL-03, PAINEL-04, PAINEL-05, PAINEL-13, PAINEL-14

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `solicitar_magic_link`: valida (422), checa rate limit 5/h (não envia na 6ª), gera+salva token 15min, envia — **sem revelar se o e-mail tem conta** (anti-enumeração)
- [ ] `confirmar_login`: consome token atômico (inválido→resultado inválido), upsert conta (`CONSULTA` se nova, autentica se conhecida — **não duplica**), cria sessão 30d, devolve token de sessão em claro
- [ ] `encerrar_sessao`: invalida idempotente
- [ ] Testes unit com fakes cobrem todos os ACs P1/P2 + edge cases: e-mail malformado, 6ª solicitação não envia, falha do enviador propaga, token usado não reautentica, e-mail conhecido não duplica conta, reenvio (dois tokens válidos), logout de sessão já invalidada
- [ ] Gate check passes: `pytest tests/unit/auth -q`
- [ ] Test count: ≥10 testes passam (no silent deletions)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(auth): serviço de auth (solicitar/confirmar/logout) (Fatia 7, T4)`

---

### T5: `auth/adaptadores.py` — implementações Postgres + Resend

**What**: `RepositorioCredencialPostgres`, `RepositorioTokenPostgres`, `RepositorioSessaoPostgres`, `EnviadorResend`.
**Where**: `src/terrametrica/auth/adaptadores.py` (novo); `tests/integration/auth/test_adaptadores.py` (novo)
**Depends on**: T4 (implementa as ports que o serviço consome; T1 fornece o schema)
**Reuses**: `abrir_conexao` (`persistencia/conexao.py`); padrão de repo dos `*_postgis.py`; `httpx` (T1 promoveu a runtime)
**Requirement**: PAINEL-01/03/05/13 (I/O real)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Repos recebem `conexao` (como os repos existentes); `consumir` é atômico (valida+marca usado numa transação — à prova de duplo clique)
- [ ] `contar_na_janela` implementa o rate limit 5/h via `idx_login_token_email_criado`
- [ ] Sessão grava **hash**, nunca o valor; `conta_de_sessao` filtra por `expira_em`
- [ ] `EnviadorResend` usa `httpx` + `RESEND_API_KEY`; **levanta em falha** (→ 502); testado com transporte HTTP fake (não chama Resend real)
- [ ] Testes integration (PostgisContainer) cobrem: consumir atômico (2º consumo→None), contar janela, criar/ler/invalidar sessão, sessão expirada→None
- [ ] Gate check passes: `pytest tests/integration/auth -q`
- [ ] Test count: ≥6 testes passam (no silent deletions)

**Tests**: integration
**Gate**: full
**Commit**: `feat(auth): adaptadores Postgres + EnviadorResend (Fatia 7, T5)`

---

### T6: `api/identidade.py` — resolver identidade por sessão OU header

**What**: Nova dependency `conta_id_da_sessao_ou_header`: cookie de sessão válido→conta; senão header `X-Conta-Id`; senão 401. Mantém `conta_id_obrigatorio` intacto.
**Where**: `src/terrametrica/api/identidade.py` (estende); `src/terrametrica/api/app.py` (troca a dependency injetada nas rotas de dossiê/cobertura); `tests/integration/api/test_identidade_sessao.py` (novo)
**Depends on**: T5 (`RepositorioSessao`)
**Reuses**: a dependency existente + o comentário-guia do arquivo ("o único ponto que muda quando o auth real nascer"); harness `TestClient` de `test_api_e2e.py`
**Requirement**: PAINEL-07 (chamada autenticada por sessão), PAINEL-12 (sessão expira→401)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `conta_id_da_sessao_ou_header`: cookie válido→`conta_id` da sessão; sem cookie→cai no header; nenhum→401; cookie corrompido/expirado→trata como sem sessão (cai no header ou 401), **nunca 5xx**
- [ ] Precedência sessão > header provada por teste
- [ ] **Retrocompat**: header `X-Conta-Id` sozinho (sem cookie) ainda resolve conta — F1.10 não regride (Success Criteria 3)
- [ ] Rotas `/dossie`/`/cobertura` trocam a dependency injetada; corpo das rotas **inalterado**
- [ ] Testes e2e (TestClient) cobrem: só cookie, só header, ambos (sessão vence), nenhum→401, cookie inválido→401/fallback
- [ ] Gate check passes: `pytest tests/integration/api -q` (inclui o `test_api_e2e.py` existente — prova zero regressão)
- [ ] Test count: `test_api_e2e.py` mantém contagem anterior + novos testes de identidade passam

**Tests**: integration
**Gate**: full
**Commit**: `feat(api): identidade por sessão OU header (retrocompat F1.10) (Fatia 7, T6)`

---

### T7: Rotas `/auth/*` — solicitar / confirmar / logout

**What**: 3 rotas finas em `api/app.py` traduzindo HTTP↔`auth/servico`, com ports injetadas via `criar_app`.
**Where**: `src/terrametrica/api/app.py` (modify — rotas + injeção de ports de auth em `criar_app`); `tests/integration/api/test_auth_e2e.py` (novo)
**Depends on**: T6
**Reuses**: `criar_app` (injeção de ports por parâmetro, como `limitador`/`relogio`); harness `TestClient` + `PostgisContainer` de `test_api_e2e.py`
**Requirement**: PAINEL-01, PAINEL-02, PAINEL-03, PAINEL-04, PAINEL-05, PAINEL-08, PAINEL-13, PAINEL-14

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `POST /auth/solicitar` → `solicitar_magic_link`: 202 sucesso, 422 e-mail ruim, 429 rate limit (6ª/h), 502 falha Resend
- [ ] `GET /auth/confirmar?token=` → `confirmar_login`: 302 + Set-Cookie httpOnly/Secure/SameSite=Lax/`Domain` pai (sucesso), 401 token inválido/expirado/usado (motivo único)
- [ ] `POST /auth/logout` → `encerrar_sessao`: 204 + cookie expirado; sessão já invalidada reapresentada→401
- [ ] `criar_app` aceita as ports de auth por parâmetro (mesmo mecanismo de `limitador`/`relogio`); nenhum novo seam de bootstrap
- [ ] **Prova de ponta**: clique autenticado por cookie (sessão criada via confirmar) retorna dossiê 200 sem header `X-Conta-Id`
- [ ] Testes e2e cobrem todos os status acima + o fluxo login→dossiê por cookie
- [ ] Gate check passes: `ruff check . && mypy && pytest -q`
- [ ] Test count: novos testes de auth e2e passam; suíte total sobe sem regredir

**Tests**: integration
**Gate**: build
**Commit**: `feat(api): rotas /auth/solicitar /confirmar /logout + fluxo cookie→dossiê (Fatia 7, T7)`

---

### T8: `app/dossie.js` — render do painel lateral (módulo puro) [P]

**What**: Módulo JS puro que recebe o JSON de `dossie_para_dict` e devolve o HTML/estado do painel lateral, tratando 200/404/409/429.
**Where**: `app/dossie.js` (novo); `app/tests/dossie.test.mjs` (novo)
**Depends on**: T7 (contrato de resposta estável)
**Reuses**: layout/render do dossiê de `prototipos/mapa-dossie/index.html`; padrão `node --test` de `prototipos/mapa-dossie/tests/geom.test.mjs`; shape de `api/dto.py::dossie_para_dict`
**Requirement**: PAINEL-08 (render 200), PAINEL-09 (404 sem_lote), PAINEL-10 (409 sobreposicao), PAINEL-11 (429 cota)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `dossie.js` exporta função pura: dado `{status, corpo}` devolve a estrutura a renderizar (lote, restrições, proveniência, ressalva no 200; mensagem+cobertura no 404; mensagem+candidatos no 409; mensagem+`retry_after_segundos` no 429)
- [ ] Testes `node --test` cobrem os 4 status a partir de JSON fixo (mesmo shape que `dossie_para_dict` produz)
- [ ] Gate check passes: `node --test app/tests/`
- [ ] Test count: ≥4 testes passam (no silent deletions)

**Tests**: unit (JS `node --test`)
**Gate**: JS
**Commit**: `feat(app): dossie.js — render do painel lateral (200/404/409/429) (Fatia 7, T8)`

---

### T9: `app/login.html` — tela de login por e-mail [P]

**What**: Página estática com form de e-mail → `POST /auth/solicitar` (`fetch` com `credentials:'include'`), estados de sucesso/erro (422/429/502).
**Where**: `app/login.html` (novo), `app/estilos.css` (novo — adaptado do protótipo)
**Depends on**: T7 (contrato de `/auth/solicitar`)
**Reuses**: CSS/layout de `prototipos/mapa-dossie/`
**Requirement**: PAINEL-01 (solicitar link), PAINEL-02 (422 e-mail ruim), PAINEL-05 (429), PAINEL-06 (sem sessão→login)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Form envia `POST /auth/solicitar` com `credentials:'include'`; mostra confirmação "link enviado" no 202
- [ ] Trata 422 (e-mail inválido, mensagem genérica), 429 (muitas tentativas), 502 (falha de envio explícita — não finge sucesso)
- [ ] **UX DoD**: responsivo, foco/acessibilidade AA no input, estados de loading/erro/sucesso visíveis, microcopy claro
- [ ] Verificação manual: submeter e-mail válido/malformado e observar cada estado (registrar no `Done when` da execução)

**Tests**: none (glue de UI — matriz: verificação manual + UX DoD)
**Gate**: — (verificação manual)
**Commit**: `feat(app): login.html — solicitar magic link + estados (Fatia 7, T9)`

---

### T10: `app/index.html` + `app/mapa.js` — mapa Leaflet + fetch autenticado

**What**: Página do mapa (Leaflet + tiles OSM); clique→`GET /dossie?lat&lon` (cookie automático), pluga `dossie.js` no painel lateral; 401→redirect para login.
**Where**: `app/index.html` (novo), `app/mapa.js` (novo)
**Depends on**: T8 (usa `dossie.js`), T7 (contrato `/dossie` autenticado por cookie)
**Reuses**: interação de mapa/layout de `prototipos/mapa-dossie/index.html`; `dossie.js` (T8)
**Requirement**: PAINEL-07 (clique→dossiê autenticado), PAINEL-12 (sessão expira→redirect), PAINEL-06 (sem sessão→login)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Leaflet + tiles OSM; clique captura `lat`/`lon` e chama `GET /dossie` com `credentials:'include'` (sem header manual)
- [ ] Resposta plugada no painel via `dossie.js` (T8); 200/404/409/429 renderizados
- [ ] 401 (sessão expirada/ausente) → redireciona para `login.html` (PAINEL-12/06)
- [ ] **UX DoD**: responsivo, painel lateral acessível AA, estado de loading no clique, erro visível, sem quebra de interação do mapa no 404/409
- [ ] Verificação manual: com sessão válida, clicar ponto conhecido do dataset de teste e conferir que o painel mostra os mesmos campos de uma chamada direta a `GET /dossie` (Independent Test da spec P1-mapa)

**Tests**: none (glue de UI — matriz: verificação manual + UX DoD; a lógica pura vive em `dossie.js`/T8)
**Gate**: — (verificação manual)
**Commit**: `feat(app): index.html + mapa.js — mapa autenticado → painel do dossiê (Fatia 7, T10)`

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1 (migração+httpx) ──→ T2 (regras) ──→ T3 (portas)

Phase 2 (Sequential):
  T3 complete, then:
    T4 (serviço) ──→ T5 (adaptadores)

Phase 3 (Sequential):
  T5 complete, then:
    T6 (identidade sessão|header) ──→ T7 (rotas /auth/*)

Phase 4 (Parallel parcial):
  T7 complete, then:
    ├── T8  (dossie.js + node --test) [P]
    ├── T9  (login.html) [P]
    └── T10 (index.html + mapa.js) ── depende de T8
```

**Parallelism constraint aplicada:** só T8 e T9 são `[P]` (unit JS parallel-safe / glue sem teste
integration). T10 depende de T8. T1/T5/T6/T7 usam integration (não parallel-safe) → sequenciais.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: migração + httpx runtime | 1 SQL + 1 edit pyproject (coeso: o schema da fatia) | ✅ Granular |
| T2: auth/regras.py | 1 módulo de funções puras coesas | ✅ Granular |
| T3: auth/portas.py | 1 arquivo de contratos | ✅ Granular |
| T4: auth/servico.py | 1 módulo de orquestração | ✅ Granular |
| T5: auth/adaptadores.py | 1 módulo de adapters (repos + enviador — mesma camada edge) | ✅ Granular |
| T6: api/identidade.py + wiring | 1 dependency + troca de injeção | ✅ Granular |
| T7: rotas /auth/* | 3 rotas finas coesas no mesmo entrypoint | ✅ Granular |
| T8: dossie.js | 1 módulo JS puro | ✅ Granular |
| T9: login.html | 1 página | ✅ Granular |
| T10: index.html + mapa.js | 1 tela (mapa+glue) coesa | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
| ---- | ----------------- | ------------- | ------ |
| T1 | None | (raiz Phase 1) | ✅ Match |
| T2 | None | T1→T2 (fase sequencial) | ✅ Match (ordem de fase, não dependência de dado — ver nota) |
| T3 | T2 | T2→T3 | ✅ Match |
| T4 | T3 | T3→T4 | ✅ Match |
| T5 | T4 | T4→T5 | ✅ Match |
| T6 | T5 | T5→T6 | ✅ Match |
| T7 | T6 | T6→T7 | ✅ Match |
| T8 | T7 | T7→T8 | ✅ Match |
| T9 | T7 | T7→T9 | ✅ Match |
| T10 | T8, T7 | T7→T10, T8→T10 | ✅ Match |

> Nota: T2 não depende de dado de T1 (regras puras independem do schema), mas roda depois na ordem
> de fase por coesão de commit. O diagrama mostra a **ordem de execução da fase**; a dependência
> real de dado de T2 é `None` (pode iniciar em paralelo a T1 se desejado). Marcado explícito para
> não parecer drift.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | migração SQL | integration (idempotência) | integration | ✅ OK |
| T2 | `auth/regras.py` | unit | unit | ✅ OK |
| T3 | `auth/portas.py` (Protocol) | none (build gate) | none | ✅ OK |
| T4 | `auth/servico.py` | unit (fakes) | unit | ✅ OK |
| T5 | `auth/adaptadores.py` | integration | integration | ✅ OK |
| T6 | `api/identidade.py` + app wiring | integration (e2e) | integration | ✅ OK |
| T7 | rotas `api/app.py` | integration (e2e) | integration | ✅ OK |
| T8 | `app/dossie.js` (módulo puro) | unit (JS node --test) | unit | ✅ OK |
| T9 | `app/login.html` (glue UI) | none (manual + UX DoD) | none | ✅ OK |
| T10 | `app/index.html`+`mapa.js` (glue UI) | none (manual + UX DoD) | none | ✅ OK |

> `Tests: none` em T3/T9/T10 é válido: T3 é camada de contrato (matriz diz build gate); T9/T10 são
> glue de UI sem lógica pura — a lógica de render testável foi **extraída para `dossie.js` (T8)**,
> que É testado. Isso NÃO é deferral: a lógica não fica sem teste, ela mora no módulo puro certo.

---

## Requirement Coverage (14 PAINEL-NN → tasks)

| Requirement | Task(s) |
| ----------- | ------- |
| PAINEL-01 (solicitar link) | T1, T4, T7, T9 |
| PAINEL-02 (422 e-mail malformado) | T2, T4, T7, T9 |
| PAINEL-03 (confirmar cria/autentica) | T1, T4, T7 |
| PAINEL-04 (401 token expirado/usado) | T2, T4, T7 |
| PAINEL-05 (429 rate limit 5/h) | T1, T4, T5, T7, T9 |
| PAINEL-06 (sem sessão→login) | T9, T10 |
| PAINEL-07 (clique→dossiê autenticado) | T6, T10 |
| PAINEL-08 (render 200 dossiê) | T7, T8 |
| PAINEL-09 (render 404 sem_lote) | T8 |
| PAINEL-10 (render 409 sobreposicao) | T8 |
| PAINEL-11 (render 429 cota) | T8 |
| PAINEL-12 (sessão expira→redirect) | T6, T10 |
| PAINEL-13 (logout invalida) | T4, T7 |
| PAINEL-14 (sessão invalidada→401) | T4, T7 |

**Cobertura:** 14/14 requisitos mapeados a ≥1 task. 0 órfãos.

---

## Débitos a registrar na execução (do design §Risks)

Ao chegar nas tasks correspondentes, abrir os TDs que o design deixou como `TD-NNN`:
- **CSRF em `/auth/solicitar` e `/auth/logout`** (mitigado por `SameSite=Lax` + rate limit; aceito no MVP) → abrir TD na T7.
- **GC de `login_token`/`sessao` expirados** (consultas já filtram por `expira_em`; job de limpeza fora de escopo) → abrir TD na T1/T5.
- **TD-006** (`conta_id` sem FK) já está registrado em `.specs/TECH-DEBT.md` (não reabrir).

## Next Step

Tasks prontas para revisão. Ao aprovar → fase **Execute**. São **4 fases (>3)** → o skill vai
**oferecer sub-agentes** (um worker por fase, sequencial) antes de executar — offer-then-confirm, sem
auto-spawn. Após a última task, o **Verifier independente** roda automaticamente (author ≠ verifier,
evidence-or-zero + sensor de discriminação) e escreve `validation.md`.

A **RFD de infra** do design (VPS+Caddy vs CDN+container) pode ficar para o fim de Execute — o código
não muda entre as opções, só o empacotamento.
