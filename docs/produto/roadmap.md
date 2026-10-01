<!-- CLASSIFICAÇÃO: ROADMAP DE PROJETO · segue o MODELO PADRÃO do workspace (_hq/biblioteca/roadmaps/ROADMAP-projeto-PADRAO.md, decisão 2026-09-10) e a portfolio/ROADMAP-CONVENTION.md -->

# Roadmap

> Uma espinha canônica que a máquina lê + prosa livre que o humano escreve. O deck de portfólio lê só a espinha.
> Versão anterior (fases 0–4, formato próprio) preservada em [`roadmap-old.md`](roadmap-old.md).
>
> **Status:** ✅ feito · ⚠️ feito c/ débito · 🔄 em andamento · 🗓️ planejado · ⚪ sem spec · 🔒 bloqueado por dependência externa · ⏭️ condicional (só existe se um "se" confirmar)
> **Domínio** (pasta durável, futuro `dominios.md`) ≠ **Feature** (unidade de entrega). Tag por linha.
> **SemVer:** MAJOR = novo pilar/fase de negócio · MINOR = feature no pilar · `0.x` = primeiro pilar (o MVP) em construção.
> **Invariante:** exatamente **1** item `🔄` em todo o arquivo — é o foco atual (`grep 🔄 roadmap.md`).

Datas são deliberadamente ausentes: as dependências externas (verificar fontes, contatar o ONR) têm
prazo que não controlamos. Vocabulário em [glossario.md](glossario.md); o que **não** faremos e por
quê, em [riscos.md](riscos.md).

**Regra que a Fatia 5 nos ensinou:** cada camada de restrição/urbana nova carrega um custo de
verificação de fonte próprio (achar o endpoint real, medir schema/CRS/contagem antes de escrever
código). Toda fonte nova pode gerar uma feature nova — os totais abaixo são **piso, não teto**.

---

## Visão geral (uma tela)

| Versão | Fase | Alvo da fase | Domínios | Status |
|--------|------|--------------|----------|--------|
| v0.1 | Verificar fontes | as fontes geoespaciais existem e são usáveis de verdade? | `ingestao` (pré-medição) | ✅ fechada (reabre por fonte nova) |
| v0.2 | Motor do dossiê | o cruzamento vale mais que o dado cru — provado fim-a-fim | `dossie`, `ingestao`, `geometria`, `cobertura`, `api` | ✅ fechada |
| v0.3 | MVP visível | um usuário clica no mapa e vê o dossiê | `app`, `api`, `ingestao`, `cobertura` | 🔄 *(F1.9/F1.11/F1.12 fechadas; falta F1.8/F1.6/F1.7 + base no ar)* |
| v0.4 | Fazer circular | o dossiê vira artefato e a divergência vira produto | `api`, `geometria`, `autorizacao` | 🗓️ |
| v0.5 | Camada registral | existe caminho jurídico defensável p/ o dado registral? | `registral`, `autorizacao` | ⏭️ condicional |
| v1.0 | Ampliação | escala em município, camada, estado e canal | `ingestao`, `api` | 🗓️ |

---

## v0.1 — Verificar fontes ✅ · *(fechada; reabre por fonte nova)*
**Alvo atingido:** nenhuma ingestão antes de medir a fonte por acesso real. Não "fecha" de vez —
reabre toda vez que uma camada nova entra no escopo.

| Feature | Domínio | Slice | Status |
|---------|---------|-------|--------|
| SIGEF RJ — feições, CRS, validade | `ingestao` | 0.1 | ✅ *(14.664 feições, EPSG:4674, 0 inválidas)* |
| CAR + sobreposição SIGEF×CAR | `ingestao` | 0.2 | ✅ *(69.105 feições; só 35,1% sobrepõem SIGEF — confirma AD-003)* |
| SIGeo Niterói expõe lote (não só quadra) + endpoint | `ingestao` | 0.3 | ✅ *(82.199 feições, EPSG:31983, FeatureServer)* |
| UC — fonte consolidada | `ingestao` | 0.4 | ✅ *(455 feições MPRJ/CNUC, EPSG:4326)* |
| INEA inundação / deslizamento / corpo d'água | `ingestao` | 0.5 | 🗓️ *(não verificada — custo de verificação por camada; bloqueia F1.6/F1.7)* |

Detalhe em [`../research/fontes-de-dados-rj.md`](../research/fontes-de-dados-rj.md). A verificação do
ONR **não** é fonte geoespacial do dossiê — é a pergunta que decide se v0.5 existe (feature F3.1).

## v0.2 — Motor do dossiê ✅ · *(fechada)*
**Alvo atingido:** o motor do dossiê roda fim-a-fim sobre PostGIS real e já tem superfície HTTP.
Corresponde às três histórias P1 do spec (DOS-01 a DOS-13, mais DOS-25/26/28/29/30).

| Feature | Domínio | Slice | Status |
|---------|---------|-------|--------|
| F1.1 Núcleo de domínio | `dossie` | Fatia 1 | ✅ *(árvore de decisão a partir de um read-model)* |
| F1.2 Persistência + ingestão rural SIGEF | `ingestao` | Fatia 2 | ✅ *(schema PostGIS versionado, guarda de 90%, swap atômico)* |
| F1.3 Restrição CAR (APP + Reserva Legal) | `restricoes` | Fatia 3 | ✅ *(cruza APP e Reserva Legal com o lote)* |
| F1.4 Cobertura honesta | `cobertura` | Fatia 4 | ✅ *(camada ingerida deixa de aparecer falsamente "sem cobertura" — DOS-11)* |
| F1.5 Restrição Unidade de Conservação | `restricoes` | Fatia 5 | ✅ *(UC por categoria SNUC cruzada com o lote)* |
| F1.10 API HTTP (FastAPI) | `— ops` | Fatia 6 | ✅ *(rotas /dossie, /cobertura, /saude; rate limit 100/h DOS-27; identidade via header AD-011; observabilidade DOS-30)* |

## v0.3 — MVP visível 🔄
**Prioridade principal:** o que falta para um usuário ver o dossiê é o painel web (F1.11); as camadas
F1.6–F1.9 aumentam o valor do cruzamento em paralelo.

| Feature | Domínio | Slice | Status |
|---------|---------|-------|--------|
| F1.11 Painel web + conta autenticada | `— ops` | — | ✅ *(mapa, clique→dossiê, conta obrigatória sem paywall, magic link; AD-012, Verifier PASS)* |
| F1.12 Página de cobertura pública | `cobertura` | — | ✅ *(estado real por município × camada, `GET /cobertura/estado` + `app/cobertura.html`; sem limiar de obsolescência ainda — DOS-29 parcial; Verifier PASS)* |
| F1.8 Malha municipal IBGE + resolução de município | `ingestao` | — | 🗓️ *(destrava o clique "sem lote" DOS-04 e o nome de município; fecha TD-001)* |
| F1.9 Camada urbana Niterói (SIGeo) | `restricoes` | — | ✅ *(82.205 lotes de Niterói no dossiê, UC cruzada, atribuição SIGeo; Verifier PASS; base ainda não restaurada no Railway)* |
| F1.6 Restrição inundação + deslizamento (INEA) | `restricoes` | — | 🔒 *(fonte a verificar — slice 0.5)* |
| F1.7 Restrição corpo d'água | `restricoes` | — | 🔒 *(fonte a verificar — slice 0.5)* |

## v0.4 — Fazer circular 🗓️
**Prioridade principal:** o dossiê sai do painel e vira artefato; a divergência entre fontes vira
produto; a estrutura de autorização nasce vazia. Corresponde às três histórias P2 do spec (DOS-14 a
DOS-22, mais DOS-27).

| Feature | Domínio | Slice | Status |
|---------|---------|-------|--------|
| F2.1 Exportação em PDF | `— ops` | — | ⚪ *(dossiê carimbado com data, versão da base e ressalva de fé pública)* |
| F2.2 Divergência SIGEF × CAR | `restricoes` | — | ⚪ *(dois polígonos, diferença em ha e %, alerta acima de 5% — nunca reconcilia, AD-003)* |
| F2.3 Gate jurídico (decisão de acesso) | `autorizacao` | — | ⚠️ *(lógica Verified GATE-01..06; falta adapter de persistência + auditoria real — TD-gate)* |

**Por que o gate vem antes do dado registral:** construir autorização e auditoria depois significa
reescrever o sistema; construir antes custa pouco e transforma v0.5 em ligar uma chave.

## v0.5 — Camada registral ⏭️ *(condicional)*
**A versão inteira é condicional:** só avança se F3.1 confirmar um caminho jurídico defensável.

| Feature | Domínio | Slice | Status |
|---------|---------|-------|--------|
| F3.1 Verificação do caminho registral (ONR) | `registral` | — | 🔒 *(existe API do ONR para terceiros? decide SE a fase existe — pendência humana, contato com o ONR)* |
| F3.2 Camada registral | `registral` | — | ⏭️ *(ligar o dado registral ao dossiê sob o gate, num dos três desenhos abaixo)* |

Desenhos possíveis de **F3.2**, em ordem decrescente de valor e de risco:

| Desenho | Como funciona | Depende de |
|---------|---------------|------------|
| Consulta viva | app consulta o registro no ato sob identidade do usuário habilitado, exibe e loga; sem cache de conteúdo pessoal | integração do ONR para terceiros |
| Deep link | app leva o usuário ao pedido de certidão no portal oficial, já preenchido | só o portal existir |
| Upload de certidão | usuário anexa a certidão que ele mesmo obteve; o app extrai e cruza | nada externo |

**O que nunca acontece, em nenhum desenho:** ingerir e servir uma base agregada de "proprietário →
imóveis". Ver [riscos.md](riscos.md).

## v1.0 — Ampliação 🗓️
**Prioridade principal:** escalar em ordem de custo crescente por unidade de valor.

| Feature | Domínio | Slice | Status |
|---------|---------|-------|--------|
| F4.1 Município do Rio de Janeiro | `restricoes` | — | ⚪ *(segundo município urbano, maior mercado do estado, via DATA.RIO / IPP)* |
| F4.2 Inventário dos 92 municípios | `ingestao` | — | ⚪ *(quem publica lote cadastral aberto — define se a camada urbana escala ou estaciona)* |
| F4.3 Camadas de infraestrutura | `restricoes` | — | ⚪ *(rodovias do DNIT e afins — cruzamentos que hoje ninguém faz)* |
| F4.4 API para terceiros | `— ops` | — | ⚪ *(vender o motor para quem já tem sistema: banco, ERP agro, escritório)* |
| F4.5 Federação para outros estados | `— ops` | — | ⚪ *(a arquitetura já trata a UF como dimensão; o custo é ingestão + verificação, não redesenho)* |

---

## Domínios (referência — detalhe futuro em `dominios.md`)
- **dossie** — árvore de decisão do dossiê a partir do read-model · **ingestao** — schema PostGIS, adapters de fonte, publicação com guarda + swap atômico · **restricoes** — camadas geoespaciais cruzadas com o lote (CAR, UC, INEA, corpo d'água, urbana) · **cobertura** — estado real por município × camada · **registral** — dado do registro de imóveis (condicional) · `autorizacao` — autorização, verificação de credencial, log imutável (cross-cutting) · `— ops` — API HTTP, painel web, exportação, deploy (suporte) · `ingestao` — medição de fonte antes de ingerir (suporte).

## Débito herdado das fases fechadas
*(features `⚠️` acima — "feito" não é "sem resíduo")*

| TD | Origem | Status | Trigger de revisita |
|----|--------|--------|----------------------|
| TD-001 | v0.2 (clique sem lote / nome de município) | open | fecha em F1.8 (v0.3) |
| TD-gate | v0.4 F2.3 (gate sem persistência/auditoria) | open | quando v0.5 for confirmada por F3.1 |

## Backlog por domínio (pool — futuro `backlog.md`)
- `restricoes` — MapBiomas (uso/cobertura do solo), condicionado a licença comercial · GeoPAL (alinhamentos do município do Rio) · `— ops` — app móvel (só se o painel responsivo não cobrir).

## Fora de escopo (decisão de NÃO fazer, não "ainda não")
- 🚫 Valuation / preço estimado — exige base de transações que não temos e responsabilidade de laudo que não queremos.
- 🚫 Emissão de documento com fé pública — não somos cartório.
- 🚫 Edição de dado público pelo usuário — retificação cadastral é com o órgão que produziu o dado.
- 🚫 App móvel nativo — painel web responsivo cobre o uso previsto.
