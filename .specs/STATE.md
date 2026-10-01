# STATE

Memória do projeto: log de decisões (AD-NNN) e snapshot de handoff.

## Decisions

### AD-001 — Recorte geográfico: apenas Rio de Janeiro
**Data:** 2026-08-18
**Decisão:** O produto cobre exclusivamente o estado do RJ (UF 33) nesta fase.
**Razão:** Foco declarado pelo usuário. Permite profundidade de cruzamento em vez de largura rasa.
**Consequência:** Toda consulta valida a UF antes de processar. A arquitetura mantém a UF como
dimensão explícita para federar depois, mas nenhuma outra UF é ingerida.

### AD-002 — Camada de proprietário fora do MVP, com gate arquitetado
**Data:** 2026-08-18
**Decisão:** Nome, CPF/CNPJ, ônus e cadeia dominial não são ingeridos nem persistidos nesta versão.
Papéis de usuário, verificação de credencial e log de auditoria são construídos em P2, vazios.
**Razão:** A publicidade registral (Lei 6.015/73 art. 17) sustenta consulta por certidão, não a
agregação e redistribuição de uma base "proprietário → imóveis". A LGPD não isenta dado público
de origem quando ele é agregado. Não há integração pública documentada do ONR para terceiros.
**Consequência:** A seção de proprietário aparece como "indisponível nesta versão". Quando o
caminho registral for confirmado, liga-se a camada sem reescrever autorização e auditoria.

### AD-003 — SIGEF é o limite autoritativo; CAR é declaração
**Data:** 2026-08-18
**Decisão:** Onde as duas fontes descrevem o mesmo imóvel rural, o SIGEF é apresentado como limite
certificado e o CAR como declaração do proprietário. As divergências são exibidas, nunca reconciliadas.
**Razão:** SIGEF é certificado pelo INCRA; CAR é autodeclaratório. Reconciliar silenciosamente
esconderia exatamente o achado de maior valor para o usuário.
**Consequência:** O modelo de dados guarda as duas geometrias por imóvel, não uma "geometria final".

### AD-004 — Base própria, não proxy de portais públicos
**Data:** 2026-08-18
**Decisão:** Os dados públicos são baixados, validados e materializados em banco próprio. As
consultas do usuário nunca dependem de um portal do governo estar de pé.
**Razão:** Latência, disponibilidade e capacidade de cruzar fontes que não se conhecem.
**Consequência:** Exige pipeline de ingestão versionado e política de atualização explícita.
Cria a obrigação de carimbar data de extração por camada.

### AD-005 — Proveniência é requisito, não enfeite
**Data:** 2026-08-18
**Decisão:** Todo campo exibido carrega fonte e data de extração. Ausência de dado é declarada
como ausência de cobertura, nunca devolvida como vazio ambíguo.
**Razão:** O produto vende confiança para decisão financeira. Um número sem origem é um chute
bem formatado, e cobertura irregular por município é fato estrutural do RJ, não defeito temporário.
**Consequência:** O esquema de dados carrega metadados de proveniência junto de cada feição, e
existe uma página pública de cobertura por município e camada.

### AD-006 — Piloto urbano: município de Niterói
**Data:** 2026-08-18 (revisada)
**Decisão:** A camada urbana do MVP cobre apenas o município de Niterói, via SIGeo. O município do
Rio de Janeiro é o segundo.
**Razão:** Escolha do usuário, sustentada tecnicamente: o SIGeo publica WFS, WMS e GeoJSON por
ArcGIS Hub, permitindo ingestão automatizada e reprodutível. O DATA.RIO também publica dado
aberto, mas a granularidade da camada de lote não está confirmada.
**Consequência:** A página de cobertura precisa deixar explícito que 91 municípios não têm camada
urbana. A revisão substitui a decisão anterior, que apontava o município do Rio como piloto.

### AD-007 — Arquitetura: monolito Python modular com read-model materializado por versão
**Data:** 2026-08-20
**Decisão:** O backend é um monolito Python (FastAPI) organizado por domínio, com a **ingestão como
entrypoint separado no mesmo repo**. O dossiê é montado a partir de um **read-model materializado
por versão de base**: as intersecções lote × restrição são calculadas na ingestão, não por consulta.
**Razão:** MVP de um dev — separar a ingestão pesada (que exige egress `.gov.br`) sem pagar um
segundo deployable. Uma linguagem só evita duplicar a regra geoespacial. Materializar torna DOS-03
(10s p95), DOS-26 (idempotência) e DOS-28 (troca atômica) verdadeiros por construção, não por
esforço em tempo de request. Escolhido pelo usuário entre 3 approaches (A/B/C).
**Consequência:** Toda regra de negócio vive em módulos framework-agnósticos; a rota FastAPI só
orquestra. A ingestão nunca está no caminho de request. Read-model cresce por versão → exige
política de retenção de N versões.

### AD-008 — CRS canônico e versionamento de base por ponteiro
**Data:** 2026-08-20
**Decisão:** Armazenamento em SIRGAS 2000 (EPSG:4674); área calculada em projeção equivalente;
Web Mercator (3857) só para tiles. Publicação de versão troca um **ponteiro `published` por swap
atômico em transação**, com guarda de ≥90% das feições da versão anterior.
**Razão:** EPSG:4674 é o padrão oficial brasileiro; a área correta não pode depender do SRID de
exibição. O ponteiro atômico garante que nenhuma consulta veja base meio atualizada e que a
reingestão não misture versões dentro de um dossiê.
**Consequência:** Toda tabela cujo dado muda por reingestão carrega `versao_base_id`. O SRID final
e a granularidade de lote do SIGeo permanecem **pendentes de confirmação na Fase 0** — o design é
robusto a ambos (CRS é config; camada urbana fica atrás de cobertura declarada).

### AD-009 — `cobertura` semeada na ingestão, derivada do que foi publicado
**Data:** 2026-09-04
**Decisão:** A tabela `cobertura` (município × camada → tem dado / data) é semeada por um passo de
ingestão dedicado, `semear_cobertura(versao, conexao)`, chamado **depois** de `materializar_intersecoes`
e **antes** de `publicar_versao` (rida a mesma transação — só persiste se a versão publicar). O
conjunto de municípios vem de `lote_rural.municipios` DISTINCT da versão (não de uma lista externa
de municípios nem da malha municipal do IBGE — TD-001 fica independente); o conjunto de camadas vem
de `restricao.tipo` DISTINCT (genérico — INEA/ICMBio futuras entram sem tocar este passo); a
`data_extracao` vem de `proveniencia` (fonte única da data, AD-005).
**Razão:** Fecha TD-002 sem puxar a malha municipal (TD-001) nem uma lista de 92 códigos IBGE: as
camadas de restrição APP/Reserva Legal são estaduais, logo cobrem todo município que contenha um
lote — e o único caminho de dossiê que hoje consulta `cobertura_de` é o do lote achado, cujo
município já vem do próprio `lote_rural`. Derivar de `restricao` mantém o passo genérico para as
próximas camadas. Rodar dentro da transação de publicação torna a cobertura consistente com a base
publicada por construção (mesmo espírito de atomicidade do AD-008/DOS-28).
**Consequência:** `cobertura` é keyed por código IBGE bruto (mesmo valor de `lote_rural.municipios`,
herda a limitação código-vs-nome de TD-001). O passo é idempotente (`ON CONFLICT DO UPDATE`). Um
concern novo: como `cobertura` não é versionada e o passo só faz upsert, um município que perca
todos os lotes numa reingestão mantém a linha antiga (staleness) — aceitável no MVP, anotado como
concern em TD-002 ao fechá-lo. O caminho `SemLote` (DOS-04) segue quebrado por TD-001 (independente).

### AD-010 — UC ingerida da camada consolidada do MPRJ (não do WFS fragmentado do INDE)
**Data:** 2026-09-04
**Decisão:** A camada de restrição Unidade de Conservação (Fatia 5) é ingerida da camada
**consolidada "UC ERJ" do FeatureServer ArcGIS do MPRJ** (CNUC federal + estaduais/municipais,
455 feições RJ), reusando a tabela genérica `restricao` com `tipo='unidade_conservacao'`. O WFS do
INDE foi rejeitado como fonte: lá o INEA publica as UCs fragmentadas em ~631 feature types e o
ICMBio não expõe o dataset federal — enumerar as 631 arriscaria incompletude silenciosa (fere
AD-005).
**Razão:** Uma camada consolidada, medida por acesso real (0 inválidas/vazias, EPSG:4326, três
esferas), é honesta e completa por construção; a fragmentada não. Manter `restricao` genérica evita
código específico por camada — a próxima restrição (inundação/deslizamento/corpo d'água) reusa o
mesmo caminho + uma extensão do CHECK. A cobertura da Fatia 4 (AD-009) faz a UC aparecer sozinha no
dossiê, sem tocar `montagem.py`.
**Consequência:** `restricao.tipo` ganhou `'unidade_conservacao'` (migração 0004) e a guarda de
publicação (DOS-25) passou a cobri-la. Fica pendente confirmar licença/atribuição do MPRJ para
redistribuição (proveniência já carimba fonte+data+link) e avaliar GEOINEA/INEA como origem
autoritativa alternativa. As outras 3 camadas de restrição seguem **não verificadas** — cada uma
exige medição por acesso real antes do código, como esta teve.

### AD-011 — API HTTP (F1.10): versão resolvida por request, identidade opaca via header, rate limit em memória
**Data:** 2026-09-08
**Decisão:** A superfície HTTP (FastAPI, AD-007) da Fatia 6 assume três escolhas:
1. **Versão da base é resolvida no servidor por request**, lendo `ponteiro_publicado` (a versão de
   `Camada.LOTE_RURAL`) — o cliente **não** informa versão. Idempotência (DOS-26) vem do ponteiro
   ser estável entre reingestões; um dossiê muda só quando a base publicada muda.
2. **Identidade da conta chega como header opaco `X-Conta-Id`** (dependency injetável), não como
   login/senha/JWT. `consulta_log.usuario_id` (DOS-30) e a cota de rate limit (DOS-27) chaveiam por
   ela. O mecanismo de auth real (sessão/OAuth/gov.br) nasce com o painel (F1.11) sem reescrever a
   API — a fronteira `PapelConta`/`Conta` do gate jurídico (AD-002) já está modelada e não é tocada.
3. **Rate limit (100/h por conta, DOS-27) é um contador em memória de processo**, janela deslizante
   por hora. MVP de um processo só; quando o deploy escalar para N réplicas, troca-se o backend do
   contador (Redis) sem mudar a regra nem a rota.
**Razão:** A API é o entrypoint fino do AD-007 — nenhuma regra de negócio vive nela, ela orquestra
`montar_dossie`/cobertura. Resolver a versão no servidor mantém o cliente burro e a idempotência por
construção. Identidade via header destrava DOS-30/DOS-27 hoje sem pagar o custo (e o risco de
retrabalho) de um modelo de identidade completo antes de existir painel que o exercite — decisão do
usuário entre 3 opções (2026-09-08). Contador em memória é a coisa mais simples que torna DOS-27
verdadeiro no MVP; persistir a cota seria over-spec para tráfego de um processo.
**Consequência:** Nova dep `fastapi`/`uvicorn` (runtime) e `httpx` (teste, via `TestClient`). Um
módulo `api/` fino: resolve versão publicada, injeta `conta_id`, aplica rate limit, traduz o
tipo-resultado da montagem (`Dossie`/`SemLote`/`Sobreposicao`/`ForaDoRJ`) em HTTP + DTO, grava
`consulta_log`. **Débito assumido:** o contador de rate limit em memória zera no restart do processo
e não é compartilhado entre réplicas (registrar em TECH-DEBT ao fechar). O ramo `SemLote` da rota
segue quebrado por **TD-001** (`municipio_em` sem malha) — a rota o traduz para 404 mas o adapter
levanta `NotImplementedError`; o teste da rota cobre o caminho "achou lote"/"fora do RJ", não o
`SemLote` real (independente desta fatia).

### AD-012 — Painel F1.11: front vanilla estático (supersede a linha "SPA React/Vite" da spec)
**Data:** 2026-09-10
**Decisão:** O front do painel (F1.11) é **HTML+CSS+JS vanilla estático servido como arquivos**
(mapa via Leaflet + tiles OSM), evoluindo o protótipo `prototipos/mapa-dossie/`. **Supersede** a
Assumption da spec `painel-web-conta` (linha 50: "SPA separado React/Vite") — o auth e a API
continuam exatamente como a spec define; só a tecnologia de UI muda.
**Razão:** Coerência com o próprio critério da spec. A spec rejeitou Better Auth (linha 30/58)
porque *"é TS/Node, o backend é 100% Python; trazer um segundo runtime só para isso não se paga"*.
React/Vite traz o mesmo 2º runtime Node — e F1.11 tem só 4 estados de UI (login, 200/404/409/429),
com geometria no mapa e comparação rica explicitamente fora de escopo. O ganho do React (orquestrar
muitos estados, ecossistema de mapas) só aparece em features que ainda não existem. O protótipo já
entrega o layout do dossiê pronto para reuso. Beleza de UI vem do CSS, não do framework — empate
estético nesta fatia. Escolhido pelo usuário após trade-off explícito (2026-09-10).
**Consequência:** Sem build step, sem `node_modules`, sem toolchain Node no deploy do front — só
arquivos estáticos atrás de um servidor (nginx/Caddy) no subdomínio `app.` (o cookie de sessão de
domínio pai da spec continua valendo). Nenhuma dep nova no `pyproject.toml`. Se F1.12+ trouxer UI
rica, migra-se **só a tela de mapa** para React sem tocar o backend (cookie + `GET /dossie` são
agnósticos de front) — decisão barata de adiar. Débito: teste de UI vanilla é mais manual/`node
--test` sobre módulos JS puros do que um harness de componentes React (aceitável no MVP).

### AD-013 — Deploy no Railway, front e API na mesma origem, base carregada local e restaurada
**Data:** 2026-09-30
**Decisão:** Produção no Railway (projeto `terrametrica`): um serviço `web` (Dockerfile; uvicorn
serve a API **e** os arquivos de `app/` via `StaticFiles`, montado depois das rotas) + um serviço
`PostGIS` (template oficial, Postgres 16). A base é montada **localmente** pelo CLI
`python -m terrametrica.ingestao.carregar_base` e levada ao Railway por `pg_dump`/`pg_restore`.
**Razão:** Escolhido pelo usuário na RFD de infra (opção B, contra VPS+Caddy e CDN+container): menor
tempo até URL pública, sem operar SO. Mesma origem elimina o cookie de domínio pai, o DNS de dois
subdomínios e o CORS — o desenho `app.`/`api.` do design de F1.11 vira opcional
(`TERRAMETRICA_DOMINIO_COOKIE` continua suportado). Carga local porque a ingestão grava feição a
feição: contra um banco nos EUA seria uma ida-e-volta de rede por feição.
**Consequência:** Sem região no Brasil (~120–150ms do RJ, irrelevante frente a DOS-03). Reingestão
continua manual até existir job agendado — e aí volta a pergunta de egress `.gov.br` a partir de IP
estrangeiro (hipótese não verificada). Supersede a menção a nginx/Caddy e subdomínio `app.` da AD-012.

### AD-014 — Período sem login: acesso aberto por flag, identidade anônima por IP
**Data:** 2026-10-01
**Decisão:** `TERRAMETRICA_ACESSO_ABERTO=1` faz a API aceitar `/dossie` sem sessão nem header. Quem
chega sem credencial vira `anonimo:<sha256(ip)[:16]>`; sessão válida e header continuam valendo e
têm precedência. Padrão **desligado** (login obrigatório, AD-012 intacto).
**Razão:** Decisão do usuário (2026-10-01): usar o produto por um período sem o atrito do e-mail,
inclusive sem depender do Resend. Por IP, e não uma conta única compartilhada, para a cota de
100/h (DOS-27) continuar significando "por visitante". Hash para o `consulta_log` nunca guardar IP
em claro (LGPD).
**Consequência:** Voltar a exigir login = remover a variável, sem mudança de código. Enquanto
aberto: o painel não redireciona para `login.html` (só redireciona em 401); o botão "Sair" é inócuo;
atrás de NAT/CGNAT visitantes diferentes dividem uma cota; e `X-Conta-Id` forjado burla a cota — já
era assim em AD-011, mas agora o painel público fica exposto. Risco aceito no período.

## Handoff

**Branch:** `main`. **Fase atual:** Execute + verificação **concluídos** para a **Página de
Cobertura Pública (F1.12)** (`.specs/features/pagina-de-cobertura-publica/`, 3 tasks inline —
escopo Medium, sem `tasks.md` formal). Validação **PASS** por Verifier independente
(`validation.md`): 6/6 requisitos COBPUB-01..06 cobertos com asserção ancorada na spec; gates verdes
(ruff 0, mypy strict 0, **220 Python passed + 9 JS passed**, 0 falhas); sensor de discriminação
**3/3 mortos**. **Nota:** o "bug pré-existente" `test_dto.py::test_distingue_os_tres_estados_de_camada`
citado no handoff da Fatia 7 **já não falha** — confirmado passando tanto na base quanto no HEAD
desta fatia; o handoff anterior estava desatualizado (a causa raiz não foi investigada, só
constatado que não é mais um bloqueio).
**O que existe agora, além de F1.1–F1.11:** `RepositorioLotesPostGIS.cobertura_de_todos()` +
`CoberturaMunicipio` (dominio/modelos.py) agregam toda a tabela `cobertura` por município, ordem
alfabética; `cobertura_estado_para_dict` (api/dto.py) preenche toda `Camada` do domínio por
município (nunca omite uma camada, mesma honestidade de DOS-11); rota nova `GET /cobertura/estado`
(api/app.py), pública, sem sessão/header — `GET /cobertura?municipio=X` (F1.10) não mudou, confirmado
byte-a-byte pelo Verifier. Front: `app/cobertura.html` + `app/cobertura.js` (view model puro,
testado por `node --test`) renderizam uma tabela município×camada com data `DD/MM/AAAA` (nunca ISO)
e "sem dado" explícito. **Bug de layout achado e corrigido durante verificação manual (Playwright):**
`.badge { display: inline-block }` aplicado direto num `<td>` quebra `display:table-cell` — badge
movido para um `<span>` interno.
**Decisões da fatia (registradas em `spec.md`, Assumptions & Open Questions, não em `STATE.md`
Decisions — escopo Medium):** página lista só municípios com ≥1 lote (não os 92 do RJ, evita
depender de TD-001); sem limiar automático de "obsoleto" (reafirmado mesmo após achar
`LIMIAR_DIAS_DESATUALIZADA=90` já usado por DOS-13 no dossiê individual — decisão consciente de
manter os dois lugares com critérios diferentes por ora); página pública sem login (ao contrário do
painel F1.11/AD-012); rota nova é JSON puro + JS estático (não HTML server-side) — corrigido em
Specify após checar que AD-012 já fixa esse padrão no projeto inteiro.
**Gap não-bloqueante (relatado pelo Verifier):** a renderização DOM (`pintarTabela`/`pintarVazio`
em `cobertura.html`) só tem evidência manual (Playwright); o view model puro (`cobertura.js`) tem
cobertura automatizada completa. Não virou tech debt formal — reavaliar se a página crescer em
complexidade de DOM.
**Commits (F1.12):** `cab4883` T1 (`cobertura_de_todos`) · `1e2f0d7` T2 (rota `/cobertura/estado`)
· `cce3d6d` T3 (`cobertura.html`/`cobertura.js` + fix de layout). **Nada em push** — verificar
`git rev-list --count origin/main..main` antes do próximo push.
**Próximo passo natural:** roadmap tem F1.8 (malha municipal IBGE, fecha TD-001), F1.9 (camada
urbana Niterói), F1.6/F1.7 (inundação/deslizamento/corpo d'água, 🔒 fonte a verificar) como
candidatos para reabrir o `🔄` de v0.3 — decisão do usuário, roadmap ainda não atualizado com F1.12
✅ (fazer isso quando o usuário confirmar o próximo item, mantendo a invariante de 1 único `🔄`).
**RFD de infra** do design de F1.11 (VPS+Caddy vs CDN+container; DNS `app.`/`api.`, TLS,
`RESEND_API_KEY`, cookie `Domain` pai) segue **aberta** — resolver antes do primeiro deploy real.

---

**Handoff anterior (Fatia 7 — Painel web + conta autenticada, F1.11):** Execute PASS (T1–T10), 212
passed. Detalhe abaixo, preservado.

**Fase atual:** Execute + verificação **concluídos** para a **Fatia 7 — Painel web + conta
autenticada (F1.11)** (`.specs/features/painel-web-conta/`, 10 tasks T1–T10). Validação **PASS** por
Verifier independente (`validation.md`): 14/14 requisitos PAINEL-NN + 4 edge cases cobertos com
asserção localizada e ancorada na spec; gates verdes (ruff 0, mypy strict 0, **212 passed** — a 1
falha restante é o **bug pré-existente** `test_dto.py::test_distingue_os_tres_estados_de_camada`,
fora de escopo, confirmado falhando no commit base `e5ec45b`); sensor de discriminação **5/5
mortos**. Decisão da fatia: **AD-012** (front vanilla estático). **Débitos:** **TD-006** (`conta_id`
sem tabela `conta` física); CSRF-MVP em `/auth/*` (mitigado por `SameSite=Lax` + rate limit) e GC de
`login_token`/`sessao` expirados ficaram como concerns aceitos no design (não promovidos a TD
numerado — revisitar se surgir). **O que existe agora, além das Fatias 1-6:** módulo
`terrametrica.auth` (regras puras + ports Protocol + serviço + adaptadores Postgres/Resend); migração
`0006_fatia7_auth.sql` (`credencial_login`/`login_token`/`sessao`, PII isolada de `Conta`, tokens em
hash); identidade da API agora resolve por **sessão (cookie) OU header** (`api/identidade.py`,
precedência sessão>header, retrocompat F1.10 intacta — Success Criteria 3); 3 rotas `/auth/solicitar`
`/auth/confirmar` `/auth/logout` (`api/app.py`); front vanilla estático em `app/` (login.html,
index.html+mapa.js Leaflet, dossie.js testado por `node --test`, estilos.css herdado do protótipo).
`httpx` promovido a dep de runtime. **Fluxo provado fim-a-fim no navegador (Playwright):** login por
magic link → cookie httpOnly/Secure → clique no mapa autentica → `GET /dossie` retorna 200 com o
dossiê. **Lições:** L-002 (AC de UI precisa de evidência manual, não só 401 server-side), L-003
(`token_valido` é lógica de referência dos fakes; expiry real é a query `_CONSUMIR_TOKEN`).
**Commits (Fatia 7):** `9e7db89` T1 (migração 0006 + httpx) · `46ebabb` T2 (regras) · `5521fe5` T3
(portas) · `5d4de5e` T4 (serviço) · `9dc73b5` T5 (adaptadores) · `7b06f59` T6 (identidade sessão|
header) · `b2dc15e` T7 (rotas /auth/* + cookie→dossiê) · `e701f33` T8 (dossie.js) · `8a36816` T9
(login.html) · `920eb31` T10 (index.html+mapa.js) · `c6534ad` docs (validation PASS). **Bug
conhecido a tratar à parte (nota: revisado na Fatia F1.12, já não reproduz — ver handoff acima):**
`test_dto.py::test_distingue_os_tres_estados_de_camada` (ordena `corpo_dagua` vs `inundacao` em
`camadas_ausentes`) — pré-existe à F1.11, não corrigido aqui (fora de escopo).

---

**Handoff anterior (Fatia 6 — API HTTP F1.10):** Execute PASS (T28–T32), 149 passed. Detalhe abaixo, preservado.

**Fase (Fatia 6):** Execute concluído para a **Fatia 6 — API HTTP (F1.10)** (`tasks.md`, seção Fatia 6,
T28–T32 + fix de sensor). Validação **PASS** por Verifier independente (`validation.md`, seção
Fatia 6): gate verde (ruff 0, mypy strict 0, **149 passed** — +25 vs 124 da Fatia 5), sensor
**7 mortos / 2 sobreviventes**; o gap #1 (invariante "bloqueio não consome vaga" do rate limiter)
foi fechado com um teste de rajada ≥ limite (`04122ea`, confirmado que mata o mutante). Os 2 gaps
restantes viraram **TD-005** (aceitos, não corrigidos — lacunas de cobertura sobre código correto:
filtro `WHERE camada` de `resolver_versao` e o `409` de `Sobreposicao` sem caso e2e). Decisões da
fatia em **AD-011** (versão resolvida por request via `ponteiro_publicado`; identidade opaca via
header `X-Conta-Id`; rate limit 100/h em memória de processo). **Débito assumido:** rate limit em
memória não persiste/distribui (**TD-004**). O motor (`montagem.py`/`dominio`/`geometria`/adapters
PostGIS) **não mudou uma linha** — o Verifier confirmou no `--stat`; a API só orquestra (AD-007).
**Commits (Fatia 6):** `db2f6c7` T28 (deps fastapi/uvicorn/httpx + migração 0005 `consulta_log` +
`resolver_versao_publicada`) · `ce3f5b4` T29 (`api/dto.py` puro) · `98b09d7` T30 (identidade header
+ `LimitadorEmMemoria`) · `fe99742` T31 (`registrar_consulta`/DOS-30) · `a62393e` T32 (`api/app.py`
+ rotas + prova e2e HTTP via `TestClient`) · `04122ea` fix de sensor do rate limiter. **Nada em
push** — `main` está **26 commits à frente de `origin/main`** (`git rev-list --count origin/main..main`).
**O que existe agora, além das Fatias 1-5:** o pacote `api/` (FastAPI fino, AD-007): `GET /dossie`
(resolve versão publicada → `montar_dossie` → traduz `Dossie`/`SemLote`/`Sobreposicao`/`ForaDoRJ` em
200/404/409/422, aplica cota 429, exige `X-Conta-Id` senão 401, grava `consulta_log`), `GET /cobertura`,
`GET /saude`. Migração `0005` cria `consulta_log` (DOS-30, sem PII). Roda via
`uvicorn terrametrica.api.app:app_padrao --factory` (lê `TERRAMETRICA_DB_URL`). **Próximo passo
natural:** F1.11 (painel web + conta) consome `/dossie`; F1.12 (página de cobertura HTML) consome
`/cobertura`. O ramo `SemLote` real segue 🔒 por **TD-001** (a rota mapeia para 404, mas
`municipio_em` levanta `NotImplementedError`).

---

**Handoff anterior (Fatia 5 — Unidade de Conservação):** Execute PASS (T24–T27), 124 passed. Detalhe abaixo, preservado.

**Fase (Fatia 5):** Execute concluído para a **Fatia 5 — Unidade de Conservação (UC) como camada de
restrição** (`tasks.md`, seção Fatia 5, T24–T26 + fix task T27). Validação **PASS** por Verifier
independente (`validation.md`, seção Fatia 5): gate verde (ruff 0, mypy strict 0, **124 passed** —
+1 vs 123 após o fix), sensor **5 mortos / 0 sobreviventes** após o fix (o Verifier achou 1
sobrevivente — a reprojeção AD-008 não era sensorizada porque o SRID vinha hardcoded do SQL; T27
adicionou fixture em EPSG:31983/metros que mata o mutante de `to_crs`). **Pré-requisito cumprido:**
a fonte de UC **não estava verificada** (só CAR estava) — foi feita a verificação Fase-0 por acesso
real (455 feições MPRJ, EPSG:4326, 3 esferas) ANTES do código, decisão em **AD-010**.
**Commits (Fatia 5):** `f027efe` T24+T25 (migração 0004 + `ingerir_uc`) · `45afce7` T26 (guarda de
publicação + e2e) · `64316e7` docs (AD-010 + research + tasks) · `360162d` T27 (sensor de
reprojeção + TD-003). **Nada em push** — `main` está **18 commits à frente de `origin/main`**
(medido por `git rev-list --count origin/main..main`; números anteriores no handoff estavam
desatualizados — este é o real).
**O que existe agora, além das Fatias 1-4:** `ingestao/restricao_uc.py::ingerir_uc` (lê GeoJSON da
camada consolidada UC ERJ do MPRJ, reprojeta 4326→4674, grava genérico em `restricao` com
`tipo='unidade_conservacao'` + proveniência), migração `0004` (estende o CHECK do `tipo`), UC na
guarda de publicação (DOS-25). A cobertura da Fatia 4 faz a UC aparecer sozinha no dossiê —
`montagem.py`/`geometria`/`dominio` **não mudaram**. Entrega o AC#2 de "P1: Restrições" (UC com
nome+categoria); traceability por DOS ainda em aberto (**TD-003** — DOS-09 sem texto no repo).
**Dado real baixado (gitignored):** `data/raw/rj/uc/uc_erj.geojson` (40 MB, 455 UCs, regenerável
via `.../FeatureServer/12/query?f=geojson`).

---

**Handoff anterior (Fatia 4 — Seed de cobertura):** Execute PASS (T21-T23), 119 passed, TD-002
resolvido. Detalhe abaixo, preservado.

**Fase atual (Fatia 4):** Execute concluído para a **Fatia 4 — Seed de cobertura** (T21–T22 + T23). Validação **PASS** por Verifier
independente registrada em `validation.md` (seção Fatia 4): gate verde (ruff 0, mypy strict 0,
**119 passed** — +8 vs baseline 111 da Fatia 3), sensor pós-fix **4 mortos / 1 sobrevivente por
escolha** (mutante C = DISTINCT, testaria o `ON CONFLICT` do próprio PostgreSQL). O Verifier passou
no objetivo central na 1ª rodada (2/5 mutantes mortos) e apontou 3 sobreviventes; fix task T23
matou os dois de maior impacto (D = refresh do upsert/DOS-13; B = filtro INNER JOIN sem
proveniência). **DOS-11 marcado `✅ Verified` em `spec.md`.**
**Commits (Fatia 4):** `c36ac88` T21 `semear_cobertura` · `5243d54` T22 fiação e2e + DOS-11 honesto
· `eb44d65` docs (AD-009, fecha TD-002, tasks) · `a91604b` T23 mata mutantes D/B + marca DOS-11
Verified. **Nada foi dado push** — só local (`main` está 34 commits à frente de `origin/main`).

**O que existe agora, além das Fatias 1/2/3:** `ingestao/cobertura.py::semear_cobertura` — deriva o
produto (município do lote × camada de restrição) de `lote_rural`/`restricao`/`proveniencia` num
único upsert SQL idempotente (`ON CONFLICT DO UPDATE`), sem loop Python. Chamado depois de
`materializar_intersecoes` e antes de `publicar_versao`, na mesma transação (cobertura só persiste
se a versão publicar). Decisão em **AD-009**. `montagem.py`/`geometria`/`dominio` **não mudaram uma
linha** — o Verifier confirmou no diff. Efeito visível: no dossiê real, APP/Reserva Legal saem de
"sem cobertura no município" e passam a trazer proveniência (fonte+data); UC/inundação/deslizamento/
corpo-d'água seguem honestamente marcadas sem cobertura (não ingeridas ainda).

---

**Handoff anterior (Fatia 3 — CAR como restrição):** Execute PASS (T15–T20), 111 passed. Detalhe
preservado no histórico de git; substituído acima ao fechar a Fatia 4.
**Commits (Fatia 3):** `fe2f2f4` design+tasks+TD-002 · `fd1ebc5` T16 ingestão CAR · `cf11559` T17
materialização · `db94e68` T18 `intersecoes_de` real · `0a7ffcc` T19 guarda publicação ·
`b095437` T20 prova e2e · `74eb62e` teste toque-de-borda (mata M2) + validation.md. A migração
`0003` foi commitada junto de `fe2f2f4`. **Nada foi dado push** — só local (`main` está 30 commits
à frente de `origin/main`).
**Escopo desta fatia:** SÓ o papel P1 de CAR — restrição (APP + Reserva Legal) cruzada com o lote,
materializada na ingestão. O papel P2 (CAR como segunda geometria/identidade, divergência SIGEF×CAR,
AD-003) foi **deliberadamente adiado** — decisão confirmada com o usuário no design (o handoff da
Fatia 2 descrevia "CAR = segunda geometria", mas isso conflitava com a priorização do `spec.md`).
**O que existe agora, além das Fatias 1/2:** `ingestao/restricao_car.py`
(`ingerir_app_car`/`ingerir_reserva_legal_car`, filtro `ind_status='AT'`, grava em `restricao`),
`ingestao/intersecoes.py` (`materializar_intersecoes` — spatial join SQL com índice GiST, idempotente
via `ON CONFLICT`), `RepositorioLotesPostGIS.intersecoes_de` agora lê `intersecao_materializada`
(fim do stub `[]`), `publicar.py` estende a guarda de 90% a `app`/`reserva_legal`. Schema `0003`
cria `restricao` + `intersecao_materializada`. `dossie/montagem.py`, `geometria/regras.py` e
`dominio/modelos.py` **não mudaram uma linha** — a lógica marginal <1% (DOS-08) foi reusada intacta,
provado pelo Verifier no diff.
**Dado real medido nesta sessão** (arquivos da Fase 0, antes nunca abertos): APP `APPS.zip` 416.927
feições (383.213 ativas), Reserva Legal `RESERVA-LEGAL.zip` 52.179 (47.348 ativas), ambos EPSG:4674.
Filtrar `ind_status='AT'` elimina 100% das duplicatas de `cod_imovel`. A ingestão real ainda não
rodou sobre esses arquivos de ~430k feições — só sobre fixtures sintéticas; ver Risk em `design.md`
sobre inserção em lote quando rodar no volume real.
**Tech debt:** **TD-002 RESOLVIDO nesta fatia** (Fatia 4, AD-009) — resta um concern menor herdado:
`cobertura` não é versionada e o passo só faz upsert, então um município que perca todos os lotes
numa reingestão mantém a linha antiga (staleness); aceito no MVP, anotado em TD-002. **TD-001**
(malha municipal, `municipio_em`) segue aberto — o caminho `SemLote`/DOS-04 continua quebrado contra
o adapter real; a Fatia 4 não dependeu dele (município vem do próprio `lote_rural`).
**Lição registrada:** `L-001` (`.specs/LESSONS.md`, status candidate) — testar toque-de-borda
área-zero em spatial join. (Fatia 4 gerou um padrão candidato adicional: ao materializar tabela por
upsert, testar explicitamente o *refresh* — `len` estável + ausência de erro NÃO provam que
`DO UPDATE` atualiza valores; `DO NOTHING` passaria. Registrar via `scripts/lessons.py` se recorrer.)
**Próximo passo:** **usuário pediu revisão de TODA a roadmap futura antes de escolher a próxima
fatia** (2026-09-04) — fazer isso primeiro. Candidatos remanescentes, para alimentar essa revisão:
(a) camada de inundação/deslizamento do INEA (AC#3, `grau_suscetibilidade`) — **fonte ainda NÃO
verificada**, exige Fase-0 por acesso real antes do código (lição da Fatia 5); mesmo padrão de
`restricao` + extensão do CHECK; força resolver TD-003 (mapa AC→DOS); (b) corpo d'água (INEA) —
idem, fonte não verificada; (c) camada urbana Niterói via SIGeo (82.199 feições, EPSG:31983) — o
seed de cobertura (Fatia 4) só cobre municípios *com lote rural*, então precisará estender
`semear_cobertura` para `lote_urbano`/municipal; (d) CAR papel P2 (divergência SIGEF×CAR, AD-003);
(e) malha municipal IBGE (fecha TD-001, destrava DOS-04); (f) fechar TD-003 (traceability DOS-09).
**Lição estrutural da Fatia 5:** o roadmap tratava "demais restrições INEA/ICMBio" como "mesmo
padrão, já pronto", mas **as fontes nunca foram verificadas** (só CAR/SIGEF/SIGeo estavam) — cada
nova camada de restrição carrega um custo de Fase-0 (achar endpoint, medir schema/CRS/contagem)
que o roadmap não precificava. A revisão de roadmap deve embutir esse custo por camada.

**Fase 0 — FECHADA, verificada por navegação real e dado real (2026-09-03):**
- **Egress `.gov.br` funciona na máquina local** (o bloqueio era do ambiente remoto). SIGEF 200,
  CAR 302, INCRA export_shp 200.
- **Piloto urbano confirmado por acesso real:** SIGeo Niterói expõe camada `Lotes` lote-a-lote —
  Feature Service `NGP_SMF_SEREC_A_LOTES_PUBLICO/FeatureServer/30`, **82.199 feições**, CRS nativo
  **EPSG:31983**, atributos cadastrais sem PII de proprietário, GeoJSON via `query`. Amostra
  validada (polígono 8 vértices, Caramujo). Pronto para prototipar ingestão real.
- **SIGEF — baixado e medido (2026-09-03):** login GOV.BR feito pelo usuário numa sessão de
  browser compartilhada (Playwright); export "Imóvel certificado SIGEF Total" filtrado por RJ.
  **14.664 feições, 100% Polygon, 0 inválidas/vazias/área-zero, CRS EPSG:4674** (bate com AD-008).
  Campos incluem `municipio_` (código IBGE) e `status` (`CERTIFICADA`); `.dbf` em encoding
  `latin1`. Detalhe completo em `fontes-de-dados-rj.md`. API ConectaGov existe mas é restrita a
  órgãos públicos, não serve para o projeto.
- **CAR — baixado e medido (2026-09-03):** captcha (imagem de texto) resolvido pelo usuário na
  sessão compartilhada; baixadas as 9 camadas do estado inteiro (~1 GB). Camada "Perímetros dos
  imóveis": **69.105 feições, CRS EPSG:4674**.
- **Sobreposição SIGEF × CAR medida de verdade (STRtree, 14.664 × 69.105 polígonos):** só **35,1%**
  dos imóveis CAR têm qualquer sobreposição espacial com um SIGEF certificado; entre os que
  sobrepõem, a mediana de cobertura é só **6,9%** (só 22,3% são pares quase idênticos >99%).
  **Confirma AD-003 empiricamente** — SIGEF e CAR realmente divergem na maioria dos casos; mostrar
  os dois lados sem reconciliar é a decisão certa, não cautela excessiva.
- **Licença SIGeo Niterói confirmada:** liberada, com atribuição obrigatória.
- **Dados brutos baixados ficam em `data/raw/rj/`** (fora do git, `.gitignore` cobre `data/raw/`,
  ~1,1GB, regeneráveis via navegação real). A ingestão real (Fatia 2) lê da fonte, não desses
  arquivos. Ver `data/raw/rj/README.md`.
- **Inventário urbano dos 92 municípios fechado:** 0 municípios (fora Niterói) com download
  vetorial de lote confirmado; 75 sem nenhuma fonte espacial aberta; 6 "Parcial" (WebGIS sem
  export, ex.: Macaé/GeoMacaé é o mais promissor) + 9 "Ambíguo" ainda precisam verificação manual
  direta (não bloqueia MVP, fica em `pendencias-humano.md` item 4). Detalhe e CSVs em
  `docs/research/municipios-rj/`.
- **`pendencias-humano.md` reduzido** — itens totalmente resolvidos (licença Niterói, download
  SIGEF, download CAR) foram removidos; só ficam ONR (futuro), revisão jurídica AD-002
  (pré-publicação), política de push, e verificação manual dos 15 municípios urbanos.

**Bloqueios conhecidos:** nenhum bloqueio de egress na máquina local. Fontes rurais exigem ação
humana pontual para baixar o arquivo (login gov.br p/ SIGEF; resolver captcha p/ CAR) — depois
disso a medição segue por agente. A camada urbana (Niterói) já está pronta para prototipar
ingestão real sem depender de ação humana adicional.
