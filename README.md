# Terramétrica

**Um clique no mapa, o dossiê do lote.** Área, restrições ambientais e de risco já cruzadas,
com fonte e data em cada número. Estado do Rio de Janeiro.

---

## O problema em uma frase

O dado sobre a terra é público e está espalhado por oito portais que não se falam; o cruzamento
— que é onde mora o valor — ninguém entrega pronto.

## Estado atual

**Fase Specify concluída.** Não há código ainda. O que existe é a especificação, a pesquisa de
fontes e o registro de decisões.

| Fase | Estado |
| --- | --- |
| Pesquisa de fontes | Feita, **não verificada por acesso real** — ver aviso abaixo |
| Specify | Concluída, gate determinístico limpo |
| Design | Não iniciada |
| Tasks | Não iniciada |
| Execute | Não iniciada |

> ⚠️ **As fontes ainda não foram confirmadas.** O ambiente de desenvolvimento remoto bloqueia
> HTTPS para hosts `.gov.br` (403 na política de egress), então nenhum endpoint foi testado por
> requisição real. Cada fonte carrega nível de confiança explícito e há uma checklist de
> verificação que precisa rodar antes de qualquer código de ingestão.

## Escopo do MVP

| Camada | Cobertura | Fonte |
| --- | --- | --- |
| Rural | **Todo o estado do RJ** | SIGEF/INCRA (certificado) + CAR (declarado) |
| Urbana | **Município de Niterói** | SIGeo / ArcGIS Hub (WFS · WMS · GeoJSON) |
| Restrições | Todo o estado | INEA, ICMBio, ANA |
| Proprietário | **Fora desta versão** | — ver [riscos](docs/produto/riscos.md#1-jurídico--a-camada-de-proprietário-alto) |

## Três decisões que definem o produto

1. **SIGEF é o limite certificado; CAR é declaração do proprietário.** Onde discordam, mostramos
   os dois com a diferença quantificada. Nunca reconciliamos em silêncio.
2. **Nenhum dado pessoal de proprietário é ingerido ou armazenado.** A publicidade registral
   sustenta consulta por certidão, não agregação de base. O gate de autorização nasce vazio para
   ligar a camada depois, se houver caminho jurídico defensável.
3. **Todo campo carrega fonte e data.** Onde não há dado, o sistema declara ausência de cobertura
   em vez de devolver vazio ambíguo.

## Documentação

### Produto
| Documento | Para quê |
| --- | --- |
| [Visão](docs/produto/visao.md) | Problema, tese, personas, o que o produto não é |
| [Anatomia do dossiê](docs/produto/dossie.md) | O que o dossiê mostra, campo a campo, e de onde vem |
| [Roadmap](docs/produto/roadmap.md) | Quatro fases, da verificação de fontes à camada registral |
| [Riscos](docs/produto/riscos.md) | Cinco riscos e a mitigação embutida em cada um |
| [Glossário](docs/produto/glossario.md) | SIGEF, CAR, APP, testada, fé pública — para quem não é da área |

### Protótipo
| O quê | Para quê |
| --- | --- |
| [Dossiê no Mapa](prototipos/mapa-dossie/) | Mapa arrastável em que clicar num polígono abre o dossiê. Interação e layout reais, polígonos sintéticos |

### Técnico
| Documento | Para quê |
| --- | --- |
| [Fontes de dados](docs/research/fontes-de-dados-rj.md) | Bases federais, estaduais e municipais, com nível de confiança e checklist |
| [Catálogo de fontes e APIs](docs/research/catalogo-fontes-e-apis.md) | Geosserviços, APIs públicas, forma de acesso e ordem de ataque |
| [Stack open source](docs/research/stack-open-source.md) | O que já existe pronto por camada, e o que não usar |
| [Spec do MVP](.specs/features/dossie-lote-rj/spec.md) | 30 requisitos rastreáveis em EARS |
| [Contexto da feature](.specs/features/dossie-lote-rj/context.md) | Decisões tomadas na discussão, e o que ficou a critério do agente |
| [Decisões do projeto](.specs/STATE.md) | Log de decisões arquiteturais (AD-NNN) |
| [Setup de desenvolvimento](docs/DEV-SETUP.md) | Skill de especificação e gates determinísticos |

## Processo

O projeto usa [tlc-spec-driven](https://github.com/tech-leads-club/agent-skills) — quatro fases
(Specify, Design, Tasks, Execute) com gates determinísticos em Python. Nenhuma fase fecha sem o
gate passar. Instalação em [DEV-SETUP.md](docs/DEV-SETUP.md).

```bash
python3 .claude/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/dossie-lote-rj/spec.md
```

## Próximo passo

Fase 0 do [roadmap](docs/produto/roadmap.md#fase-0--verificar-as-fontes-pré-requisito-sem-entrega-de-produto):
verificar as fontes em ambiente com egress liberado. Um "não" ali muda o produto, não o cronograma.
