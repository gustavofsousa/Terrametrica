# Página de Cobertura Pública (F1.12) Specification

## Problem Statement

O produto já sabe, camada por camada e município por município, onde tem dado real (`cobertura`,
AD-009) — mas essa informação só existe hoje como JSON cru atrás de `GET /cobertura?municipio=X`
(F1.10), exigindo que o chamador já saiba o código do município e leia uma resposta técnica. F1.12
expõe essa cobertura como uma página pública e navegável: qualquer visitante — antes mesmo de criar
conta — vê de cara em quais municípios o dossiê já tem dado, em qual camada, e com que idade,
fechando DOS-29 (aviso de base obsoleta, hoje `Pending`) e servindo como vitrine de confiança do
produto.

## Goals

- [ ] Um visitante sem login enxerga, numa única página, todos os municípios com pelo menos um
      lote ingerido, cada um com o estado de cada camada de restrição (`tem_dado` + data de
      extração).
- [ ] Toda linha com dado exibe a data de extração de forma legível (não ISO cru) e sinaliza
      quando essa data está `obsoleta` segundo a regra de negócio.
- [ ] Zero nova ingestão ou cálculo de domínio: a página só projeta o que `cobertura` (via
      `RepositorioLotesPostGIS`) já registra — nenhuma lógica de `dossie`/`geometria`/`ingestao`
      muda.

## Out of Scope

Explicitamente excluído. Documentado para prevenir scope creep.

| Feature | Reason |
| --- | --- |
| Listar os 92 municípios do RJ (incluindo os sem lote) | Decisão do usuário: a página lista só municípios com pelo menos 1 lote ingerido (o que `cobertura` já registra hoje, AD-009); cobrir os 92 depende de uma malha municipal (TD-001, ainda aberto) fora do escopo desta feature. |
| Limiar automático de "base obsoleta" (marcação visual) | Decisão do usuário: sem critério de negócio definido hoje para quantos dias tornam uma camada obsoleta por tipo; a página mostra a data crua da extração, sem marcar/colorir como obsoleta. DOS-29 fecha parcialmente aqui (mostra a data) e permanece com um requisito futuro em aberto (o limiar em si). |
| Autenticação/conta | Decisão do usuário: página pública, sem exigir sessão — ao contrário do painel F1.11 (AD-012), que exige conta. Cobertura por município×camada não é dado de um lote específico, não carrega PII. |
| Busca/filtro por município na mesma página | Fora do MVP: a listagem completa (visão de estado) já resolve o problema declarado; filtro é um refinamento de UX, não uma nova capacidade de dado — pode virar P2/P3 futuro sem mudar a rota. |
| Mudar o contrato de `GET /cobertura?municipio=X` existente | A rota HTTP existente (F1.10, DOS-11/13) não muda; a agregação "todos os municípios" é uma rota nova e adicional (ex.: `GET /cobertura/estado`), não uma alteração da rota por-município já usada por F1.10. |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica silenciosamente indefinido.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Escopo de municípios listados | Só municípios com ≥1 lote ingerido (os que já aparecem em `cobertura`) | Decisão do usuário; evita depender de TD-001 (malha municipal) ainda aberto | y |
| Regra de "base obsoleta" (DOS-29) | Nenhum limiar automático nesta fatia; só exibe a data crua de extração | Decisão do usuário, reafirmada após achar `LIMIAR_DIAS_DESATUALIZADA=90` (`montagem.py:33`, já usado por DOS-13 no dossiê individual): decisão consciente de manter a página de cobertura só com data crua por ora, mesmo sabendo que o dossiê individual já aplica esse limiar — os dois lugares tratam "idade do dado" de forma diferente até uma revisão futura decidir unificar. | y — reafirmado |
| Autenticação da página | Pública, sem login/sessão | Decisão do usuário; cobertura município×camada não é PII nem dado de um lote específico | y |
| Ordenação da listagem | Municípios em ordem alfabética; camadas na ordem fixa de `Camada` (enum de domínio) | Não discutido explicitamente — comportamento determinístico mais simples para uma página de leitura; sem impacto de negócio | n — assumido, revisitar se o usuário pedir ordenação por "mais desatualizado primeiro" |
| Formato de resposta da rota nova | JSON puro (agregação `GET /cobertura/estado` ou similar), renderizado por HTML+JS estático novo em `app/` — nunca HTML server-side no FastAPI | Correção de leitura do código real: AD-012 já fixou "front vanilla estático" como o padrão do projeto — `app/index.html`+`mapa.js`, `app/login.html` e `dossie.js` (view model puro, sem tocar DOM) todos seguem API JSON + JS estático; nenhuma rota do `api/app.py` hoje devolve HTML. Uma rota nova devolvendo HTML quebraria esse padrão sem motivo. | y — corrigido nesta revisão, ver nota abaixo |
| Camada sem nenhuma linha em `cobertura` para um município listado | Célula mostra "sem dado" explícito (equivalente a `tem_dado=false`), nunca omite a camada da grade | Mantém a mesma honestidade de DOS-11 (Fatia 4) — nunca esconder ausência de cobertura | y |

**Open questions:** nenhuma — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Visão de cobertura do estado ⭐ MVP

**User Story**: Como visitante (sem conta), quero ver, numa única página pública, quais
municípios já têm dado ingerido e em quais camadas, para avaliar se o produto cobre a área que me
interessa antes de criar conta.

**Why P1**: É o objetivo inteiro da feature (roadmap F1.12) — sem isso não há página.

**Acceptance Criteria**:

1. WHEN um visitante sem sessão faz `GET` na rota de agregação de cobertura THEN o sistema SHALL
   responder 200 com JSON (sem exigir cookie/header de autenticação) — mesmo padrão de `GET
   /dossie`/`/cobertura` (AD-012: API JSON pura, front vanilla estático consome).
2. WHEN a rota responde THEN o sistema SHALL incluir todo município presente em `cobertura`
   (≥1 linha), em ordem alfabética pelo código do município.
3. WHEN um município aparece na resposta THEN o sistema SHALL incluir, para cada `Camada` do
   domínio, se `tem_dado` é verdadeiro ou falso para aquele município.
4. WHEN uma célula município×camada tem `tem_dado=true` THEN a página estática (`app/`) SHALL
   exibir a `data_extracao` em formato legível (ex.: `DD/MM/AAAA`), nunca a string ISO crua.
5. WHEN uma célula município×camada tem `tem_dado=false` (ou não existe linha em `cobertura` para
   aquele par) THEN a página estática SHALL exibir "sem dado" de forma explícita, nunca omitir a
   célula.
6. WHEN a rota responde com zero municípios (base vazia) THEN o sistema SHALL responder 200 com uma
   lista vazia, e a página estática SHALL exibir uma mensagem explícita de "nenhuma cobertura
   ainda", nunca uma tabela vazia sem contexto ou um erro.

**Independent Test**: com uma versão publicada contendo 2 municípios × 2 camadas (1 `tem_dado=true`
com data, 1 `tem_dado=false`), chamar a rota nova e conferir o JSON; abrir a página estática e
conferir via parse do DOM que as 4 células aparecem corretas.

---

## Edge Cases

- WHEN a mesma camada tem `tem_dado=true` em alguns municípios e `false` em outros (caso real hoje:
  APP/Reserva Legal com dado, UC/INEA ainda não ingeridas) THEN o sistema SHALL mostrar cada
  município de forma independente, sem inferir estado de um município a partir de outro.
- WHEN o banco está indisponível ao carregar a página THEN o sistema SHALL responder um erro 5xx
  padrão (mesmo padrão de falha das demais rotas HTTP do projeto), nunca uma página HTML parcial
  silenciosa.
- WHEN uma camada nunca apareceu em nenhum município (0% ingerida, ex.: `corpo_dagua` antes da
  Fatia correspondente) THEN o sistema SHALL ainda listar essa coluna/camada com "sem dado" em
  todas as linhas, nunca omitir a coluna inteira da grade.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| COBPUB-01 | P1: Visão de cobertura do estado | Execute | ✅ Verified |
| COBPUB-02 | P1: Visão de cobertura do estado | Execute | ✅ Verified |
| COBPUB-03 | P1: Visão de cobertura do estado | Execute | ✅ Verified |
| COBPUB-04 | P1: Visão de cobertura do estado | Execute | ✅ Verified |
| COBPUB-05 | P1: Visão de cobertura do estado | Execute | ✅ Verified |
| COBPUB-06 | P1: Visão de cobertura do estado | Execute | ✅ Verified |

**ID format:** `COBPUB-NN` — feature nova de superfície (página pública), distinta de `DOS-NN`
(motor do dossiê) e `PAINEL-NN` (painel autenticado, F1.11); DOS-29 permanece a referência da spec
original para o requisito de "aviso de base obsoleta" (parcialmente fechado aqui — ver Out of
Scope).

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 6 total, 6 mapped to tasks, 0 unmapped — Verifier PASS (`validation.md`, 2026-09-23):
6/6 ACs com asserção ancorada na spec, gate 220 Python + 9 JS (0 falhas), sensor 3/3 mutantes
mortos.

---

## Success Criteria

Como saberemos que a feature teve sucesso:

- [x] Um visitante sem conta consegue ver, em uma única página, todos os municípios com lote
      ingerido e o estado de cada camada, sem precisar conhecer código de município ou ler JSON.
      Verificado no navegador via Playwright (tabela 3 municípios × 8 camadas, sem sessão).
- [x] Nenhuma célula município×camada é omitida silenciosamente — `tem_dado=false` é sempre visível
      como tal. Verificado por teste (`test_dto.py`) e visualmente ("sem dado" em toda camada não
      ingerida, incl. `lote_rural`/`lote_urbano`).
- [x] Zero alteração em `dossie/`, `geometria/`, `ingestao/cobertura.py` — a feature só lê e projeta.
      Confirmado pelo Verifier no diff `cab4883^..cce3d6d`.
