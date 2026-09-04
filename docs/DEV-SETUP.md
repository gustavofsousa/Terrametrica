# Setup de desenvolvimento

## Skill de especificação (tlc-spec-driven)

O projeto usa a skill `tlc-spec-driven` (Tech Lead's Club, CC-BY-4.0) como processo de
especificação e implementação. Ela não é versionada aqui — é código de terceiros e ocupa
236 KB. Instale localmente:

```bash
git clone --depth 1 https://github.com/tech-leads-club/agent-skills.git /tmp/agent-skills
mkdir -p .claude/skills
cp -r "/tmp/agent-skills/packages/skills-catalog/skills/(development)/tlc-spec-driven" \
      .claude/skills/tlc-spec-driven
```

### Gates determinísticos

Rode antes de fechar cada fase. Saída diferente de zero significa parar e corrigir.

```bash
# Antes de confirmar um spec
python3 .claude/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/<feature>/spec.md

# Antes de apresentar tasks para aprovação
python3 .claude/skills/tlc-spec-driven/scripts/validate_tasks.py .specs/features/<feature>/tasks.md

# Em cada commit
python3 .claude/skills/tlc-spec-driven/scripts/check_commit.py --message "<msg>"

# Antes de declarar uma feature pronta
python3 .claude/skills/tlc-spec-driven/scripts/validate_state.py <feature>
```

Requer Python 3 (sem dependências externas).

## Ambiente Python

Requer Python 3.12. Crie o `.venv` e instale o projeto em modo editável com os extras de dev:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Banco de dados (Docker + PostGIS)

A persistência (Fatia 2 em diante) requer PostgreSQL com PostGIS. Pré-requisito: **Docker**
instalado e rodando (`docker info` deve retornar sem erro).

Para dev manual (subir um Postgres persistente local na porta 5433, fora dos testes):

```bash
docker compose up -d
```

Os testes de integração (`tests/integration/`) **não** usam o `docker-compose.yml` acima — eles
sobem um container PostGIS efêmero por módulo de teste via `testcontainers`, que gerencia sua
própria porta automaticamente. Antes de rodar a suíte de integração, confirme que o Docker está
disponível:

```bash
docker info
pytest tests/unit tests/integration -q
```

Se o Docker não estiver rodando, os testes de integração falham com uma mensagem clara em vez de
um erro genérico de conexão.

## Restrição conhecida do ambiente remoto

O ambiente de execução remota deste projeto bloqueia HTTPS para hosts `.gov.br` por política
de egress (403 no CONNECT) e não tem credencial de escrita no git — a publicação acontece pela
API do GitHub. A ingestão de dados públicos precisa rodar em ambiente com egress liberado.
Ver a checklist em `docs/research/fontes-de-dados-rj.md`.
