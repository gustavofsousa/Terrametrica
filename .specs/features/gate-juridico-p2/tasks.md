# Gate de Permissão Jurídica (P2) — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `spec-driven` skill: **activate it by name and follow its Execute
flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the
source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review,
Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user — do not proceed without it.**

---

**Design**: `.specs/features/gate-juridico-p2/design.md`
**Status**: Done — T1-T4 executadas e commitadas (2026-09-03). Aguardando Verifier.

**Isolamento operacional**: nenhuma task abaixo toca `src/terrametrica/persistencia/` ou
`src/terrametrica/ingestao/` — esses diretórios estão em execução (Fatia 2 de `dossie-lote-rj`) em
outra sessão. Todas as tasks tocam apenas `dominio/modelos.py` (acréscimo, sem remover nada
existente) e um módulo novo, `src/terrametrica/autorizacao/`.

**Slice 1 (única desta rodada)**: domínio puro — value objects, ports (Protocol) e as duas funções
de decisão/orquestração, testados com fake em memória. Slice 2 (persistência Postgres real de
`conta`/`log_auditoria`, wiring HTTP 403) fica para quando a Fatia 2 de `dossie-lote-rj` estabilizar
`persistencia/conexao.py`/`migrar.py` — ver `design.md`, Out of Scope do `spec.md`.

---

## Test Coverage Matrix

> Gerado a partir de `pyproject.toml` (pytest/ruff/mypy já configurados pela Fatia 1 de
> `dossie-lote-rj`), da amostra de testes existente (`tests/unit/dominio/`, `tests/unit/geometria/`,
> `tests/unit/dossie/`) e de `~/.claude/CLAUDE.md` ("tests derive from acceptance criteria, never
> mirror the implementation"; "make illegal states unrepresentable"). Mesmo padrão da Fatia 1: só
> pytest unit, sem infraestrutura de teste nova (nenhum I/O nesta fatia).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domínio — value objects novos (`dominio/modelos.py`: `Conta`, `EntradaAuditoria`, `TipoEventoAuditoria`, `ResultadoAcesso`, `EstadoSecao`) | unit | Todos os ramos de validação e construção; enums fechados exercitados nos dois valores | `tests/unit/dominio/test_modelos.py` (arquivo existente, acrescido) | `pytest tests/unit -q` |
| Autorização — regras puras (`autorizacao/regras.py`) | unit | 1:1 com GATE-01, 02, 03 — os dois papéis exercitados em cada função | `tests/unit/autorizacao/test_regras.py` | `pytest tests/unit -q` |
| Autorização — ports (`autorizacao/portas.py`) — Protocol | none | Build gate apenas (sem implementação a testar) | — | build gate |
| Autorização — serviço (`autorizacao/servico.py`) | unit | Toda a árvore de decisão: GATE-03, 04, 05 (com fakes dos dois ports); inclui o caso de erro (conta desconhecida) | `tests/unit/autorizacao/test_servico.py` | `pytest tests/unit -q` |

## Parallelism Assessment

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --- | --- | --- | --- |
| unit | Yes | Funções puras; fakes de `RepositorioContas`/`LogAuditoria` instanciados por teste, sem estado global mutável | Mesmo padrão de `tests/fakes/repositorio_fake.py` (Fatia 1 de `dossie-lote-rj`) — nenhum I/O nesta fatia |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Após tasks com testes unit | `pytest tests/unit -q` |
| Full | N/A nesta fatia (sem integração/e2e) | `pytest tests/unit -q` |
| Build | Fim de fase / tasks de config | `ruff check . && mypy src && pytest tests/unit -q` |

---

## Execution Plan

### Phase 1: Vocabulário do domínio (Sequential)

```
T1
```

### Phase 2: Contratos e regras (Parallel OK)

Após T1, sem dependência entre si.

```
     ┌→ T2 [P]
T1 ──┤
     └→ T3 [P]
```

### Phase 3: Orquestração (Sequential)

```
T1, T2, T3 → T4
```

3 fases → execução inline, sem sub-agentes (mesmo critério da Fatia 1 de `dossie-lote-rj`: só
oferece sub-agente por fase quando >3 fases).

---

## Task Breakdown

### T1: Value objects de autorização em `dominio/modelos.py`

**What**: Acrescentar `Conta`, `TipoEventoAuditoria`, `EntradaAuditoria`, `ResultadoAcesso`
(`Permitido`/`Negado`), `EstadoSecao`/`Indisponivel` ao módulo de domínio existente, reusando
`PapelConta` já presente. Nenhuma remoção nem modificação de código já existente no arquivo.
**Where**: `src/terrametrica/dominio/modelos.py` (acréscimo)
**Depends on**: None
**Reuses**: `PapelConta`, `ErroValidacao` (já existentes no arquivo)
**Requirement**: GATE-01, GATE-06 (base), GATE-02/04/05 (tipos usados por regras/serviço)

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`

**Done when**:
- [x] `Conta(id: str, papel: PapelConta)` frozen, sem nenhum campo que possa carregar nome/CPF/CNPJ
- [x] `TipoEventoAuditoria` enum fechado com `CONSULTA_REGISTRAL` e `PROMOCAO`
- [x] `EntradaAuditoria` frozen com os campos do design (`id`, `ts`, `conta_id`, `tipo`, `finalidade`, `lote_id`, `promovido_por`, `credencial_verificada`)
- [x] `ResultadoAcesso` como união fechada `Permitido | Negado`
- [x] `EstadoSecao` como união fechada com a variante `Indisponivel(mensagem: str)`
- [x] Testes unit cobrem construção válida de cada tipo novo e a impossibilidade estrutural de campo de dado pessoal (teste de introspecção: nenhum atributo de `Conta` bate com `nome`/`cpf`/`cnpj`)
- [x] Gate check passa: `pytest tests/unit -q`
- [x] Test count: ~6 testes passam (sem deleção silenciosa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(dominio): value objects do gate jurídico (Conta, EntradaAuditoria, ResultadoAcesso, EstadoSecao)`

---

### T2: Regras puras de autorização [P]

**What**: Implementar `avaliar_acesso_registral` e `estado_secao_proprietario`, as duas funções
puras que decidem acesso e estado da seção, sem I/O.
**Where**: `src/terrametrica/autorizacao/regras.py` (+ `src/terrametrica/autorizacao/__init__.py`)
**Depends on**: T1
**Reuses**: `PapelConta`, `ResultadoAcesso`, `EstadoSecao` (T1); padrão de `geometria/regras.py`
**Requirement**: GATE-01, GATE-02, GATE-03

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [x] `avaliar_acesso_registral(papel: PapelConta) -> ResultadoAcesso` devolve `Permitido` só para `HABILITADO_JURIDICAMENTE`, `Negado` para `CONSULTA`
- [x] `estado_secao_proprietario(papel: PapelConta) -> EstadoSecao` devolve `Indisponivel("indisponível nesta versão")` para os dois papéis, com `CAMADA_REGISTRAL_LIGADA = False` como constante do módulo
- [x] Testes unit cobrem os dois papéis em cada função (nenhum ramo sem teste)
- [x] Gate check passa: `pytest tests/unit -q`
- [x] Test count: ~4 testes passam (sem deleção silenciosa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(autorizacao): regras puras de acesso registral e estado da seção de proprietário`

---

### T3: Ports de repositório de contas e log de auditoria [P]

**What**: Definir os Protocols que o serviço de autorização consome, sem implementação concreta.
**Where**: `src/terrametrica/autorizacao/portas.py`
**Depends on**: T1
**Reuses**: padrão de `dossie/portas.py` (Protocol, sem I/O importado)
**Requirement**: fronteira (habilita GATE-03/04/05); mantém persistência real fora desta fatia

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`

**Done when**:
- [x] `RepositorioContas` (Protocol): `papel_de(conta_id: str) -> PapelConta`, `promover(conta_id: str, novo_papel: PapelConta) -> Conta`
- [x] `LogAuditoria` (Protocol): `registrar(entrada: EntradaAuditoria) -> None` — sem método de remoção/edição (garante imutabilidade estrutural, ver design.md)
- [x] `mypy src` valida os Protocols; nenhuma dependência de I/O importada
- [x] Gate check passa: `ruff check . && mypy src && pytest tests/unit -q`

**Tests**: none (Protocol — build gate, conforme matriz)
**Gate**: build

**Commit**: `feat(autorizacao): ports de repositório de contas e log de auditoria`

---

### T4: Serviço de autorização (orquestração)

**What**: Implementar `solicitar_dado_registral` e `promover_conta`, orquestrando os ports e as
regras de T2 — toda decisão de acesso gera exatamente uma entrada de log, sem exceção.
**Where**: `src/terrametrica/autorizacao/servico.py` (+ fakes em `tests/fakes/autorizacao_fake.py`)
**Depends on**: T1, T2, T3
**Reuses**: `autorizacao/regras.py` (T2), `autorizacao/portas.py` (T3), `dominio/modelos.py` (T1)
**Requirement**: GATE-03, GATE-04, GATE-05

**Tools**:
- MCP: NONE
- Skill: `python-delivery-stack`, `tdd`

**Done when**:
- [x] `solicitar_dado_registral(conta_id, finalidade, lote_id, instante, repo, log) -> ResultadoAcesso` busca o papel, aplica `avaliar_acesso_registral`, registra 1 `EntradaAuditoria` do tipo `CONSULTA_REGISTRAL` **antes de devolver o resultado**, tanto no caso `Permitido` quanto `Negado` (GATE-03/05)
- [x] `promover_conta(conta_id, promovido_por, credencial_verificada, instante, repo, log) -> Conta` chama `repo.promover(...)` e registra 1 `EntradaAuditoria` do tipo `PROMOCAO` com `promovido_por`/`credencial_verificada`/`instante` (GATE-04)
- [x] Conta desconhecida em `repo.papel_de` propaga `ErroValidacao` sem produzir entrada de log (ver design.md, Error Handling Strategy)
- [x] Fakes em memória (`ContasFake`, `LogAuditoriaFake`) implementam os ports; testes cobrem: papel `consulta` → `Negado` + 1 log; papel `habilitado_juridicamente` → `Permitido` + 1 log; promoção → 1 log de `PROMOCAO` com os 3 campos; conta desconhecida → erro propagado, 0 logs
- [x] Gate check passa: `pytest tests/unit -q`
- [x] Test count: ~5 testes passam (sem deleção silenciosa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(autorizacao): serviço de decisão de acesso registral e promoção de conta com auditoria obrigatória`

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1

Phase 2 (Parallel):
  T1 completo, então:
    ├── T2 [P]
    └── T3 [P]

Phase 3 (Sequential):
  T2, T3 completos, então:
    T4
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Value objects | 1 arquivo, acréscimo coeso | ✅ Granular |
| T2: Regras puras | 2 funções, 1 arquivo | ✅ Granular |
| T3: Ports | 1 arquivo de contratos | ✅ Granular |
| T4: Serviço | 2 funções coesas, 1 arquivo | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | (raiz) | ✅ Match |
| T2 | T1 | T1 → T2 [P] | ✅ Match |
| T3 | T1 | T1 → T3 [P] | ✅ Match |
| T4 | T1, T2, T3 | T2, T3 → T4 (e T1 via cadeia) | ✅ Match |

T2 e T3 marcados `[P]` não dependem um do outro. ✅

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Domínio — value objects novos | unit | unit | ✅ OK |
| T2 | Autorização — regras puras | unit | unit | ✅ OK |
| T3 | Autorização — ports (Protocol) | none | none | ✅ OK |
| T4 | Autorização — serviço | unit | unit | ✅ OK |

Nenhuma violação. Testes co-localizados na task que cria a camada — sem deferral.
