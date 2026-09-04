# Terramétrica

**Um clique no mapa, o dossiê do lote.** Área, restrições ambientais e de risco já cruzadas,
com fonte e data em cada número. Estado do Rio de Janeiro.

---

## O problema em uma frase

O dado sobre a terra é público e está espalhado por oito portais que não se falam; o cruzamento
— que é onde mora o valor — ninguém entrega pronto.

## Estado atual

**Fase 0 fechada, Fatia 2 fechada.** Há código real: núcleo de domínio, montagem do dossiê, gate
jurídico (regras) e um walking skeleton de ingestão (SIGEF + limite do RJ) publicando num
PostGIS real. Ver [arquitetura](docs/arquitetura.md) e [domínio](docs/dominio.md) para o estado
atual em diagramas, e [`.specs/STATE.md`](.specs/STATE.md) para o log de decisões e o handoff
completo.

| Fase (tlc-spec-driven) | Estado |
| --- | --- |
| Pesquisa de fontes | Feita e **verificada por acesso real** (2026-09-03) |
| Specify | Concluída (`dossie-lote-rj`, `gate-juridico-p2`) |
| Design | Concluído |
| Tasks | Concluídas para Fatia 1, Fatia 2 e gate jurídico P2 |
| Execute | Fatia 1 e Fatia 2 **DONE**, Verifier PASS; gate jurídico (regras + serviço) DONE, sem adapter real ainda |

> ✅ **As fontes foram confirmadas por acesso real.** SIGEF (14.664 feições), CAR (69.105
> feições) e SIGeo Niterói (82.199 feições) foram baixados e medidos numa máquina local — o
> bloqueio de HTTPS para `.gov.br` era do ambiente de desenvolvimento remoto, não da rede em
> geral. Sobreposição SIGEF × CAR medida de verdade: só 35,1% dos imóveis CAR sobrepõem algum
> SIGEF certificado, confirmando empiricamente a AD-003. Detalhe em
> [`fontes-de-dados-rj.md`](docs/research/fontes-de-dados-rj.md) e no handoff de `.specs/STATE.md`.

**O que ainda não existe:** camada HTTP/API (FastAPI está decidido em AD-007, zero código),
ingestão de CAR e da camada urbana de Niterói, malha municipal do IBGE, e persistência real do
gate jurídico. Nada disso bloqueia o próximo passo — ver [arquitetura](docs/arquitetura.md#o-que-ainda-não-existe-para-não-ler-o-diagrama-como-se-existisse).

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
| [Arquitetura](docs/arquitetura.md) | Estado atual dos componentes, pipeline de ingestão, árvore de decisão do dossiê e estratégia de testes |
| [Modelo de domínio](docs/dominio.md) | Vocabulário ubíquo em diagramas de classe: value objects, uniões fechadas, gate jurídico |
| [Visão geral (Excalidraw)](docs/visao-geral.excalidraw) | One-pager de onboarding — produto, domínio, arquitetura e status num só canvas (abrir em excalidraw.com) |
| [Fontes de dados](docs/research/fontes-de-dados-rj.md) | Bases federais, estaduais e municipais, com nível de confiança e checklist |
| [Catálogo de fontes e APIs](docs/research/catalogo-fontes-e-apis.md) | Geosserviços, APIs públicas, forma de acesso e ordem de ataque |
| [Stack open source](docs/research/stack-open-source.md) | O que já existe pronto por camada, e o que não usar |
| [Spec do MVP](.specs/features/dossie-lote-rj/spec.md) | 30 requisitos rastreáveis em EARS |
| [Contexto da feature](.specs/features/dossie-lote-rj/context.md) | Decisões tomadas na discussão, e o que ficou a critério do agente |
| [Decisões do projeto](.specs/STATE.md) | Log de decisões arquiteturais (AD-NNN) |
| [Setup de desenvolvimento](docs/DEV-SETUP.md) | Ambiente Python, Docker/PostGIS, como rodar e testar localmente, lint e type-check |

## Processo

O projeto usa [tlc-spec-driven](https://github.com/tech-leads-club/agent-skills) — quatro fases
(Specify, Design, Tasks, Execute) com gates determinísticos em Python. Nenhuma fase fecha sem o
gate passar. Instalação em [DEV-SETUP.md](docs/DEV-SETUP.md).

```bash
python3 .claude/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/dossie-lote-rj/spec.md
```

## Próximo passo

**Fatia 3**, em ordem de valor: (a) CAR — segunda geometria do lote rural (AD-003), reusando o
padrão de `ingestao/sigef.py`; (b) camada urbana de Niterói via SIGeo, já confirmada acessível em
Fase 0; (c) malha municipal do IBGE, fechando o débito técnico TD-001. Sem bloqueio técnico
conhecido para nenhuma das três — ver o handoff completo em [`.specs/STATE.md`](.specs/STATE.md).
