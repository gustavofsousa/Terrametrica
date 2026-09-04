# Tech Debt Ledger

Tracked technical debt. Recorded = exists (AGENTS.md: no entry, no debt).
Format: `TD-NNN` · Status: `open | in-progress | resolved | wontfix`.

---

## TD-001 — `RepositorioLotesPostGIS.municipio_em` sem malha municipal

**Status:** open
**Opened:** 2026-09-03
**Origin:** Fatia 2 (`.specs/features/dossie-lote-rj/tasks.md`, T9) implementa o adapter real do
Protocol `RepositorioLotes` (`dossie/portas.py`). O Protocol tem 5 métodos; a task T9, como
originalmente escrita, listou só 4 no "Done when" e esqueceu `municipio_em(coord, versao) -> str`
— usado por `dossie/montagem.py:61` no ramo "sem lote no ponto" (DOS-04, `SemLote`). Resolver a
coordenada pra um município exige a malha municipal do IBGE (polígonos por município), que não faz
parte do escopo desta fatia (só SIGEF — ver `design.md`, "Fatia 2 — Escopo desta rodada"). Buscar
isso ao vivo por request (API de Malhas do IBGE) violaria AD-004 (fonte externa fora do caminho de
request).

**What to investigate / change:**
1. Ingerir a malha municipal do RJ (IBGE, via geobr `read_municipality` ou API de Malhas) numa
   fatia futura — provavelmente junto da camada urbana (SIGeo/Niterói) ou de CAR, já que ambos
   também precisam de contexto municipal.
2. Até lá, `RepositorioLotesPostGIS.municipio_em` levanta `NotImplementedError` com mensagem
   explícita, em vez de simular um retorno — falha alto e claro, não dado inventado.

**Impact if ignored:** O ramo `SemLote` do dossiê (clique sem lote mapeado, DOS-04) quebra em
produção contra o adapter real — funciona hoje só no fake em memória (T5). O caminho "achou lote"
(a prova fim-a-fim da Fatia 2, T14) não é afetado.

**Revisit trigger:** Quando a Fatia 3+ (CAR, camada urbana Niterói, ou qualquer trabalho que
precise de contexto municipal) começar — ingerir a malha municipal nesse momento, não isoladamente
só pra fechar este TD.

**Nota (2026-09-03, T12):** mesma causa raiz aparece na ingestão SIGEF — `lote_rural.municipios`
grava o código IBGE bruto do campo `municipio_` do shapefile (ex. `3304557`), não o nome do
município, porque não há malha código→nome disponível nesta fatia. Some junto quando a malha
municipal for ingerida.

---

## TD-002 — `cobertura` nunca é semeada por nenhuma ingestão

**Status:** resolved (Fatia 4, 2026-09-04 — commits `c36ac88`/`5243d54`)
**Opened:** 2026-09-04
**Origin:** Encontrado durante o design da Fatia 3 (`.specs/features/dossie-lote-rj/design.md`,
seção "Fatia 3"). A tabela `cobertura` (município × camada → tem dado / data de extração) existe
desde a migração `0001_fatia2_sigef.sql`, mas **nenhuma ingestão até agora a escreve** — nem
`ingerir_limite_rj`, nem `ingerir_sigef`, e a Fatia 3 (CAR como restrição) também não vai escrevê-la
(fora do escopo desta rodada, ver design.md). `montagem.py:_montar_do_lote` lê `cobertura_de` e
trata `registro is None` como "sem cobertura" (DOS-11) — então, hoje, **toda** camada não-lote de
**todo** dossiê aparece marcada "sem cobertura no município", mesmo quando o dado foi realmente
ingerido para o estado inteiro.

**What to investigate / change:**
1. Decidir onde a seed de `cobertura` deveria acontecer: por camada (cada `ingerir_*` grava sua
   própria cobertura por município) ou centralizado (um passo separado que varre o que foi
   publicado). A primeira opção é mais simples mas replica a decisão N vezes; a segunda precisa
   de uma lista de municípios do RJ (já existe: `docs/research/municipios-rj/`), independente da
   malha geométrica de TD-001.
2. Cobertura estadual (SIGEF, CAR-restrição) e cobertura municipal (Niterói/urbano) têm
   granularidade diferente — o design de seed precisa cobrir os dois casos, não só copiar o padrão
   de um pros dois.

**Impact if ignored:** Nenhum dossiê real mostra "camada disponível" para nada além do lote em si
— a proveniência funciona (DOS-10), mas a UX de "sem cobertura" (DOS-11) mente sistematicamente
sobre camadas que na verdade têm dado.

**Revisit trigger:** Antes de qualquer fatia que dependa de `cobertura_de` para uma decisão visível
ao usuário no P1 real (não só em teste) — o mais tardar quando o painel web (`web/`) for construído
e precisar renderizar esse estado de verdade.

**Resolução (Fatia 4, AD-009):** `ingestao/cobertura.py::semear_cobertura` deriva o produto
(município do lote × camada de restrição) de `lote_rural`/`restricao`/`proveniencia` num único
upsert idempotente, chamado antes de `publicar_versao` (mesma transação). Escolhida a opção
centralizada, mas **derivando os municípios do próprio `lote_rural`** em vez de uma lista externa —
o único caminho de dossiê que consulta `cobertura_de` hoje é o do lote achado, então não precisou da
malha municipal (TD-001 segue independente). Fica **um concern menor herdado**: `cobertura` não é
versionada e o passo só faz upsert, então um município que perca todos os lotes numa reingestão
mantém a linha antiga (staleness). Aceito no MVP; revisitar se/quando reingestão com perda de
cobertura municipal virar caso real (provavelmente junto da política de retenção de N versões do
AD-007).

---

## TD-003 — DOS-09 sem texto definido; AC#2 (UC) sem DOS confirmado

**Status:** open
**Opened:** 2026-09-04 (Fatia 5)
**Origin:** A Fatia 5 entrega o AC#2 de "P1: Restrições ambientais" (`spec.md` ~linha 106 —
"indicar se o lote intersecta unidade de conservação, informando nome e categoria"). Mas o mapa
AC→DOS não é resolúvel no repo: DOS-06 = sobreposição de lotes, DOS-07/08 = Verified na Fatia 3
(APP / marginal). Sobra **DOS-09** (`Pending`) como único slot de restrição sem dono — porém
**DOS-09 não tem definição textual em lugar nenhum das specs**, e o AC#3 (inundação/deslizamento)
também disputa esse slot. Verifier independente concordou que marcar DOS-09 Verified sem a fonte
seria chute (ver `validation.md`, Fatia 5).

**What to investigate / change:**
1. Recuperar o texto original de DOS-09 (e conferir se há um DOS separado para AC#2 vs AC#3).
2. Decidir explicitamente o mapa: AC#2 (UC) → qual DOS, AC#3 (inundação/deslizamento) → qual DOS.
3. Marcar o DOS de UC como `✅ Verified` (Fatia 5) na tabela de traceability quando confirmado.

**Impact if ignored:** A entrega de UC fica sem linha na traceability por DOS — rastreio
Requisito→Fatia incompleto, embora a entrega esteja provada por teste (e2e + unit) e por AD-010.

**Revisit trigger:** No próximo doc-sync das specs, ou ao ingerir a camada de inundação/
deslizamento (AC#3), que força resolver o mesmo mapa AC→DOS.
