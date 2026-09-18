# Roadmap

Cinco fases (0 a 4). Cada uma responde a uma pergunta de negócio, entrega valor sozinha e destrava
a seguinte. Datas são deliberadamente ausentes: as dependências externas (verificar fontes,
contatar o ONR) têm prazo que não controlamos.

## Como ler este documento

Três níveis, do estratégico ao executável (vocabulário em [glossario.md](glossario.md)):

- **Fase** — um arco estratégico que responde a uma pergunta de negócio. Não tem data, tem resposta.
- **Feature** — um incremento entregável de verdade (≈ uma issue). É a unidade que este roadmap
  conta por fase.
- **Fatia** — um corte vertical de uma feature grande demais para uma tacada só. As "Fatias 1–5"
  entregues até agora são fatias da Fase 1.

**A contagem de features por fase é a atual — pode crescer.** Regra que a Fatia 5 nos ensinou na
prática: **cada camada de restrição/urbana nova carrega um custo de "Fase 0" próprio** (achar o
endpoint real, medir schema/CRS/contagem antes de escrever código). Toda vez que uma fonte nova for
verificada, pode nascer feature nova numa fase. Portanto os totais abaixo são piso, não teto.

**Legenda de estado:**
✅ feito (Verifier PASS) · 🟡 parcial · ⬜ não começado · 🔒 bloqueado por dependência externa ·
⏭️ condicional (só existe se um "se" for confirmado)

## Panorama

| Fase | Pergunta que responde | Features (feito / total atual) | Estado |
| --- | --- | --- | --- |
| **0 — Verificar fontes** | As fontes geoespaciais existem e são usáveis de verdade? | 4 / 5 (reabre por fonte nova) | 🟡 em aberto por camada |
| **1 — MVP: o dossiê** | O cruzamento vale mais que o dado cru? | **6 / 12** | 🟡 em andamento |
| **2 — Fazer circular** | O dossiê vira artefato e a divergência vira produto? | 0 / 3 (1 parcial) | ⬜ não começada |
| **3 — Camada registral** | Existe caminho jurídico defensável p/ o dado registral? | 0 / 2 | ⏭️ condicional |
| **4 — Ampliação** | Escala em município, camada, estado e canal? | 0 / 5 | ⬜ futura |

---

## Fase 0 — Verificar as fontes (pré-requisito, sem entrega de produto)

Nada de ingestão antes de medir a fonte por acesso real. **Não é uma fase que "fecha" de vez:
reabre toda vez que uma camada nova entra no escopo.**

| # | Item de verificação | Estado | Evidência |
| --- | --- | --- | --- |
| 0.1 | SIGEF RJ — feições, CRS, validade | ✅ | 14.664 feições, EPSG:4674, 0 inválidas |
| 0.2 | CAR + sobreposição SIGEF×CAR | ✅ | 69.105 feições; só 35,1% sobrepõem SIGEF (confirma AD-003) |
| 0.3 | SIGeo Niterói expõe **lote** (não só quadra) + endpoint | ✅ | 82.199 feições, EPSG:31983, FeatureServer confirmado |
| 0.4 | UC (Unidade de Conservação) — fonte consolidada | ✅ | 455 feições MPRJ/CNUC, EPSG:4326 (Fatia 5) |
| 0.5 | INEA inundação / deslizamento / corpo d'água | ⬜ | **não verificada** — custo de Fase-0 por camada |

> A verificação do ONR (existe API registral para terceiros?) **não é item da Fase 0** — não é uma
> fonte geoespacial do dossiê, é a pergunta que decide se a Fase 3 existe. Passou a ser a feature
> **F3.1**.

**Contagem:** 4 feito / 5 (cresce a cada camada nova). Detalhe em
[`../research/fontes-de-dados-rj.md`](../research/fontes-de-dados-rj.md).
**Destrava:** todo o resto. Um "não" aqui muda o produto, não o cronograma.

---

## Fase 1 — MVP: o dossiê

**Entrega:** clicar no mapa e receber o dossiê, com restrições cruzadas e proveniência em cada
campo. **Corresponde às três histórias P1 do spec** (DOS-01 a DOS-13, mais DOS-25/26/28/29/30).
**Prova ou refuta:** a tese de que o cruzamento vale mais que o dado cru. Se ninguém voltar uma
segunda vez, o problema não era esse.

| # | Feature | O que entrega | Estado | Fatia / nota |
| --- | --- | --- | --- | --- |
| F1.1 | Núcleo de domínio | Árvore de decisão do dossiê a partir de um read-model (fora do RJ / sem lote / sobreposição / lote resolvido) | ✅ | Fatia 1 |
| F1.2 | Persistência + ingestão rural SIGEF | Schema PostGIS versionado, adapter real, limite RJ + SIGEF, publicação com guarda de 90% e swap atômico | ✅ | Fatia 2 |
| F1.3 | Restrição CAR (APP + Reserva Legal) | Cruza APP e Reserva Legal com o lote, materializado na ingestão | ✅ | Fatia 3 |
| F1.4 | Cobertura honesta | Semeia `cobertura`; uma camada ingerida deixa de aparecer falsamente "sem cobertura" (DOS-11) | ✅ | Fatia 4 |
| F1.5 | Restrição Unidade de Conservação | UC (parques/reservas/APAs, categoria SNUC) cruzada com o lote | ✅ | Fatia 5 |
| F1.6 | Restrição inundação + deslizamento (INEA) | Suscetibilidade a inundação/deslizamento com grau (DOS AC#3) | ⬜ | 🔒 fonte a verificar (0.5) |
| F1.7 | Restrição corpo d'água | Corpos d'água / faixas marginais como restrição | ⬜ | 🔒 fonte a verificar (0.5) |
| F1.8 | Malha municipal IBGE + resolução de município | Destrava o clique "sem lote" (DOS-04) e o nome de município; fecha TD-001 | ⬜ | precisa da malha IBGE |
| F1.9 | Camada urbana Niterói (SIGeo) | Lotes urbanos de Niterói + estender a cobertura ao caso municipal | ⬜ | fonte já verificada (0.3) |
| F1.10 | API HTTP (FastAPI) | Rotas `/dossie`, `/cobertura`, `/saude`; rate limit 100/h (DOS-27); identidade via header (AD-011); observabilidade (DOS-30) | ✅ | Fatia 6 |
| F1.11 | Painel web + conta autenticada | Mapa, clique→dossiê, conta obrigatória sem paywall | ⬜ | depende de F1.10 |
| F1.12 | Página de cobertura pública | Estado real por município × camada, com data e aviso de base obsoleta (DOS-29/30) | ⬜ | depende de F1.4 + F1.10 |

**Contagem:** 6 feito / 12 (piso — cada restrição nova é uma feature a mais). O motor do dossiê já
roda fim-a-fim sobre PostGIS real **e tem superfície HTTP (F1.10 ✅)**; **o que falta para um usuário
ver isso é o painel (F1.11) + a página de cobertura HTML (F1.12)**, mais as camadas que aumentam o
valor do cruzamento (F1.6–F1.9).

---

## Fase 2 — O que faz o dossiê circular

**Entrega:** o dossiê sai do painel e vira artefato; a divergência entre fontes vira produto; a
estrutura de autorização nasce vazia. **Corresponde às três histórias P2 do spec** (DOS-14 a
DOS-22, mais DOS-27).

| # | Feature | O que entrega | Estado | Nota |
| --- | --- | --- | --- | --- |
| F2.1 | Exportação em PDF | Dossiê carimbado com data, versão da base e ressalva de fé pública | ⬜ | |
| F2.2 | Divergência SIGEF × CAR (CAR papel P2) | Dois polígonos, diferença em ha e %, alerta acima de 5% — nunca reconcilia (AD-003) | ⬜ | a segunda geometria do imóvel |
| F2.3 | Gate jurídico (decisão de acesso) | Papéis, verificação de credencial, decisão Permitido/Negado, log imutável — **sem nenhum dado pessoal** | 🟡 | lógica **Verified** (GATE-01..06); falta adapter de persistência + auditoria real |

**Contagem:** 0 concluídas / 3 (F2.3 parcial). **Por que o gate vem antes do dado registral:**
construir autorização e auditoria depois significa reescrever o sistema; construir antes custa
pouco e transforma a Fase 3 em ligar uma chave.

---

## Fase 3 — A camada registral (condicional)

**A fase inteira é condicional: só avança se F3.1 confirmar um caminho jurídico defensável.**

| # | Feature | O que entrega | Estado | Nota |
| --- | --- | --- | --- | --- |
| F3.1 | Verificação do caminho registral (ONR) | Descobrir se existe API do ONR para terceiros e sob quais condições — decide SE a fase existe e QUAL desenho é viável | 🔒 | pendência humana (contato com o ONR) |
| F3.2 | Camada registral | Ligar o dado registral ao dossiê, sob o gate da Fase 2, num dos três desenhos abaixo | ⏭️ | escolha depende de F3.1 |

Desenhos possíveis de **F3.2**, em ordem decrescente de valor e de risco:

| Desenho | Como funciona | Depende de |
| --- | --- | --- |
| Consulta viva | O app consulta o registro no ato, sob identidade do usuário habilitado, exibe e registra em log. Sem cache do conteúdo pessoal. | Existir integração do ONR para terceiros |
| Deep link | O app leva o usuário ao pedido de certidão no portal oficial, já preenchido com o imóvel | Só o portal existir |
| Upload de certidão | O usuário anexa a certidão que ele mesmo obteve; o app extrai e cruza com o dossiê | Nada externo |

**Contagem:** 0 / 2 (⏭️ condicional). **O que nunca acontece, em nenhum desenho:** ingerir e servir
uma base agregada de "proprietário → imóveis". Ver [riscos.md](riscos.md).

---

## Fase 4 — Ampliação

Em ordem de custo crescente por unidade de valor. Todas ⬜.

| # | Feature | O que entrega |
| --- | --- | --- |
| F4.1 | Município do Rio de Janeiro | Segundo município urbano, maior mercado do estado, via DATA.RIO / IPP |
| F4.2 | Inventário dos 92 municípios | Planilha de quem publica lote cadastral aberto — define se a camada urbana escala ou estaciona |
| F4.3 | Camadas de infraestrutura | Rodovias do DNIT e afins — cruzamentos que hoje ninguém faz |
| F4.4 | API para terceiros | Vender o motor para quem já tem sistema (banco, ERP agro, escritório) |
| F4.5 | Federação para outros estados | A arquitetura já trata a UF como dimensão explícita; o custo é ingestão + verificação, não redesenho |

**Contagem:** 0 / 5.

---

## Fora do roadmap, por decisão

| Item | Razão |
| --- | --- |
| Valuation e preço estimado | Exige base de transações que não temos e responsabilidade de laudo que não queremos |
| Emissão de documento com fé pública | Não somos cartório |
| Edição de dado público pelo usuário | Retificação cadastral é com o órgão que produziu o dado |
| App móvel nativo | Painel web responsivo cobre o uso previsto |
