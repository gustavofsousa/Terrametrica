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
