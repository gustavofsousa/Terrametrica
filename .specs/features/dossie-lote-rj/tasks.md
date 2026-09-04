# Dossiê de Lote RJ — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/dossie-lote-rj/design.md`
**Status**: Fatia 1 executada e validada (`validation.md`, PASS, 46 passed). **Fatia 2 em Draft,
tasks abaixo aguardando aprovação — Fase 0 fechada, sem bloqueio técnico restante.**

**Slice 1**: **Núcleo de domínio (rodável agora, sem Fase 0)**. Regras numéricas do produto
+ árvore de decisão da montagem do dossiê, atrás de um *port* de repositório, testadas com um fake
em memória. Puro Python, `pytest` unit — não depende de PostGIS, ingestão nem egress `.gov.br`.

**Slice 2**: **Adaptador PostGIS + ingestão SIGEF (walking skeleton)** — ver seção própria mais
abaixo. Schema mínimo, adapters reais dos *ports* de T4, ingestão de limite RJ + SIGEF, publicação
com guarda e swap atômico, prova fim-a-fim.

**Fatias seguintes (fora deste tasks.md ainda):**
CAR (segunda geometria do lote rural) · camada urbana Niterói (SIGeo) · camadas de restrição
(INEA/ICMBio/ANA) + `intersecao_materializada` · página de cobertura · API FastAPI +
observabilidade · web MapLibre · gate jurídico P2.

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

---
---

# Fatia 2 — Adaptador PostGIS + Ingestão SIGEF (walking skeleton)

**Design**: `.specs/features/dossie-lote-rj/design.md` (seção "Fatia 2 — Escopo desta rodada" e
"Testing Seams — Fatia 2")
**Status**: **Draft — aguardando aprovação do usuário, ainda não executada.**

**Escopo**: schema PostGIS mínimo, adapters reais (`RepositorioLotesPostGIS`,
`LimiteEstadoPostGIS`) implementando os *ports* já existentes (T4), e ingestão de **só duas
fontes**: limite estadual do RJ (geobr, fetch programático) e SIGEF (arquivo local já exportado por
ação humana — SICAR/gov.br não tem download programático, ver Fase 0 em `.specs/STATE.md`). CAR,
SIGeo (urbano) e camadas de restrição (INEA/ICMBio/ANA) ficam para fatias seguintes — sem uma
camada de restrição ingerida, `intersecao_materializada` não existe ainda nesta fatia.

**Fora desta fatia**: CAR (segunda geometria do lote rural, AD-003), camada urbana Niterói,
qualquer camada de restrição, `intersecao_materializada`, API FastAPI, front-end MapLibre.

---

## Test Coverage Matrix — Fatia 2

> Gerado a partir de `pyproject.toml` (sem deps de integração ainda), `tests/unit/` (só unit até
> aqui) e `~/.claude/CLAUDE.md` ("tests derive from acceptance criteria"). Fatia 2 introduz um tipo
> de teste novo — **integration** — porque comportamento espacial real (`ST_Intersection`,
> `ST_MakeValid`, swap atômico em transação) não é verificável contra um fake em memória.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Dev infra / config (`docker-compose.yml`, deps) | none | Build gate apenas | — | build gate |
| Schema / migrações SQL (`persistencia/migracoes/*.sql`) | none | Build gate apenas (correção real verificada indiretamente pelas tasks que a usam) | — | build gate |
| Persistência — conexão + runner de migração (`persistencia/conexao.py`, `persistencia/migrar.py`) | integration | Migração aplica limpo em banco vazio; idempotente ao rodar duas vezes | `tests/integration/persistencia/test_*.py` | `pytest tests/integration -q` |
| Persistência — adapters (`repositorio_lotes_postgis.py`, `limite_estado_postgis.py`) | integration | Mesmos ramos/casos de borda que o fake em memória de T5 (contrato do Protocol) | `tests/integration/persistencia/test_*.py` | `pytest tests/integration -q` |
| Ingestão — pipelines (`ingestao/limite_rj.py`, `ingestao/sigef.py`, `ingestao/publicar.py`) | integration | Happy path + validação/correção de geometria + guarda de publicação (DOS-25/28) | `tests/integration/ingestao/test_*.py` | `pytest tests/integration -q` |
| Fim-a-fim — `montar_dossie` sobre PostGIS real | integration | 1 caso completo: clique → dossiê real com proveniência, usando os adapters desta fatia | `tests/integration/test_dossie_e2e.py` | `pytest tests/integration -q` |

## Parallelism Assessment — Fatia 2

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --- | --- | --- | --- |
| unit (Fatia 1, inalterado) | Yes | Funções puras, fake em memória por teste | Nenhum I/O; ver matriz da Fatia 1 |
| integration (novo) | **No** | Container PostGIS efêmero via testcontainers, um por módulo de teste; cada teste roda dentro de uma transação com rollback no teardown — isola dado, mas subir containers Docker concorrentes numa máquina de um dev só é instável/caro | Nenhuma infra de CI dedicada ainda (projeto solo); decisão registrada em design.md Risks & Concerns |

**Consequência**: nenhuma task desta fatia leva `[P]`. O `Depends on` de cada task reflete a
dependência real de código/schema; a ordem de execução é sempre sequencial.

## Gate Check Commands — Fatia 2

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Tasks só-unit (nenhuma nesta fatia) | `pytest tests/unit -q` |
| Full | Após qualquer task de integração (checar `docker info` antes) | `pytest tests/unit tests/integration -q` |
| Build | Fim de fase / tasks de config | `ruff check . && mypy src && pytest tests/unit tests/integration -q` |

---

## Execution Plan — Fatia 2

### Phase 1: Infra e schema (Sequential)

```
T6 → T7 → T8
```

### Phase 2: Adapters (Sequential — mesma razão de Parallelism Assessment)

```
T8 → T9 → T10
```

### Phase 3: Ingestão (Sequential)

```
T8 → T11 → T13
T8 → T12 → T13
```

### Phase 4: Prova fim-a-fim (Sequential)

```
T9, T10, T13 → T14
```

4 fases, todas sequenciais dentro de si — sem paralelismo real nesta fatia (ver Parallelism
Assessment). Execução inline recomendada; oferta de sub-agente por fase é decisão do momento do
Execute, não deste documento.

---

## Task Breakdown — Fatia 2

### T6: Infra de dev — PostGIS local + dependências

**What**: `docker-compose.yml` com `postgis/postgis:16-3.4` para dev manual; adiciona ao
`pyproject.toml` as deps de runtime (`psycopg[binary]`, `geopandas`, `shapely`, `pyproj`) e de dev
(`testcontainers[postgres]`); documenta pré-requisito Docker em `docs/DEV-SETUP.md`.
**Where**: `docker-compose.yml`, `pyproject.toml`, `docs/DEV-SETUP.md`
**Depends on**: None
**Reuses**: `docs/research/stack-open-source.md` (escolhas de lib já levantadas)
**Requirement**: infra (habilita Fatia 2)

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`

**Done when**:
- [ ] `docker compose up -d` sobe Postgres 16 + PostGIS na porta configurada (não conflita com
      outros projetos — checar portas em uso antes de fixar)
- [ ] `pyproject.toml` tem as 4 deps de runtime + `testcontainers[postgres]` em dev
- [ ] `docs/DEV-SETUP.md` documenta o pré-requisito Docker e como rodar a suíte de integração
- [ ] Gate check passa: `ruff check . && mypy src && pytest tests/unit -q` (integração ainda não existe)

**Tests**: none (config)
**Gate**: build

**Commit**: `chore(fatia2): infra de dev PostGIS + deps de persistência e ingestão`

---

### T7: Schema — migração SQL da Fatia 2

**What**: Migração `persistencia/migracoes/0001_fatia2_sigef.sql` criando `versao_base`,
`ponteiro_publicado`, `limite_estado`, `lote_rural` (com `geom_sigef` e `geom_car` nullable — dupla
geometria é invariante do modelo, AD-003, mesmo com `geom_car` vazio nesta fatia), `proveniencia`,
`cobertura`. Extensão PostGIS habilitada na migração.
**Where**: `src/terrametrica/persistencia/migracoes/0001_fatia2_sigef.sql`
**Depends on**: T6
**Reuses**: modelo de dados de `design.md` (seção Data Models)
**Requirement**: base p/ DOS-04/10/13/25/28; AD-003, AD-007, AD-008

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`

**Done when**:
- [ ] `CREATE EXTENSION IF NOT EXISTS postgis` na migração
- [ ] Todas as 6 tabelas do escopo da fatia criadas com os tipos de `design.md` (geometry em
      EPSG:4674, `versao_base_id` como FK onde aplicável)
- [ ] `lote_rural.geom_car` é nullable (AD-003 preservado, mesmo sem CAR nesta fatia)
- [ ] Gate check passa: `ruff check . && mypy src && pytest tests/unit -q`

**Tests**: none (DDL — verificado funcionalmente por T8)
**Gate**: build

**Commit**: `feat(persistencia): schema PostGIS mínimo da Fatia 2 (versao_base, limite_estado, lote_rural, proveniencia, cobertura)`

---

### T8: Conexão + runner de migração

**What**: `persistencia/conexao.py` (abre conexão `psycopg` a partir de uma URL de config) e
`persistencia/migrar.py` (aplica migrações SQL em ordem, idempotente via tabela de controle
`schema_migrations`).
**Where**: `src/terrametrica/persistencia/conexao.py`, `src/terrametrica/persistencia/migrar.py`
**Depends on**: T7
**Reuses**: nenhuma dep externa além de `psycopg`

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [ ] `aplicar_migracoes(conexao)` roda a 0001 num banco vazio e cria as 6 tabelas
- [ ] Rodar `aplicar_migracoes` duas vezes seguidas não falha nem duplica (idempotente)
- [ ] Teste de integração sobe container PostGIS efêmero (testcontainers), aplica migração, faz
      introspecção (`information_schema`) confirmando as 6 tabelas + extensão PostGIS ativa
- [ ] `docker info` checado antes da suíte de integração (skip com mensagem clara se Docker não
      estiver rodando, não falha genérica)
- [ ] Gate check passa: `pytest tests/unit tests/integration -q`
- [ ] Test count: ~3 testes passam (sem deleção silenciosa)

**Tests**: integration
**Gate**: full

**Commit**: `feat(persistencia): conexão e runner de migração idempotente`

---

### T9: Adapter `RepositorioLotesPostGIS`

**What**: Implementa o Protocol `RepositorioLotes` (T4) contra o schema real: `lote_em`,
`intersecoes_de` (retorna lista vazia — nenhuma restrição ingerida nesta fatia, comportamento
documentado, não um placeholder escondido), `proveniencia_de`, `cobertura_de`, `municipio_em`
(**TD-001**: levanta `NotImplementedError` explícito — exige malha municipal IBGE, fora do escopo
desta fatia; ver `.specs/TECH-DEBT.md`).
**Where**: `src/terrametrica/persistencia/repositorio_lotes_postgis.py`
**Depends on**: T8
**Reuses**: `dossie/portas.py` (T4, contrato); casos de borda de `tests/fakes/repositorio_fake.py` (T5)
**Requirement**: DOS-01, DOS-04 (parcial — ver TD-001), DOS-10, DOS-11 sobre dado real

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [ ] `lote_em(coord, versao)` encontra o lote certo via `ST_Contains`/`ST_Intersects` em dado
      semeado diretamente por SQL (fixture de teste, sem passar pela ingestão)
- [ ] `intersecoes_de` retorna `[]` de forma explícita e documentada (sem restrição ingerida)
- [ ] `proveniencia_de` retorna fonte + data carimbadas na ingestão (T12)
- [ ] `cobertura_de` reflete `cobertura` semeada (camada SIGEF presente, demais ausentes)
- [ ] `municipio_em` levanta `NotImplementedError` com mensagem citando TD-001 — teste confirma a
      exceção, não um retorno inventado
- [ ] Mesmos casos de borda testados no fake em memória (T5) passam aqui contra Postgres real,
      **exceto** o ramo `SemLote` (que depende de `municipio_em` — cai em TD-001, não testável
      nesta fatia)
- [ ] Gate check passa: `pytest tests/unit tests/integration -q`
- [ ] Test count: ~6 testes passam (sem deleção silenciosa)

**Tests**: integration
**Gate**: full

**Commit**: `feat(persistencia): adapter RepositorioLotesPostGIS implementando o port da Fatia 1`

---

### T10: Adapter `LimiteEstadoPostGIS`

**What**: Implementa o Protocol `LimiteEstado` (T4): `contem(coord) -> bool` via `ST_Contains`
contra o polígono do RJ em `limite_estado`.
**Where**: `src/terrametrica/persistencia/limite_estado_postgis.py`
**Depends on**: T8
**Reuses**: `dossie/portas.py` (T4); coordenadas de teste de fronteira já usadas em T2/T5

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [ ] Coordenada claramente dentro do RJ → `True`; claramente fora → `False`
- [ ] Coordenada na borda (mesmos casos-limite de T2/T5) concorda com o comportamento já testado
      no domínio
- [ ] Gate check passa: `pytest tests/unit tests/integration -q`
- [ ] Test count: ~4 testes passam (sem deleção silenciosa)

**Tests**: integration
**Gate**: full

**Commit**: `feat(persistencia): adapter LimiteEstadoPostGIS implementando o port da Fatia 1`

---

### T11: Ingestão — limite estadual do RJ

**What**: `ingestao/limite_rj.py` — `ingerir_limite_rj(versao) -> RelatorioCamada`: busca o
polígono do RJ via `geobr.read_state(code_state=33)` (fetch programático, sem login — S3, não
`.gov.br`), valida (`ST_MakeValid` equivalente via Shapely `.buffer(0)`/`make_valid`), reprojeta
para EPSG:4674, grava em `limite_estado` para a versão.
**Where**: `src/terrametrica/ingestao/limite_rj.py`
**Depends on**: T8
**Reuses**: `docs/research/stack-open-source.md` (geobr); `AD-008` (CRS canônico)
**Requirement**: base p/ `LimiteEstadoPostGIS` (T10) ter dado real

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [ ] `ingerir_limite_rj` grava exatamente 1 polígono/multipolígono válido em EPSG:4674
- [ ] Teste de integração faz a chamada real ao geobr (rede necessária — documentado como
      dependência de rede no teste, não mockado; falha com mensagem clara se offline)
- [ ] Geometria inválida (se ocorrer) é corrigida e o registro é marcado `geometria_corrigida=true`
- [ ] Gate check passa: `pytest tests/unit tests/integration -q`
- [ ] Test count: ~3 testes passam (sem deleção silenciosa)

**Tests**: integration
**Gate**: full

**Commit**: `feat(ingestao): busca e materializa o limite estadual do RJ via geobr`

---

### T12: Ingestão — SIGEF a partir de arquivo local

**What**: `ingestao/sigef.py` — `ingerir_sigef(caminho: Path, versao) -> RelatorioCamada`: lê
shapefile via GeoPandas (`pyogrio`), valida geometria (`ST_MakeValid` equivalente), confirma/ajusta
CRS para EPSG:4674, grava cada feição em `lote_rural.geom_sigef` (`geom_car` fica null) e carimba
`proveniencia` (fonte='SIGEF', data de extração, link oficial).
**Where**: `src/terrametrica/ingestao/sigef.py`
**Depends on**: T8
**Reuses**: campos reais descobertos em Fase 0 (`municipio_`, `status`) — `docs/research/fontes-de-dados-rj.md`
**Requirement**: DOS-10 (proveniência), AD-003 (dupla geometria, mesmo com CAR vazio)

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [ ] Fixture `.shp` sintética criada em `tests/fixtures/sigef/` (poucas feições, mesmos campos
      reais: `municipio_`, `status`, encoding `.dbf` latin1) — não depende do arquivo real de
      ~1GB nem de rede/login
- [ ] `ingerir_sigef` lê a fixture, valida geometria, grava em `lote_rural` com `geom_car` null
- [ ] `proveniencia` carimbada com fonte='SIGEF' e data de extração
- [ ] Feição inválida na fixture é corrigida e marcada (`geometria_corrigida=true`), não descartada
      silenciosamente
- [ ] Gate check passa: `pytest tests/unit tests/integration -q`
- [ ] Test count: ~5 testes passam (sem deleção silenciosa)

**Tests**: integration
**Gate**: full

**Commit**: `feat(ingestao): ingere SIGEF a partir de export local (sem download programático — Fase 0)`

---

### T13: Publicação de versão — guarda + swap atômico

**What**: `ingestao/publicar.py` — `publicar_versao(versao) -> ResultadoPublicacao`: por camada,
compara contagem de feições da nova versão contra a publicada anteriormente; se ≥90%, faz swap
atômico do `ponteiro_publicado` em transação; se <90%, rejeita e mantém a versão anterior (DOS-25).
**Where**: `src/terrametrica/ingestao/publicar.py`
**Depends on**: T11, T12
**Reuses**: `AD-008` (ponteiro atômico); dado real de `limite_estado`/`lote_rural` gravado nesta fatia

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [ ] Primeira publicação (sem versão anterior) sempre passa a guarda e publica
- [ ] Segunda versão com ≥90% das feições da anterior → swap atômico, ponteiro aponta pra nova
- [ ] Segunda versão com <90% → publicação rejeitada, ponteiro continua na versão anterior
      (DOS-25/edge)
- [ ] Swap roda dentro de uma transação — teste de integração confirma que uma falha no meio não
      deixa o ponteiro em estado parcial (DOS-28)
- [ ] Gate check passa: `pytest tests/unit tests/integration -q`
- [ ] Test count: ~4 testes passam (sem deleção silenciosa)

**Tests**: integration
**Gate**: full

**Commit**: `feat(ingestao): publicação de versão com guarda de 90% e swap atômico de ponteiro`

---

### T14: Prova fim-a-fim — dossiê real sobre PostGIS

**What**: Teste de integração único que injeta `RepositorioLotesPostGIS` (T9) e
`LimiteEstadoPostGIS` (T10) reais em `montar_dossie` (T5, inalterado) e confirma um dossiê completo
— com proveniência — para uma coordenada dentro de um lote SIGEF semeado via T12. Sem código novo
de produção; é o teste que prova a Fatia 2 fim-a-fim.
**Where**: `tests/integration/test_dossie_e2e.py`
**Depends on**: T9, T10, T13
**Reuses**: `dossie/montagem.py` (T5, zero mudança — prova que os *ports* isolaram a troca de fake→real)
**Requirement**: prova de AD-007 (read-model materializado) e AD-004 (fonte externa fora do request)

**Tools**:
- MCP: NONE
- Skill: `tdd`

**Done when**:
- [ ] Pipeline completo: `ingerir_limite_rj` → `ingerir_sigef` (fixture) → `publicar_versao` →
      `montar_dossie(coord_dentro_do_lote, versao, RepositorioLotesPostGIS, LimiteEstadoPostGIS)`
- [ ] Dossiê retornado tem proveniência (fonte + data) no campo SIGEF
- [ ] Coordenada fora do RJ ainda devolve `ForaDoRJ` (mesmo comportamento de T5, agora sobre dado
      real)
- [ ] Gate check passa: `pytest tests/unit tests/integration -q`
- [ ] Test count: ~2 testes passam (sem deleção silenciosa)

**Tests**: integration
**Gate**: full

**Commit**: `test(dossie): prova fim-a-fim do dossiê sobre PostGIS real (Fatia 2 fechada)`

---

## Parallel Execution Map — Fatia 2

```
Phase 1 (Sequential):
  T6 ──→ T7 ──→ T8

Phase 2 (Sequential):
  T8 ──→ T9 ──→ T10

Phase 3 (Sequential):
  T8 ──→ T11 ──→ T13
  T8 ──→ T12 ──┘

Phase 4 (Sequential):
  T9, T10, T13 ──→ T14
```

Nenhuma task leva `[P]` nesta fatia — ver Parallelism Assessment (containers Docker concorrentes
não são seguros numa máquina de um dev só).

---

## Task Granularity Check — Fatia 2

| Task | Scope | Status |
| --- | --- | --- |
| T6: Infra de dev | 1 concern (compose + deps) | ✅ Granular |
| T7: Schema | 1 arquivo de migração | ✅ Granular |
| T8: Conexão + migrar | 2 funções coesas, 1 concern | ✅ Granular |
| T9: Adapter lotes | 1 Protocol implementado | ✅ Granular |
| T10: Adapter limite | 1 Protocol implementado | ✅ Granular |
| T11: Ingestão limite RJ | 1 função | ✅ Granular |
| T12: Ingestão SIGEF | 1 função | ✅ Granular |
| T13: Publicação | 1 função | ✅ Granular |
| T14: Prova e2e | 1 teste, zero código de produção novo | ✅ Granular |

## Diagram-Definition Cross-Check — Fatia 2

| Task | Depends On (body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T6 | None | (raiz) | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |
| T10 | T8 | T8 → T10 (via T9 na Phase 2, sequencial) | ✅ Match |
| T11 | T8 | T8 → T11 | ✅ Match |
| T12 | T8 | T8 → T12 | ✅ Match |
| T13 | T11, T12 | T11 → T13, T12 → T13 | ✅ Match |
| T14 | T9, T10, T13 | T9, T10, T13 → T14 | ✅ Match |

## Test Co-location Validation — Fatia 2

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T6 | Dev infra / config | none | none | ✅ OK |
| T7 | Schema / migrações | none | none | ✅ OK |
| T8 | Persistência — conexão/migrar | integration | integration | ✅ OK |
| T9 | Persistência — adapter lotes | integration | integration | ✅ OK |
| T10 | Persistência — adapter limite | integration | integration | ✅ OK |
| T11 | Ingestão — limite RJ | integration | integration | ✅ OK |
| T12 | Ingestão — SIGEF | integration | integration | ✅ OK |
| T13 | Ingestão — publicação | integration | integration | ✅ OK |
| T14 | Fim-a-fim | integration | integration | ✅ OK |

Nenhuma violação. Nenhum "testado em outra task" — cada task carrega seu próprio teste.
