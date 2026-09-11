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

### L-002 — AC de UI com efeito de navegação (PAINEL-06/12: sessão ausente/expira → redirect ao login) fica só com prova server-side (401) se o redirect vive em JS classificado manual-only. Registrar a verificação manual (nota/screenshot no validation) como evidência da metade-UI do AC.
- signal: `ac_gap` · recurrence: 1 feature(s) · harmful: 0
- features: painel-web-conta
- evidence: Verifier F1.11 (validation.md)
- last seen: 2026-09-11T18:20:36Z

### L-003 — auth/regras.py::token_valido é chamado só pelos fakes; o enforcement real de expiração/uso-único é a query _CONSUMIR_TOKEN (WHERE usado_em IS NULL AND expira_em > agora). Mutante no operador < de token_valido sobrevive por ser dead-code no runtime. Se wirar token_valido no fluxo, adicionar teste de boundary direto.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · harmful: 0
- features: painel-web-conta
- evidence: Verifier F1.11 (sensor mutant A1)
- last seen: 2026-09-11T18:20:36Z

## Quarantined (failed when applied — ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
