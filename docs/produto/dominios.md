<!-- CLASSIFICAÇÃO: DOMÍNIOS DE PROJETO · referência canônica dos bounded contexts. Espelha src/terrametrica/ (design.md: "vocabulário do glossario.md é o dos módulos e tabelas"). -->

# Domínios

> Os domínios **são os módulos** de [`src/terrametrica/`](../../src/terrametrica/). Não há divergência
> entre o nome no código e o nome aqui — é uma decisão de design (`.specs/features/dossie-lote-rj/design.md`,
> "Perspective Sweep → Domain"): o vocabulário do [glossario.md](glossario.md) é o dos módulos e tabelas.
> Este arquivo é a fonte que o [roadmap.md](roadmap.md) referencia na coluna **Domínio**.

Arquitetura hexagonal em todos os domínios com I/O: `regras.py` (funções puras) + `portas.py`
(contratos `Protocol`) + `servico.py` (orquestra regras+ports) + `adaptadores.py` (implementação
real). O teste injeta *fakes* nos ports; o núcleo nunca importa I/O.

## Tiers

Classificação DDD-lite (ver skill `domain-first-structure`): **Core** carrega a tese do produto,
**Support** viabiliza, **Generic** é infra substituível, **Cross-cutting** (⟂) corta vários.

| Domínio | Pasta | Tier | Responsabilidade (uma frase) |
|---------|-------|------|-------------------------------|
| **dominio** | `dominio/` | Core | Value objects e tipos-resultado — hub do vocabulário ubíquo; sem I/O. Ports e montagem importam daqui, nunca o contrário. |
| **dossie** | `dossie/` | Core | Da coordenada clicada ao read-model montado. Árvore de decisão explícita (fora do RJ / sem lote / sobreposição / lote resolvido). |
| **geometria** | `geometria/` | Core | Regras numéricas que definem o produto sobre áreas já calculadas — toque marginal <1% (DOS-08), divergência >5% (AD-003). Funções puras. |
| **ingestao** | `ingestao/` | Core | Baixar, validar, reprojetar e materializar cada fonte numa versão de base publicável. Guarda ≥90% + swap atômico (DOS-25/28). Entrypoint separado (batch, assíncrono). |
| **autorizacao** | `autorizacao/` | Core | Gate jurídico do acesso registral (P2): papéis, decisão Permitido/Negado, log imutável síncrono (GATE-05). **Sem nenhum dado pessoal.** |
| **cobertura** | `ingestao/cobertura.py` | Support | Estado real por município × camada (tem dado? de que data?). Alimenta a página pública e o "sem cobertura aqui" do dossiê (DOS-11/13). |
| **auth** | `auth/` | Support | Autenticação e sessão via magic link (Fatia 7). Anti-enumeração: o fluxo é idêntico para e-mail conhecido e desconhecido. |
| **api** | `api/` | Support | Entrypoint FastAPI **fino**: resolve versão publicada, injeta identidade opaca, aplica cota, chama a montagem. Nenhuma regra de negócio mora aqui. |
| **app** | `app/` (front-end) | Support | Painel MapLibre: mapa arrastável + clique→dossiê + login. HTML/JS estático que consome a API. |
| **persistencia** | `persistencia/` | Generic | Adapters PostGIS dos ports (`RepositorioLotes`, limite do estado), conexão e migrações. Área/perímetro via `ST_Area`/`ST_Perimeter` sobre `geography`. |
| **registral** | *(a nascer)* | Core ⏭️ | Ligar o dado do registro de imóveis ao dossiê, sob o gate. **Condicional** — só existe se F3.1 (ONR) confirmar caminho jurídico. Ver [riscos.md](riscos.md). |

## Notas de fronteira

- **`auth` ≠ `autorizacao`.** `auth` responde "quem é você" (sessão, magic link). `autorizacao` responde
  "você pode acessar o dado registral" (gate jurídico P2). Módulos separados de propósito.
- **`cobertura` e `proveniencia`** foram desenhados como domínios próprios em `design.md`, mas na fatia
  atual `cobertura` vive dentro de `ingestao/cobertura.py` e a proveniência é coluna nas tabelas (AD-005),
  não módulo. Ganham pasta própria quando a página pública (F1.12) crescer.
- **`registral` ainda não é pasta** — é fronteira reservada vazia (design.md: "o modelo de dados reserva
  o limite"). Nasce só se v0.5 for confirmada.
- **UF é dimensão explícita** em todo o modelo mesmo cobrindo só o RJ (AD-001) — federar depois é ingestão,
  não redesenho.

## Como isto se relaciona com o roadmap

O [roadmap.md](roadmap.md) tagueia cada **feature** com o domínio onde ela mora. Uma feature nova de
restrição (CAR, UC, INEA, urbana) é sempre `ingestao` (materializa) + `geometria` (regra) + `dossie`
(exibe) — não um domínio "restricoes" isolado. Painel, exportação e deploy são `app`/`api`.
