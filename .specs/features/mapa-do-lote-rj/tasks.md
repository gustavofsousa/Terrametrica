# Mapa do Lote no RJ (F1.8 + F1.13) Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/mapa-do-lote-rj/design.md`
**Spec**: `.specs/features/mapa-do-lote-rj/spec.md` (r1)
**Status**: Draft

> Nomenclatura do repo: esta é a **Fatia 10** (após F1.12). A migração segue o padrão
> `0008_f113_municipio.sql`; o rollback fica em `migracoes/rollback/0008_f113_municipio.down.sql`.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec — confirm before Execute.
> **Guidelines found:** `~/.claude/CLAUDE.md` (testes derivam dos ACs), `pyproject.toml` (ruff, mypy
> strict, pytest `testpaths=tests`), `docs/DEV-SETUP.md` (comandos). Nenhum threshold de cobertura
> → forte default (todo AC + todo edge case), com o layout atual por camada técnica.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Ingestão (funções puras e validação) | unit | Todas as branches; MUN-04/05 1:1; malha com 91, 93, código fora de `33`, geometria vazia | `tests/unit/ingestao/test_*.py` | `.venv/bin/pytest tests/unit -q` |
| Ingestão + publicação contra PostGIS | integration | MUN-01/06/07, guarda com a camada `municipio` | `tests/integration/ingestao/test_*.py` | `.venv/bin/pytest tests/integration -q` |
| Migração + rollback | integration | Idempotência, rollback sem tocar tabelas de lote (MUN-09) | `tests/integration/persistencia/test_*.py` | `.venv/bin/pytest tests/integration -q` |
| Domínio (`modelos.py`, `montagem.py`) | unit (fakes) | `SemLote` com município e com `None` | `tests/unit/dossie/test_*.py` | `.venv/bin/pytest tests/unit -q` |
| Repositório PostGIS | integration | Ponto em município, ponto no mar, geometria `[lon, lat]` com 6 casas, nomes ordenados | `tests/integration/persistencia/test_*.py` | `.venv/bin/pytest tests/integration -q` |
| DTO (`api/dto.py`) | unit | Campos novos em 200/404/409 | `tests/unit/api/test_dto.py` | `.venv/bin/pytest tests/unit -q` |
| Rotas (`api/app.py`) | integration (TestClient) | Happy + edge + erro de cada rota tocada; `consulta_log` sem geometria | `tests/integration/api/test_*.py` | `.venv/bin/pytest tests/integration -q` |
| Módulos JS puros (`app/*.js` exceto `mapa.js`) | unit (`node --test`) | 1:1 com os ACs de lógica; respostas fora de ordem; URL inválida | `app/tests/*.test.mjs` | `node --test app/tests/*.test.mjs` |
| Shell do mapa (`mapa.js`, `index.html`, `estilos.css`) | e2e (pytest-playwright, AD-017) | Cada AC de UI listado na task + UX DoD | `tests/navegador/test_*.py` | `.venv/bin/pytest tests/navegador -m navegador -q` |
| Docs | none | — | — | revisão manual |

**Spec tags:** todo teste novo leva `spec:mapa-do-lote-rj` e o ID do requisito no nome ou no
docstring (ex.: `test_mun04_malha_com_91_municipios_nao_publica`). JS: `test("MAPA-11 …")`.

## Parallelism Assessment

> Generated from codebase — confirm before Execute.

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --- | --- | --- | --- |
| unit (pytest) | Yes | Fakes em memória, sem I/O | `tests/fakes/repositorio_fake.py` |
| integration (pytest) | No | Container PostGIS por módulo, com tabelas compartilhadas | `PostgresContainer` em `tests/integration/api/test_api_e2e.py` |
| unit (`node --test`) | Yes | Módulos puros, sem DOM | `app/tests/dossie.test.mjs` |
| e2e (navegador) | No | Um servidor uvicorn + um PostGIS por sessão | AD-017 (novo) |

## Gate Check Commands

> Generated from codebase — confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Task só com unit | `.venv/bin/pytest tests/unit -q && node --test app/tests/*.test.mjs` |
| Full | Task com integration ou e2e | `.venv/bin/pytest tests/unit tests/integration -q && node --test app/tests/*.test.mjs` (+ `.venv/bin/pytest tests/navegador -m navegador -q` a partir da T19) |
| Build | Fim de fase | `.venv/bin/ruff check src tests && .venv/bin/mypy && ` + Full |

---

## Execution Plan

### Phase 1: Base — malha municipal (Sequential; integration não é paralelo)

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9
```

### Phase 2: API (Sequential)

```
T9 → T10 → T11 → T12
```

### Phase 3: Front — módulos puros (Parallel OK)

```
        ┌→ T13 [P] ─→ T17
T12 ────┼→ T14 [P]
        ├→ T15 [P]
        ├→ T16 [P]
        └→ T18 [P]
```

### Phase 4: Front — mapa no navegador (Sequential; e2e não é paralelo)

```
T13..T18 → T19 → T20 → T21 → T22 → T23 → T24
```

### Phase 5: Fechamento

```
T24 → T25
```

---

## Task Breakdown

### T1: Migração da tabela `municipio` + rollback

**What**: `0008_f113_municipio.sql` (tabela `municipio`, índice GiST, coluna `proveniencia.sha256`) e o script manual de rollback.
**Context**: O repo tem 7 migrações aplicadas por `persistencia/migrar.py`, que lê só `migracoes/*.sql`. Nada referencia `municipio` ainda. Ao fim, a tabela existe com o DDL do design, o script em `migracoes/rollback/` desfaz só o que a 0008 criou, e o runner continua ignorando a subpasta.
**Where**: `src/terrametrica/persistencia/migracoes/0008_f113_municipio.sql`, `src/terrametrica/persistencia/migracoes/rollback/0008_f113_municipio.down.sql`
**Depends on**: None
**Reuses**: `0007_f19_lote_urbano.sql`, `tests/integration/persistencia/test_migrar.py`
**Requirement**: MUN-01, MUN-09

**Done when**:
- [x] Aplicar as migrações 2× não falha e cria `municipio` com o `CHECK` de 7 dígitos.
- [x] Teste MUN-09: migrar → semear um lote → rodar o rollback → `lote_rural`, `restricao` e `ponteiro_publicado` sem mudança e `municipio` inexistente.
- [x] O runner não aplica nada de `migracoes/rollback/`.
- [x] Gate full passa; contagem de testes sobe, nenhuma remoção.

**Tests**: integration
**Gate**: full
**Commit**: `feat(persistencia): migração 0008 da malha municipal com rollback`

---

### T2: `ingerir_municipios_rj` com validação e SHA canônico

**What**: Função de ingestão da malha (geobr 2025, `simplified=False`) com leitor injetável, `MalhaIncompleta` e `sha256_canonico`.
**Context**: T1 criou a tabela. `ingestao/limite_rj.py` mostra o padrão (geobr → 4674 → corrigir → INSERT sem commit). Ao fim, a função grava 92 linhas, apaga antes as linhas da mesma versão (idempotente), grava a proveniência "IBGE — Malha Municipal 2025" com o SHA e falha alto com contagem errada.
**Where**: `src/terrametrica/ingestao/municipios_rj.py`, `tests/fixtures/municipio/`
**Depends on**: T1
**Reuses**: `ingestao/limite_rj.py`, `ingestao/validacao_geometria.py`, `ingestao/tipos.py`
**Requirement**: MUN-01, MUN-04, MUN-05, MUN-06

**Done when**:
- [x] Unit: 91 municípios, 93, um código fora de `33` e uma geometria vazia → `MalhaIncompleta` com a contagem na mensagem.
- [x] Unit: o mesmo GeoDataFrame em ordem diferente → o mesmo SHA.
- [x] Integration: 92 feições sintéticas → 92 linhas; segunda carga na mesma versão → 92 linhas; proveniência com SHA.
- [x] Gate full passa.

**Tests**: unit + integration
**Gate**: full
**Commit**: `feat(ingestao): malha municipal do RJ versionada (F1.8)`

---

### T3: `limite_estado` em resolução completa

**What**: `ingerir_limite_rj` passa a pedir a malha estadual com `simplified=False`, por um leitor injetável igual ao da T2.
**Context**: Hoje `limite_rj.py:38` chama `read_state` com o padrão `simplified=True`. Medido: isso deixa 1 lote SIGEF real fora do RJ e ~25 km² de frestas com a malha municipal (AD-016). Ao fim, o leitor recebe a resolução completa e o resto da função não muda.
**Where**: `src/terrametrica/ingestao/limite_rj.py`
**Depends on**: T2
**Reuses**: o parâmetro `ler=` da T2
**Requirement**: AD-016 (garante a coerência estado × municípios usada por MUN-02)

**Done when**:
- [x] Unit: um leitor fake registra que a chamada pediu ano 2025 e resolução completa.
- [x] Testes atuais de `limite_rj` continuam verdes.
- [x] Gate quick passa.

**Tests**: unit
**Gate**: quick
**Commit**: `fix(ingestao): limite do RJ em resolução completa (AD-016)`

---

### T4: Guarda de publicação e carga incluem `municipio`

**What**: `publicar.py` conta a camada `municipio`; `carregar_base.py` chama `ingerir_municipios_rj` logo após o limite.
**Context**: A guarda de 90% é por camada e a decisão de publicar é única (`publicar.py`). Ao fim, uma versão sem municípios não publica se a anterior tinha, e a CLI de carga ingere a malha sem argumento novo (vem do geobr).
**Where**: `src/terrametrica/ingestao/publicar.py`, `src/terrametrica/ingestao/carregar_base.py`
**Depends on**: T3
**Reuses**: `_CAMADAS_PUBLICADAS`, `_QUERY_CONTAGEM_POR_CAMADA`
**Requirement**: MUN-01, MUN-04

**Done when**:
- [x] Integration: versão anterior com 92 municípios e nova com 0 → publicação rejeitada e ponteiro intacto.
- [x] Integration: primeira versão com 92 → publica e o ponteiro `municipio` aponta para ela.
- [x] Gate full passa.

**Tests**: integration
**Gate**: full
**Commit**: `feat(ingestao): guarda e carga incluem a malha municipal`

---

### T5: Cobertura com os 92 municípios

**What**: `semear_cobertura` tira o conjunto de municípios da tabela `municipio` da versão (AD-016).
**Context**: Hoje o conjunto vem de `lote_rural.municipios` ∪ `lote_urbano.municipio` (AD-009). Ao fim, cada município da malha tem uma linha por camada, com `tem_dado=false` onde a camada não tem feição nele.
**Where**: `src/terrametrica/ingestao/cobertura.py`
**Depends on**: T4
**Reuses**: o SQL atual de `semear_cobertura`
**Requirement**: MUN-07

**Done when**:
- [x] Integration: 3 municípios na malha, lote em só 1 → 3 × N camadas linhas, `tem_dado=true` só no município com lote.
- [x] Testes atuais de cobertura continuam verdes.
- [x] Gate full passa.

**Tests**: integration
**Gate**: full
**Commit**: `feat(cobertura): semeia os municípios da malha (MUN-07)`

---

### T6: Value object `Municipio` e `SemLote.municipio` opcional

**What**: `Municipio(codigo, nome)` no domínio; `SemLote.municipio: Municipio | None`; porta `municipio_em` com o novo retorno; fake atualizado.
**Context**: `montagem.py:61` chama `municipio_em` e depois `cobertura_de(municipio)`. Ao fim, com `None` a montagem devolve `SemLote(None, ())` sem chamar `cobertura_de`; com município, chama pelo código.
**Where**: `src/terrametrica/dominio/modelos.py`, `src/terrametrica/dossie/portas.py`, `src/terrametrica/dossie/montagem.py`, `tests/fakes/repositorio_fake.py`
**Depends on**: T5
**Reuses**: value objects atuais (`dataclass(frozen=True)`)
**Requirement**: MUN-02, MUN-03

**Done when**:
- [x] Unit: ponto no RJ sem lote com município no fake → `SemLote` com código e nome.
- [x] Unit: fake sem município → `SemLote(municipio=None, cobertura=())`.
- [x] mypy strict passa.
- [x] Gate quick passa.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(dossie): SemLote carrega o município (código e nome)`

---

### T7: `municipio_em` real no PostGIS

**What**: Implementar `RepositorioLotesPostGIS.municipio_em` com `ST_Contains` na versão.
**Context**: Hoje o método levanta `NotImplementedError` (TD-001). T6 fixou o retorno. Ao fim, o ponto devolve o município da versão pedida, e o ponto fora de todo município devolve `None`.
**Where**: `src/terrametrica/persistencia/repositorio_lotes_postgis.py`
**Depends on**: T6
**Reuses**: `_SELECT_LOTE_NO_PONTO` (forma do SQL)
**Requirement**: MUN-02

**Done when**:
- [x] Integration: ponto dentro do município A → A; ponto no mar → `None`; mesma coordenada em duas versões com malhas diferentes → o município de cada versão.
- [x] `MENSAGEM_TD_001` removida.
- [x] Gate full passa.

**Tests**: integration
**Gate**: full
**Commit**: `feat(persistencia): municipio_em pela malha (fecha TD-001)`

---

### T8: Leitura de geometria do lote e do contorno do RJ

**What**: `geometrias_de(lote_ids, versao)` e `contorno_estado(versao)` no repositório.
**Context**: Nenhuma leitura de geometria existe hoje. Ao fim, as duas devolvem GeoJSON como `dict`: o lote com 6 casas e `[lon, lat]`, rural e urbano na mesma chamada; o contorno simplificado só para desenho.
**Where**: `src/terrametrica/persistencia/repositorio_lotes_postgis.py`
**Depends on**: T7
**Reuses**: o estilo de SQL atual
**Requirement**: MAPA-04, MAPA-06, MAPA-07

**Done when**:
- [x] Integration: lote rural e urbano conhecidos → `type` correto, primeira coordenada com `lon` < -40 e `lat` > -24 (ordem certa), no máximo 6 casas.
- [x] Integration: id inexistente → ausente do `dict`, sem erro.
- [x] Integration: contorno → `MultiPolygon` válido com menos vértices que o original.
- [x] Gate full passa.

**Tests**: integration
**Gate**: full
**Commit**: `feat(persistencia): leitura de geometria do lote e do contorno do RJ`

---

### T9: Cobertura de todos com nome do município

**What**: `cobertura_de_todos` junta o nome da `municipio` publicada e ordena por nome.
**Context**: Hoje ordena pelo código e não tem nome. Ao fim, `CoberturaMunicipio` ganha `nome` e a lista vem em ordem alfabética.
**Where**: `src/terrametrica/persistencia/repositorio_lotes_postgis.py`, `src/terrametrica/dominio/modelos.py`
**Depends on**: T8
**Reuses**: `_SELECT_COBERTURA_TODOS`
**Requirement**: MUN-08

**Done when**:
- [x] Integration: 3 municípios → 3 itens com nome, em ordem alfabética.
- [x] Gate full + build passam (fim da fase 1).

**Tests**: integration
**Gate**: build
**Commit**: `feat(cobertura): nome do município na cobertura de todos`

---

### T10: `/dossie` com geometria e nome do município

**What**: DTO e rota: `lote.geometria` (200), `candidatos[].geometria` (409), `municipio` + `municipio_nome` (404).
**Context**: `api/dto.py` projeta os resultados e `api/app.py::_montar_e_traduzir` orquestra. Ao fim, a rota chama `geometrias_de` depois de montar o dossiê, e o `consulta_log` não muda.
**Where**: `src/terrametrica/api/dto.py`, `src/terrametrica/api/app.py`
**Depends on**: T9
**Reuses**: `test_api_e2e.py` (container + seed)
**Requirement**: MAPA-06, MAPA-07, MAPA-10, MUN-03

**Done when**:
- [x] Unit (DTO): os três corpos têm os campos novos; 404 com `municipio=None` → `municipio_nome=None`.
- [x] Integration: 200 com geometria; 409 com geometria em cada candidato; 404 com nome; linha do `consulta_log` sem coluna nova.
- [x] Gate full passa.

**Tests**: unit + integration
**Gate**: full
**Commit**: `feat(api): geometria do lote e nome do município no /dossie`

---

### T11: `GET /mapa/contorno`

**What**: Rota pública com o contorno do RJ, `Cache-Control: public, max-age=86400` e `ETag` igual ao id da versão.
**Context**: `/cobertura/estado` é o modelo de rota pública. Ao fim, a rota devolve uma Feature GeoJSON e responde 304 para um `If-None-Match` igual.
**Where**: `src/terrametrica/api/app.py`
**Depends on**: T10
**Reuses**: `contorno_estado` (T8)
**Requirement**: MAPA-04

**Done when**:
- [x] Integration: 200 com Feature, `ETag` e `Cache-Control`; 304 com `If-None-Match`; sem versão publicada → 503 com mensagem.
- [x] Gate full passa.

**Tests**: integration
**Gate**: full
**Commit**: `feat(api): rota do contorno do RJ com cache`

---

### T12: `/cobertura/estado` com nome

**What**: `cobertura_estado_para_dict` inclui `municipio_nome`.
**Context**: T9 trouxe o nome do repositório. Ao fim, o JSON tem código e nome por município, em ordem alfabética.
**Where**: `src/terrametrica/api/dto.py`
**Depends on**: T11
**Reuses**: teste atual de `/cobertura/estado`
**Requirement**: MUN-08

**Done when**:
- [x] Unit + integration: cada item tem `municipio` e `municipio_nome`; ordem alfabética.
- [x] Gate full + build passam (fim da fase 2).

**Tests**: unit + integration
**Gate**: build
**Commit**: `feat(api): nome do município na cobertura pública`

---

### T13: View model do dossiê com os estados novos [P]

**What**: `dossie.js` ganha `fora_do_rj` (422), `erro_rede`, área formatada (ha ou m²), perímetro, geometria e `municipioNome`.
**Context**: `renderDossie({status, corpo})` cobre 200/404/409/429 e cai em "Erro inesperado" no resto. Ao fim, o 422 vira `fora_do_rj` e o 404 mostra o nome do município.
**Where**: `app/dossie.js`, `app/tests/dossie.test.mjs`
**Depends on**: T12
**Reuses**: testes atuais de `dossie.test.mjs`
**Requirement**: MAPA-05, MAPA-09, MUN-03

**Done when**:
- [x] `node --test`: 422 → `fora_do_rj` com "Fora do estado do Rio de Janeiro"; rural 12,4 ha → "12,4 ha"; urbano → m²; 404 com nome e com `null`.
- [x] Testes atuais continuam verdes.
- [x] Gate quick passa.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(app): estados fora-do-RJ e área no view model do dossiê`

---

### T14: Controlador "o último clique vence" [P]

**What**: `consultas.js` com número de sequência, `fetch` injetado e timeout de 15 s.
**Context**: Hoje `mapa.js` faz `fetch` direto e qualquer resposta pinta o painel. Ao fim, só a resposta do clique mais recente chega ao callback, e timeout ou falha de rede vira `erro_rede` com o ponto preservado.
**Where**: `app/consultas.js`, `app/tests/consultas.test.mjs`
**Depends on**: T12
**Reuses**: nenhum
**Requirement**: MAPA-11, MAPA-18

**Done when**:
- [x] `node --test`: clique A lento + clique B rápido → só B entrega; B lento + A já descartado → só B; fetch que nunca resolve → `erro_rede` após o timeout (relógio fake).
- [x] Gate quick passa.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(app): o último clique vence nas consultas do mapa`

---

### T15: Seleção na URL [P]

**What**: `url.js` com `lerSelecao(search)` e `escreverSelecao(lat, lon)`.
**Context**: Não existe estado na URL hoje. Ao fim, `?lat=&lon=` dentro do bbox do RJ vira um ponto; texto, `NaN` ou fora do bbox → `null`; a escrita usa 6 casas.
**Where**: `app/url.js`, `app/tests/url.test.mjs`
**Depends on**: T12
**Reuses**: nenhum
**Requirement**: MAPA-13, MAPA-14

**Done when**:
- [x] `node --test`: válido, inválido, fora do bbox, faltando um parâmetro, 6 casas na escrita.
- [x] Gate quick passa.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(app): seleção do ponto na URL`

---

### T16: Geometria no cliente: bbox e máscara [P]

**What**: `geometria.js` com `bboxDe(geojson)` e `mascaraFora(contorno)`.
**Context**: O enquadramento do lote e a área atenuada fora do RJ precisam de lógica pura. Ao fim, o bbox cobre todas as partes de um MultiPolygon, e a máscara é um retângulo do mundo com os anéis externos do RJ como furos.
**Where**: `app/geometria.js`, `app/tests/geometria.test.mjs`
**Depends on**: T12
**Reuses**: `prototipos/mapa-dossie/tests/geom.test.mjs` (estilo)
**Requirement**: MAPA-04, MAPA-08

**Done when**:
- [x] `node --test`: Polygon, MultiPolygon com partes distantes, máscara com N furos para N partes do RJ.
- [x] Gate quick passa.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(app): bbox do lote e máscara fora do RJ`

---

### T17: Renderização do painel

**What**: `painel.js` gera o HTML de cada estado do view model, com `esc()` em todo texto e `aria-busy` na espera.
**Context**: As funções `html*` vivem hoje em `mapa.js`. Ao fim, elas ficam em `painel.js` e cobrem os estados novos da T13, incluindo área, perímetro, proveniência e o botão "Tentar de novo".
**Where**: `app/painel.js`, `app/tests/painel.test.mjs`
**Depends on**: T13
**Reuses**: `esc()` e `html*` de `app/mapa.js`
**Requirement**: MAPA-09, MAPA-17, MAPA-18

**Done when**:
- [ ] `node --test`: um nome com `<script>` sai escapado; `erro_rede` tem o botão; `dossie` mostra área, perímetro, fonte e data.
- [ ] Gate quick passa.

**Tests**: unit
**Gate**: quick
**Commit**: `refactor(app): renderização do painel em módulo próprio`

---

### T18: Cobertura pública com nome [P]

**What**: `cobertura.js` usa `municipio_nome` na tabela.
**Context**: T12 trouxe o nome no JSON. Ao fim, a página lista os 92 nomes, e o código só aparece como atributo para depuração.
**Where**: `app/cobertura.js`, `app/tests/cobertura.test.mjs`
**Depends on**: T12
**Reuses**: teste atual
**Requirement**: MUN-08

**Done when**:
- [ ] `node --test`: o view model traz o nome; o código não aparece como texto visível.
- [ ] Gate quick + build passam (fim da fase 3).

**Tests**: unit
**Gate**: build
**Commit**: `feat(app): página de cobertura com nome do município`

---

### T19: Harness de navegador (AD-017)

**What**: `pytest-playwright` no extra `dev`, marcador `navegador`, fixture de sessão com PostGIS + seed + uvicorn em thread + estilo de basemap mínimo interceptado.
**Context**: Não há teste de navegador no repo. `test_api_e2e.py` mostra como subir o container e semear. Ao fim, `pytest tests/navegador -m navegador` abre a página e acha o canvas do mapa, sem rede externa, e a suíte padrão não roda esses testes.
**Where**: `pyproject.toml`, `tests/navegador/conftest.py`, `tests/navegador/test_smoke.py`, `docs/DEV-SETUP.md`
**Depends on**: T13, T14, T15, T16, T17, T18
**Reuses**: fixture de container de `tests/integration/api/test_api_e2e.py`
**Requirement**: AD-017

**Done when**:
- [ ] Smoke: a fixture abre `cobertura.html` e acha a tabela de cobertura. O teste do canvas do mapa entra na T20.
- [ ] `pytest tests/unit tests/integration` não coleta `tests/navegador`.
- [ ] DEV-SETUP explica `playwright install chromium`.
- [ ] Gate full passa.

**Tests**: e2e
**Gate**: full
**Commit**: `test(navegador): harness pytest-playwright (AD-017)`

---

### T20: Mapa em MapLibre focado no RJ

**What**: `index.html` + `mapa.js`: MapLibre 6.14.0, OpenFreeMap `positron`, enquadramento no RJ, contorno, máscara, clique → `consultas.js` → `painel.js`, camada `lote-selecionado` e enquadramento com `padding`.
**Context**: Hoje `mapa.js` usa Leaflet + tiles OSM e só põe um marcador. T13–T17 deram a lógica pura. Ao fim, o shell só liga DOM e MapLibre, e nenhuma requisição vai a `tile.openstreetmap.org`.
**Where**: `app/index.html`, `app/mapa.js`, `app/estilos.css`, `tests/navegador/test_mapa.py`
**Depends on**: T19
**Reuses**: skill `web-map` (`map-template.html`) e `map-ux` (`map-app-template.html`)
**Requirement**: MAPA-01, MAPA-02, MAPA-03, MAPA-04, MAPA-05, MAPA-08

**Done when**:
- [ ] E2E: nenhuma URL com `tile.openstreetmap.org`; atribuição visível; câmera inicial dentro do bbox do RJ; arraste para fora permitido.
- [ ] E2E: estilo bloqueado → "Mapa base indisponível"; clique ainda consulta.
- [ ] E2E: clique num lote semeado → camada `lote-selecionado` com o id; bbox do lote dentro da área livre do painel; com `reducedMotion: reduce`, sem animação.
- [ ] E2E: clique fora do RJ → "Fora do estado do Rio de Janeiro".
- [ ] UX DoD: foco visível, atribuição legível (contraste ≥ 4,5:1), estado de espera, sem rolagem horizontal em 320 px.
- [ ] Gate full passa.

**Tests**: e2e
**Gate**: full
**Commit**: `feat(app): mapa em MapLibre + OpenFreeMap focado no RJ (AD-015)`

---

### T21: Candidatos da sobreposição no mapa

**What**: 409 desenha todos os candidatos (tracejado) e destaca o candidato sob o cursor na lista e no mapa.
**Context**: T20 desenha só o lote selecionado. Ao fim, `hover` e `selected` são dois `feature-state` com aparências diferentes.
**Where**: `app/mapa.js`, `app/painel.js`, `tests/navegador/test_mapa.py`
**Depends on**: T20
**Reuses**: padrão "hover is not selection" da skill `map-ux`
**Requirement**: MAPA-12

**Done when**:
- [ ] E2E: clique na sobreposição semeada → N contornos; hover na linha da lista → `feature-state.hover` no candidato certo.
- [ ] Gate full passa.

**Tests**: e2e
**Gate**: full
**Commit**: `feat(app): candidatos da sobreposição no mapa`

---

### T22: URL e Esc no mapa

**What**: Ligar `url.js` ao shell: abrir com `?lat=&lon=` consulta; clique faz `replaceState`; Esc limpa.
**Context**: T15 deu o parser. Ao fim, recarregar a página mantém o lote, e o histórico não cresce por clique.
**Where**: `app/mapa.js`, `tests/navegador/test_mapa.py`
**Depends on**: T21
**Reuses**: `url.js`
**Requirement**: MAPA-13, MAPA-14

**Done when**:
- [ ] E2E: abrir com parâmetros de um lote → contorno e dossiê; parâmetro inválido → nenhuma requisição a `/dossie`; 3 cliques → `history.length` igual; Esc → sem contorno e sem parâmetros.
- [ ] Gate full passa.

**Tests**: e2e
**Gate**: full
**Commit**: `feat(app): seleção do lote compartilhável pela URL`

---

### T23: Bottom sheet no celular

**What**: `@media (max-width: 640px)`: painel vira folha inferior ≤ 50vh; `padding` inferior da câmera igual à altura da folha.
**Context**: O layout atual é de duas colunas. Ao fim, num viewport de 390×844 o mapa ocupa a largura inteira e o lote enquadrado fica acima da folha.
**Where**: `app/estilos.css`, `app/mapa.js`, `tests/navegador/test_mapa.py`
**Depends on**: T22
**Reuses**: padrão "phones get a bottom sheet" da skill `map-ux`
**Requirement**: MAPA-15, MAPA-16

**Done when**:
- [ ] E2E (390×844): altura da folha ≤ 422 px; bbox do lote acima da folha; toque no mapa visível consulta.
- [ ] UX DoD: alvos de toque ≥ 44 px; sem rolagem horizontal.
- [ ] Gate full passa.

**Tests**: e2e
**Gate**: full
**Commit**: `feat(app): painel como folha inferior no celular`

---

### T24: Espera, erro de rede e foco

**What**: Ligar `aria-busy`, "Tentar de novo" e o foco no título do painel ao shell.
**Context**: T14 e T17 deram a lógica e o HTML. Ao fim, a API bloqueada mostra o erro com o botão, o botão repete o mesmo ponto, e o resultado move o foco sem interromper um arraste.
**Where**: `app/mapa.js`, `tests/navegador/test_mapa.py`
**Depends on**: T23
**Reuses**: `consultas.js`, `painel.js`
**Requirement**: MAPA-17, MAPA-18, MAPA-19

**Done when**:
- [ ] E2E: durante a consulta, `aria-busy="true"` e o lote anterior sem estilo de selecionado; API bloqueada → erro + botão; liberar e clicar → dossiê do mesmo ponto; o foco vai para o `h2` do painel.
- [ ] Gate full + build passam (fim da fase 4).

**Tests**: e2e
**Gate**: build
**Commit**: `feat(app): estados de espera e erro de rede no mapa`

---

### T25: Docs e fechamento

**What**: README ("Estado atual" real), roadmap (F1.8 e F1.13 ✅), TD-001 resolvido no `TECH-DEBT.md`, handoff no `STATE.md`.
**Context**: O README ainda diz que não há camada HTTP. Ao fim, as docs batem com o código desta feature.
**Where**: `README.md`, `docs/produto/roadmap.md`, `.specs/TECH-DEBT.md`, `.specs/STATE.md`
**Depends on**: T24
**Reuses**: formato atual do handoff
**Requirement**: DOC-01

**Done when**:
- [ ] README lista API, painel, cobertura, deploy (AD-013) e esta feature; a frase "zero código" sumiu.
- [ ] TD-001 com status `resolved` e o commit da T7.

**Tests**: none
**Gate**: build
**Commit**: `docs: estado atual do produto e fechamento de F1.8/F1.13`

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1 | 1 migração + seu rollback | ✅ coeso |
| T2 | 1 função de ingestão (+ 2 helpers no mesmo arquivo) | ✅ coeso |
| T3 | 1 parâmetro | ✅ |
| T4 | 2 arquivos, uma regra (camada nova na carga) | ⚠️ OK, coeso |
| T5 | 1 função | ✅ |
| T6 | 1 tipo propagado por porta e fake | ⚠️ OK, mudança de assinatura indivisível |
| T7–T9 | 1 método cada | ✅ |
| T10 | 1 rota + seu DTO | ⚠️ OK, coeso |
| T11, T12 | 1 rota / 1 DTO | ✅ |
| T13–T18 | 1 módulo cada | ✅ |
| T19 | 1 harness | ✅ |
| T20 | 1 shell (troca de motor) | ⚠️ OK: não divide sem deixar o mapa quebrado entre commits |
| T21–T24 | 1 comportamento cada | ✅ |
| T25 | docs | ✅ |

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | início | ✅ |
| T2–T9 | anterior | cadeia T1→T9 | ✅ |
| T10 | T9 | T9→T10 | ✅ |
| T11, T12 | anterior | T10→T11→T12 | ✅ |
| T13–T16, T18 | T12 | T12→cada [P] | ✅ |
| T17 | T13 | T13→T17 | ✅ |
| T19 | T13–T18 | T13..T18→T19 | ✅ |
| T20–T24 | anterior | cadeia T19→T24 | ✅ |
| T25 | T24 | T24→T25 | ✅ |

## Test Co-location Validation

| Task | Code Layer | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | migração | integration | integration | ✅ |
| T2 | ingestão (pura + PostGIS) | unit + integration | unit + integration | ✅ |
| T3 | ingestão (pura) | unit | unit | ✅ |
| T4, T5 | ingestão + publicação | integration | integration | ✅ |
| T6 | domínio | unit | unit | ✅ |
| T7–T9 | repositório | integration | integration | ✅ |
| T10, T12 | DTO + rota | unit + integration | unit + integration | ✅ |
| T11 | rota | integration | integration | ✅ |
| T13–T18 | JS puro | unit | unit | ✅ |
| T19–T24 | shell do mapa | e2e | e2e | ✅ |
| T25 | docs | none | none | ✅ |

## Tools per task

| Tasks | MCP | Skill |
| --- | --- | --- |
| T1–T9 | NONE | `maps:spatial-sql`, `maps:geo-data-br`, `maps:geo-pipeline` |
| T10–T12 | NONE | `python-delivery-stack` |
| T13–T18 | NONE | `maps:web-map` (ordem `[lon, lat]`) |
| T19 | `context7` (API do pytest-playwright) | `e2e-testing-patterns` |
| T20–T24 | `playwright` (inspeção ao vivo) | `maps:web-map`, `maps:map-ux` |
| T25 | NONE | `ste-writing` |
