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

## Restrição conhecida do ambiente remoto

O ambiente de execução remota deste projeto bloqueia HTTPS para hosts `.gov.br` por política
de egress (403 no CONNECT) e não tem credencial de escrita no git — a publicação acontece pela
API do GitHub. A ingestão de dados públicos precisa rodar em ambiente com egress liberado.
Ver a checklist em `docs/research/fontes-de-dados-rj.md`.
