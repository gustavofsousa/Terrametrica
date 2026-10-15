# AGENTS.md — Terramétrica

> Repo constitution. Read it before you touch this repo. The global `AGENTS.md` still applies; this
> file adds only what is specific to this project.

## Constitution

```yaml
type: semente             # structure the lot dossier before going live; named by the owner on 2026-10-14
open-source: false
rigor:                      # off | designed | enforced; types, defaults and events: _hq/ia/catalogs/project-types.md
  auth: designed
  privacy: designed
  tests: enforced
  ci: designed
  observability: designed
  scale: designed
```

- **Promotion is an event the owner names.** Never change `type` or raise an axis on your own.
  Types, defaults and events: `_hq/ia/catalogs/project-types.md`.
