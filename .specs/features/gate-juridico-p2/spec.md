# Gate de Permissão Jurídica (P2) Specification

**Provenance**: esta feature promove a um feature próprio a história "P2: Gate de permissão
jurídica arquitetado, sem dado pessoal" já escrita e aprovada em
`.specs/features/dossie-lote-rj/spec.md` (mesmas Acceptance Criteria, mesma "Why P2"). Não é
escopo novo — é a mesma decisão de produto ganhando seu próprio spec/design/tasks porque a
ingestão (Fatia 2 de `dossie-lote-rj`) está em execução em outra sessão e este trabalho é
totalmente independente dela.

## Problem Statement

O produto decidiu (AD-002) que dado de proprietário — nome, CPF/CNPJ, ônus, cadeia dominial — fica
fora do MVP até existir caminho jurídico confirmado com o ONR. Mas construir a autorização e a
auditoria só quando esse caminho existir significa reescrever o sistema sob pressão. Construído
agora, vazio de dado pessoal, o gate custa pouco e transforma o dia em que a camada registral for
liberada em "ligar uma chave", não em um redesenho.

## Goals

- [ ] Toda conta do produto tem exatamente um papel (`consulta` ou `habilitado_juridicamente`), sem estado indefinido
- [ ] Nenhuma tentativa de acesso a dado registral passa sem decisão e sem registro em log — permitida ou negada
- [ ] Nenhum nome, CPF ou CNPJ de proprietário é representável em qualquer estrutura desta fatia

## Out of Scope

Explicitamente excluído. Documentado para evitar avanço de escopo.

| Feature | Reason |
| --- | --- |
| Persistência real (Postgres) de `conta` e `log_auditoria` | Depende de `persistencia/conexao.py` e `persistencia/migrar.py`, que a Fatia 2 de `dossie-lote-rj` está construindo agora em outra sessão. Construir sobre essa base antes dela estabilizar duplicaria retrabalho. Vira Slice 2 desta feature. |
| Endpoint HTTP real (403, roteamento FastAPI) | A API ainda não existe no projeto (nenhuma fatia chegou lá). O domínio produz a decisão (`Permitido`/`Negado`); a tradução para HTTP 403 é responsabilidade de uma fatia futura de API. |
| Mecanismo de verificação de credencial (OAB, cartório, gov.br etc.) | Não decidido em nenhum documento do produto. Esta fatia recebe a credencial como identificador opaco já verificado por processo externo/manual — não implementa a verificação em si. |
| Quem tem permissão para chamar `promover_conta` | É uma decisão de autorização da camada de API/operação (quem opera o painel administrativo), fora do domínio puro. Registrado como assumption abaixo. |
| Limite de 100 consultas/hora (DOS-27) | Pertence à camada de API do dossiê consultivo em geral (rate limit de qualquer consulta), não ao gate registral especificamente. Seguirá com a fatia de API do dossiê. |
| Ingestão ou exibição de qualquer dado de proprietário | Fora do produto nesta versão inteira (AD-002), não só desta feature. |

---

## Assumptions & Open Questions

Toda ambiguidade está resolvida ou registrada aqui — nada fica silenciosamente indefinido.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Formato da credencial verificada | String opaca (`str`) carimbada na promoção, sem estrutura interna validada por este domínio | A ACs pedem "sob qual credencial verificada" ser registrado, não que o domínio valide a credencial em si — isso pertence ao processo externo que a verifica antes de chamar `promover_conta` | y |
| Identidade de quem promove (`promovido_por`) | String opaca (identificador de operador), mesma lógica da credencial | Mesma razão acima; autenticação de operador é decisão de uma fatia de API futura | y |
| Estado da seção de proprietário quando a camada está desligada | Constante `CAMADA_REGISTRAL_LIGADA = False` nesta versão; função pura devolve "indisponível nesta versão" para os dois papéis | AD-002: a camada nunca liga nesta versão. Modelar como constante (não como config externa) torna o estado atual verdadeiro por construção, sem exigir feature flag real ainda inexistente no produto | y |
| Granularidade do log de auditoria nesta fatia | Uma entrada por decisão de acesso (permitida ou negada) e uma por promoção — em memória via port `LogAuditoria`, sem persistência real ainda | Persistência real é Slice 2 (fora de escopo desta rodada); a Slice 1 prova a regra de decisão e a obrigação de logging por construção, testável com fake | y |
| Quem pode chamar `promover_conta` | Fora do escopo do domínio puro; a fatia de API decide isso quando existir | Autorização de operador é dimensão de auth de API, não de regra de negócio do domínio de autorização em si | y |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## Implicit-Requirement Dimensions Sweep

| Dimension | Resolução |
| --- | --- |
| Input validation & bounds | GATE-01 — papel só pode ser um dos dois valores do enum `PapelConta` já existente (`dominio/modelos.py`); estado ilegal irrepresentável |
| Failure / partial-failure states | N/A porque esta fatia é pura (sem I/O real); nenhuma falha parcial possível fora do que o fake de teste simula |
| Idempotency / retry / duplicate handling | N/A porque não há persistência real nesta fatia; cada chamada de `avaliar_acesso_registral`/`promover_conta` é determinística sobre o estado dado pelo port |
| Auth boundaries & rate limits | GATE-03 — só `habilitado_juridicamente` obtém `Permitido`; `consulta` sempre `Negado`. Rate limit (DOS-27) fora de escopo, ver Out of Scope |
| Concurrency / ordering | N/A porque a persistência real (onde concorrência importaria) é Slice 2 |
| Data lifecycle / expiry | N/A nesta fatia — nenhum dado com TTL; log de auditoria "imutável" é propriedade da Slice 2 (não há como forçar imutabilidade num fake em memória além de nunca expor método de edição/remoção) |
| Observability | GATE-05 — toda decisão de acesso é uma entrada de log, sem exceção |
| External-dependency failure | N/A porque não há dependência externa nesta fatia (domínio puro) |
| State-transition integrity | GATE-04 — promoção é a única transição de papel modelada; carrega quem/quando/credencial, e não retroage decisões passadas (a decisão de acesso é avaliada no papel atual, nunca recalculada retroativamente) |

---

## User Stories

### P1: Decisão de acesso a dado registral, sempre logada ⭐ (equivalente ao P2 original — ver Provenance)

**User Story**: Como operador do produto, quero que toda solicitação de dado registral passe por
uma decisão de autorização e gere um registro de auditoria, para poder habilitar a camada
registral no futuro sem reescrever o sistema.

**Why P1 nesta feature**: É o próprio produto desta feature — sem a decisão e o log, não há gate.
(Era P2 no roadmap geral do dossiê porque o dossiê em si é o P1 do produto; dentro desta feature
isolada, é o entregável principal.)

**Acceptance Criteria** (numeração própria desta feature; mesmo conteúdo de DOS-20/21/22 no spec
de `dossie-lote-rj`):

1. GATE-01 — The sistema SHALL atribuir a toda conta exatamente um papel entre "consulta" e "habilitado juridicamente"
2. GATE-02 — WHERE a camada registral estiver desligada o sistema SHALL exibir a seção de proprietário como "indisponível nesta versão" para todos os papéis
3. GATE-03 — IF uma conta de papel "consulta" solicitar dado registral THEN o sistema SHALL negar o acesso e SHALL registrar a tentativa
4. GATE-04 — WHEN uma conta é promovida a "habilitado juridicamente" THEN o sistema SHALL registrar quem promoveu, quando e sob qual credencial verificada
5. GATE-05 — The sistema SHALL registrar em log toda consulta a dado registral, com identidade, finalidade declarada, lote e instante
6. GATE-06 — The sistema SHALL abster-se de persistir nome, CPF ou CNPJ de proprietário em qualquer estrutura do produto nesta versão

**Independent Test**: Com um fake de repositório de contas e um fake de log em memória, criar uma
conta de cada papel, chamar a decisão de acesso registral com as duas, e conferir: a de "consulta"
volta `Negado` e gera 1 entrada de log; a de "habilitado_juridicamente" volta `Permitido` e também
gera 1 entrada de log. Promover uma conta e conferir que a entrada de promoção registra
promovido_por, instante e credencial.

---

## Edge Cases

- IF a mesma conta solicitar acesso registral duas vezes seguidas THEN o sistema SHALL registrar duas entradas de log distintas (nunca deduplicar auditoria)
- IF uma conta "habilitado_juridicamente" for rebaixada no futuro (fora de escopo desta fatia — não há operação de rebaixar ainda) THEN nenhuma decisão passada é alterada — a integridade histórica do log nunca retroage (ver GATE-04)
- WHILE `CAMADA_REGISTRAL_LIGADA` for `False` o sistema SHALL devolver "indisponível nesta versão" mesmo para conta "habilitado_juridicamente" (o papel não liga a camada sozinho — GATE-02 vale para os dois papéis)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| GATE-01 | P1: Decisão de acesso registral | Implementing | Implemented |
| GATE-02 | P1: Decisão de acesso registral | Implementing | Implemented |
| GATE-03 | P1: Decisão de acesso registral | Implementing | Implemented |
| GATE-04 | P1: Decisão de acesso registral | Implementing | Implemented |
| GATE-05 | P1: Decisão de acesso registral | Implementing | Implemented |
| GATE-06 | P1: Decisão de acesso registral | Implementing | Implemented |

**ID format:** `GATE-[NUMBER]` — 1:1 com as 6 ACs da história "P2: Gate de permissão jurídica" em
`dossie-lote-rj/spec.md` (lá rastreada em bloco só como DOS-20/21/22; aqui cada AC ganha ID próprio
para rastreabilidade fina dentro desta feature).

**Coverage:** 6 total, 6 mapeados para tasks (T1-T4), 0 não mapeados. Aguardando Verifier para status `Verified`.

---

## Success Criteria

- [ ] Uma conta "consulta" nunca recebe `Permitido` em nenhum teste, mutação ou execução
- [ ] Toda chamada à decisão de acesso produz exatamente uma entrada de log, sem exceção
- [ ] Nenhum campo do domínio desta feature é capaz de representar nome, CPF ou CNPJ (verificável por leitura de código, não só por teste)
