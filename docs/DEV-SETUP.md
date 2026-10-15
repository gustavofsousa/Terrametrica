# Setup de desenvolvimento

## Skill de especificação (tlc-spec-driven)

O projeto usa a skill `tlc-spec-driven` (Tech Lead's Club, CC-BY-4.0) como processo de especificação
e implementação. O repo não versiona a skill: é código de terceiros e ocupa 236 KB. Instale-a
localmente:

```bash
git clone --depth 1 https://github.com/tech-leads-club/agent-skills.git /tmp/agent-skills
mkdir -p .claude/skills
cp -r "/tmp/agent-skills/packages/skills-catalog/skills/(development)/tlc-spec-driven" \
      .claude/skills/tlc-spec-driven
```

### Gates determinísticos

Rode estes gates antes de fechar cada fase. Se a saída for diferente de zero, pare e corrija.

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

O projeto requer Python 3.12. Crie o `.venv` e instale o projeto em modo editável com os extras de
dev:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Banco de dados (Docker + PostGIS)

A persistência (Fatia 2 em diante) requer PostgreSQL com PostGIS. Pré-requisito: o **Docker**
instalado e rodando (`docker info` retorna sem erro).

Para dev manual, suba um Postgres persistente local na porta 5433, fora dos testes:

```bash
docker compose up -d
```

O comando sobe `postgis/postgis:16-3.4` com usuário/senha/banco `terrametrica`, em
`postgresql://terrametrica:terrametrica@localhost:5433/terrametrica`.

Os testes de integração (`tests/integration/`) **não** usam o `docker-compose.yml` acima. O
`testcontainers` sobe um container PostGIS efêmero por módulo de teste. Ele gerencia a própria porta e
aplica as migrações automaticamente. O `docker-compose.yml` serve só para inspecionar dado à mão
(`psql`, DBeaver, QGIS) fora do ciclo de teste.

### Aplicar as migrações manualmente no banco do `docker-compose.yml`

Ainda não há CLI para isso. Hoje só os testes chamam `aplicar_migracoes` (`persistencia/migrar.py`).
Para rodar contra o Postgres do `docker-compose.yml` e inspecionar dado à mão:

```bash
export TERRAMETRICA_DB_URL="postgresql://terrametrica:terrametrica@localhost:5433/terrametrica"
.venv/bin/python -c "
from terrametrica.persistencia.conexao import abrir_conexao
from terrametrica.persistencia.migrar import aplicar_migracoes
conexao = abrir_conexao()
aplicar_migracoes(conexao)
conexao.commit()
"
```

## Rodando e testando localmente

A suíte de testes exercita `montar_dossie` e o pipeline de ingestão diretamente. A ingestão roda por
chamada de função Python. O padrão completo está no snippet acima e em
`tests/integration/test_dossie_e2e.py`: `ingerir_limite_rj` → `ingerir_sigef` → `publicar_versao` →
`montar_dossie`. O README e `python -m terrametrica.ingestao.carregar_base` cobrem a carga da base.

```bash
# só testes unitários — sem I/O, sem Docker, roda em segundos
pytest tests/unit -q

# suíte completa — exige Docker rodando (testcontainers sobe PostGIS efêmero por módulo)
docker info
pytest tests/unit tests/integration -q
```

Se o Docker não estiver rodando, os testes de integração falham com uma mensagem clara, não com um
erro genérico de conexão.

### Testes de navegador (AD-017)

Os testes de `tests/navegador/` abrem o painel num Chromium real com `pytest-playwright`. Cada
sessão sobe um PostGIS efêmero, semeia fixtures e serve a app numa porta livre. Eles ficam fora da
suíte padrão: o marcador `navegador` os deixa de fora, e `pytest tests/unit tests/integration` não
os coleta. Peça-os de forma explícita.

Na primeira vez, baixe o navegador (cerca de 150 MB):

```bash
.venv/bin/playwright install chromium
```

Depois rode:

```bash
.venv/bin/pytest tests/navegador -m navegador -q
```

NOTE: O MapLibre vem do `unpkg.com`. Essa é a única saída de rede que a suíte permite. As fontes e o
estilo do OpenFreeMap são interceptados.

### Lint e type-check

Rode antes de cada commit. É o mesmo padrão dos gates do `tlc-spec-driven`, mas para o código:

```bash
.venv/bin/ruff check src tests
.venv/bin/mypy       # usa [tool.mypy] do pyproject.toml — checa só src/, strict
```

## Restrição conhecida do ambiente remoto

O ambiente de execução remota deste projeto bloqueia HTTPS para hosts `.gov.br` por política de
egress (403 no CONNECT). Ele também não tem credencial de escrita no git: a publicação passa pela API
do GitHub. Por isso a ingestão de dados públicos deve rodar num ambiente com egress liberado. A
checklist está em `docs/research/fontes-de-dados-rj.md`.
