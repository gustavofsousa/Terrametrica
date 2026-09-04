# LESSONS — auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation — do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 — Ao materializar interseção espacial em SQL (ST_Intersection/ST_Area), teste explicitamente o toque-de-borda: dois polígonos que só compartilham fronteira têm ST_Intersects=true mas área 0, e o filtro que descarta esse caso não é coberto por um teste de 'sem sobreposição' (que usa polígonos disjuntos, barrados antes pelo ST_Intersects).
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `ingestao/spatial-join` · harmful: 0
- features: dossie-lote-rj
- evidence: M2: intersecoes.py area_m2 > 0 (ingestao/spatial-join)
- last seen: 2026-09-04T15:24:48Z

## Quarantined (failed when applied — ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
