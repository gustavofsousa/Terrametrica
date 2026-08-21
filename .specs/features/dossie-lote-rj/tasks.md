# Dossiê de Lote RJ — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/dossie-lote-rj/design.md`
**Status**: Executada — T1–T5 concluídas e validadas (`validation.md`, PASS, 46 passed). Fatias de
infra seguem bloqueadas na Fase 0.

**Slice**: **Fatia 1 — Núcleo de domínio (rodável agora, sem Fase 0)**. Regras numéricas do produto
+ árvore de decisão da montagem do dossiê, atrás de um *port* de repositório, testadas com um fake
em memória. Puro Python, `pytest` unit — não depende de PostGIS, ingestão nem egress `.gov.br`.

**Fatias seguintes (fora deste tasks.md), bloqueadas em Fase 0 / infra:**
adaptador PostGIS + ingestão versionada · camada urbana (Niterói) · página de cobertura ·
API FastAPI + observabilidade · web MapLibre · versionamento atômico real · gate jurídico P2.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec — confirm before Execute. Guidelines found: `~/.claude/CLAUDE.md` (AGENTS.md — "tests derive from acceptance criteria, never mirror the implementation"; "make illegal states unrepresentable"). No test-runner config exists yet — esta fatia o cria. Decisão do usuário: **só pytest unit por enquanto** (integração/e2e entram quando a Fase 0 destravar dados reais).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domínio — value objects (`dominio/modelos.py`) | unit | Todos os ramos de validação (lat/lon inválidos, área negativa, enums fechados) | `tests/unit/dominio/test_*.py` | `pytest tests/unit -q` |
| Geometria — regras numéricas (`geometria/regras.py`) | unit | Todos os ramos; 1:1 com DOS-08; edge nos limiares 1% / 5% / áreas zero | `tests/unit/geometria/test_*.py` | `pytest tests/unit -q` |
| Dossiê — montagem (`dossie/montagem.py`) | unit | Toda a árvore de decisão: DOS-02, 04, 05, 06, 10, 11, 12, 13 (com fake do port) | `tests/unit/dossie/test_*.py` | `pytest tests/unit -q` |
| Ports (`dossie/portas.py`) — Protocol | none | Build gate apenas (sem implementação a testar) | — | build gate |
| Scaffold / config (`pyproject.toml`) | none | Build gate apenas | — | build gate |

## Parallelism Assessment

> Generated from codebase — confirm before Execute.

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --- | --- | --- | --- |
| unit | Yes | Funções puras; fake de repositório em memória, instanciado por teste; sem store compartilhado, sem estado global mutável | Nenhum DB nem I/O nesta fatia; ports injetados por parâmetro |

## Gate Check Commands

> Generated from codebase — confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Após tasks com testes unit | `pytest tests/unit -q` |
| Full | N/A nesta fatia (sem integração/e2e) | `pytest tests/unit -q` |
| Build | Fim de fase / tasks de config | `ruff check . && mypy src && pytest -q` |

---

## Execution Plan

### Phase 1: Fundação (Sequential)

```
T1 → T2
```

### Phase 2: Regras e contratos (Parallel OK)

Após T2, sem dependência entre si.

```
     ┌→ T3 [P]
T2 ──┤
     └→ T4 [P]
```

### Phase 3: Montagem (Sequential)

```
T2, T3, T4 → T5
```

3 fases → execução inline, sem sub-agentes.

---

## Task Breakdown

### T1: Scaffold do projeto Python

**What**: Criar o projeto `terrametrica` com `pyproject.toml` (pacote + pytest + ruff + mypy), estrutura `src/terrametrica/` e `tests/unit/`.
**Where**: `pyproject.toml`, `src/terrametrica/__init__.py`, `tests/unit/__init__.py`
**Depends on**: None
**Reuses**: `docs/research/stack-open-source.md` (ecossistema Python); convenções de `~/.claude/CLAUDE.md`
**Requirement**: infra (habilita DOS-*)

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`

**Done when**:
- [x] `pyproject.toml` define pacote `terrametrica` (layout `src/`), deps de dev `pytest`, `ruff`, `mypy`
- [x] `pytest -q` roda e coleta 0 testes sem erro
- [x] `ruff check .` e `mypy src` passam num scaffold vazio
- [x] Gate check passa: `ruff check . && mypy src && pytest -q`

**Tests**: none (config)
**Gate**: build

**Commit**: `chore: scaffold do pacote python terrametrica com pytest, ruff e mypy`

---

### T2: Modelos de domínio (value objects e resultados)

**What**: Definir os value objects e tipos-resultado do domínio, com validação no boundary e estados ilegais irrepresentáveis (enums fechados, união de resultados).
**Where**: `src/terrametrica/dominio/modelos.py`
**Depends on**: T1
**Reuses**: vocabulário de `docs/produto/glossario.md`; regra "validate at the boundary" e "make illegal states unrepresentable" de `~/.claude/CLAUDE.md`
**Requirement**: DOS-02 (Coordenada valida lat/lon), DOS-05 (bounds do RJ como dado injetável), base p/ DOS-01/06/10

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`

**Done when**:
- [x] `Coordenada` valida lat/lon e rejeita fora de faixa com erro específico
- [x] `AreaM2` / `AreaHa` rejeitam valor negativo; enums fechados `Camada`, `TipoRestricao`, `SituacaoCertificacao`, `PapelConta`
- [x] Tipos-resultado da montagem como união fechada: `Dossie`, `SemLote`, `Sobreposicao`, `ForaDoRJ`; `CampoComProveniencia`, `VersaoBase`
- [x] Testes unit cobrem todos os ramos de validação (inválido/limite/válido)
- [x] Gate check passa: `pytest tests/unit -q`
- [x] Test count: ~8 testes passam (sem deleção silenciosa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(dominio): value objects e tipos-resultado do dossiê com validação no boundary`

---

### T3: Regras numéricas de geometria [P]

**What**: Implementar as regras puras que definem o produto sobre áreas já calculadas: classificação de intersecção (toque marginal) e avaliação de divergência entre fontes.
**Where**: `src/terrametrica/geometria/regras.py`
**Depends on**: T2
**Reuses**: constantes/limiares do protótipo (`prototipos/mapa-dossie/index.html` — 1% marginal, 5% divergência)
**Requirement**: DOS-08 (marginal <1%), regra base p/ DOS-17/18 (divergência SIGEF×CAR)

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [x] `classificar_intersecao(area_lote, area_inter) -> ClassificacaoIntersecao` marca `marginal` quando pct < 1%, `plena` caso contrário, e devolve o pct
- [x] `avaliar_divergencia(area_sigef, area_car) -> Divergencia` devolve diferença em ha e pct e aciona alerta acima de 5%; nunca reconcilia
- [x] Testes unit cobrem os limiares exatos (0.99%/1.00%/1.01%; 4.9%/5.0%/5.1%) e área zero
- [x] Gate check passa: `pytest tests/unit -q`
- [x] Test count: ~10 testes passam (sem deleção silenciosa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(geometria): regras de toque marginal e divergência entre fontes`

---

### T4: Ports do repositório e do limite estadual [P]

**What**: Definir os contratos (Protocol) que o domínio usa para consultar lote, intersecções, proveniência e cobertura, e para testar contenção no RJ — sem implementação concreta.
**Where**: `src/terrametrica/dossie/portas.py`
**Depends on**: T2
**Reuses**: modelo de dados de `design.md` (read-model materializado, proveniência, cobertura)
**Requirement**: fronteira (habilita DOS-01/04/06/10/11/12/13); mantém fonte externa fora do request (AD-004)

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`

**Done when**:
- [x] `RepositorioLotes` (Protocol): `lote_em(coord, versao) -> LoteHit | Sobreposicao | None`, `intersecoes_de(lote, versao) -> list[IntersecaoBruta]`, `proveniencia_de(camada, versao) -> Proveniencia`, `cobertura_de(municipio) -> list[CoberturaCamada]`
- [x] `LimiteEstado` (Protocol): `contem(coord) -> bool`
- [x] `mypy src` valida os Protocols; nenhuma dependência de I/O importada
- [x] Gate check passa: `ruff check . && mypy src && pytest -q`

**Tests**: none (Protocol — build gate, conforme matriz)
**Gate**: build

**Commit**: `feat(dossie): ports de repositório e limite estadual`

---

### T5: Montagem do dossiê (árvore de decisão)

**What**: Implementar `montar_dossie` orquestrando os ports e as regras: recusa fora do RJ, sem lote, sobreposição, dossiê parcial em camada faltante/sem cobertura, carimbo de proveniência e aviso de base >90 dias.
**Where**: `src/terrametrica/dossie/montagem.py` (+ fake do port em `tests/fakes/repositorio_fake.py`)
**Depends on**: T2, T3, T4
**Reuses**: `geometria/regras.py` (T3), `dossie/portas.py` (T4), `dominio/modelos.py` (T2); ordem do dossiê de `docs/produto/dossie.md`
**Requirement**: DOS-02, DOS-04, DOS-05, DOS-06, DOS-10, DOS-11, DOS-12, DOS-13

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [x] `montar_dossie(coord, versao, repo, limite) -> Dossie | SemLote | Sobreposicao | ForaDoRJ`
- [x] Fora do RJ → `ForaDoRJ` "apenas RJ" (DOS-05); sem lote → `SemLote` com município + cobertura declarada (DOS-04); sobreposição → `Sobreposicao` exigindo escolha (DOS-06)
- [x] Camada indisponível → dossiê parcial marcando a faltante (DOS-12); sem cobertura no município → seção declara ausência (DOS-11)
- [x] Cada campo carrega fonte + data (DOS-10); camada com extração > 90 dias marcada "possivelmente desatualizada" (DOS-13)
- [x] Intersecções passam por `classificar_intersecao` (marginal preservado no dossiê)
- [x] Fake em memória implementa os ports; testes unit cobrem cada ramo da árvore (1 teste por AC no mínimo)
- [x] Gate check passa: `pytest tests/unit -q`
- [x] Test count: ~12 testes passam (sem deleção silenciosa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(dossie): montagem do dossiê com proveniência, dossiê parcial e cobertura`

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1 ──→ T2

Phase 2 (Parallel):
  T2 completo, então:
    ├── T3 [P]
    └── T4 [P]

Phase 3 (Sequential):
  T3, T4 completos, então:
    T5
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Scaffold | 1 setup de projeto | ✅ Granular |
| T2: Modelos de domínio | 1 arquivo coeso (value objects) | ✅ Granular |
| T3: Regras de geometria | 2 funções puras, 1 arquivo | ✅ Granular |
| T4: Ports | 1 arquivo de contratos | ✅ Granular |
| T5: Montagem | 1 função/módulo | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | (raiz) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 [P] | ✅ Match |
| T4 | T2 | T2 → T4 [P] | ✅ Match |
| T5 | T2, T3, T4 | T3,T4 → T5 (e T2 via cadeia) | ✅ Match |

T3 e T4 marcados `[P]` não dependem um do outro. ✅

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Scaffold / config | none | none | ✅ OK |
| T2 | Domínio — value objects | unit | unit | ✅ OK |
| T3 | Geometria — regras | unit | unit | ✅ OK |
| T4 | Ports (Protocol) | none | none | ✅ OK |
| T5 | Dossiê — montagem | unit | unit | ✅ OK |

Nenhuma violação. Testes co-localizados na task que cria a camada — sem deferral.
