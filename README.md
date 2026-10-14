# Terramétrica

**Um clique no mapa, o dossiê do lote.** Área, restrições ambientais e de risco já cruzadas,
com fonte e data em cada número. Estado do Rio de Janeiro.

---

## O problema em uma frase

O dado sobre a terra é público e está espalhado por oito portais que não se falam; o cruzamento
— que é onde mora o valor — ninguém entrega pronto.

## Estado atual

**v0.3 (MVP visível) em andamento.** O produto roda ponta a ponta: o usuário clica no mapa do RJ e
recebe o dossiê do lote, com o contorno do lote desenhado no mapa. Ver [arquitetura](docs/arquitetura.md)
e [domínio](docs/dominio.md) para os diagramas, e [`.specs/STATE.md`](.specs/STATE.md) para o log de
decisões e o handoff.

| Peça | Estado |
| --- | --- |
| Núcleo de domínio e montagem do dossiê | ✅ F1.1 |
| Ingestão: SIGEF, CAR, UC, lotes de Niterói, limite do RJ e malha municipal (92 municípios) | ✅ F1.2–F1.5, F1.9, F1.8 |
| API HTTP (FastAPI): `/dossie`, `/cobertura`, `/cobertura/estado`, `/mapa/contorno`, `/auth/*`, `/saude` | ✅ F1.10, F1.12, F1.13 |
| Painel web (`app/`): mapa MapLibre + OpenFreeMap, contorno do lote, link compartilhável, celular | ✅ F1.11, F1.13 |
| Página de cobertura pública (`app/cobertura.html`): 92 municípios pelo nome | ✅ F1.12 |
| Resolução de município por coordenada (fecha TD-001) | ✅ F1.8 |
| Deploy no Railway, front e API na mesma origem (AD-013) | Serviço no ar. A base real ainda não foi restaurada — ver [RESTORE-E-GO-LIVE](docs/RESTORE-E-GO-LIVE.md) |
| Gate jurídico | Regras e serviço prontos, sem adapter de persistência |

Testes: Python (`pytest tests/unit tests/integration`), JS (`node --test app/tests/*.test.mjs`) e
navegador (`pytest tests/navegador -m navegador`, ver [DEV-SETUP](docs/DEV-SETUP.md)).

> ✅ **As fontes foram confirmadas por acesso real.** SIGEF (14.664 feições), CAR (69.105
> feições) e SIGeo Niterói (82.199 feições) foram baixados e medidos numa máquina local — o
> bloqueio de HTTPS para `.gov.br` era do ambiente de desenvolvimento remoto, não da rede em
> geral. Sobreposição SIGEF × CAR medida de verdade: só 35,1% dos imóveis CAR sobrepõem algum
> SIGEF certificado, confirmando empiricamente a AD-003. Detalhe em
> [`fontes-de-dados-rj.md`](docs/research/fontes-de-dados-rj.md) e no handoff de `.specs/STATE.md`.

**O que ainda não existe:** as camadas de inundação, deslizamento e corpo d'água (fontes do INEA
ainda sem verificação), a exportação em PDF, a divergência SIGEF × CAR e a persistência real do gate
jurídico. Ver o [roadmap](docs/produto/roadmap.md).

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

**Recarregar a base com a malha municipal e restaurá-la no Railway.** A base atual não tem a camada
`municipio`. Com ela, o clique sem lote devolve o nome do município e a página de cobertura lista os
92 municípios. Rode `python -m terrametrica.ingestao.carregar_base` com uma versão nova e siga o
[RESTORE-E-GO-LIVE](docs/RESTORE-E-GO-LIVE.md). Depois, abra as camadas do INEA (F1.6 e F1.7) quando
a fonte for verificada.
