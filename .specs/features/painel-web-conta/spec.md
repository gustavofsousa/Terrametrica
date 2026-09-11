# Painel Web + Conta Autenticada (F1.11) Specification

## Problem Statement

O motor do dossiê roda fim-a-fim e tem superfície HTTP (F1.10: `GET /dossie`, `/cobertura`,
`/saude`), mas nenhum usuário real consegue vê-lo — a identidade hoje é um header opaco
`X-Conta-Id` que qualquer chamador informa sem prova, e não existe interface visual. F1.11 fecha
essa lacuna: um painel web onde a pessoa faz login, clica no mapa e recebe o dossiê do lote,
autenticada por uma conta real pela primeira vez no produto.

## Goals

- [ ] Uma pessoa sem cadastro prévio consegue logar via e-mail (magic link) e chegar ao mapa em
      menos de 2 minutos, sem preencher formulário de cadastro separado.
- [ ] O clique no mapa autenticado retorna o dossiê do lote (via `GET /dossie` existente) e exibe
      seus campos — lote, restrições, proveniência, ressalvas — em um painel lateral.
- [ ] Zero dado pessoal novo persistido além do e-mail necessário para o login (mantém GATE-06:
      `Conta` não carrega nome/CPF/CNPJ).
- [ ] A identidade de sessão do painel substitui o `X-Conta-Id` manual como a via real de uso da
      API: `consulta_log.usuario_id` (DOS-30) e a cota (DOS-27) passam a chavear por uma conta que
      nasceu de um login de verdade, não de um valor arbitrário informado no header.

## Out of Scope

Explicitamente excluído. Documentado para prevenir scope creep.

| Feature | Reason |
| --- | --- |
| Senha / OAuth social / gov.br | Decisão do usuário: magic link por e-mail é o único mecanismo desta feature (AD-011 já citava "sessão/OAuth/gov.br" como opções futuras — ficam fora). |
| Better Auth (lib) | Avaliado e descartado: é TS/Node, o backend é 100% Python; trazer um segundo runtime só para magic link + sessão não se paga frente a implementar ~150-200 linhas em Python puro reusando a fronteira `Conta`/`ContaId` já existente. |
| Página de cobertura pública (HTML) | É F1.12, depende de F1.4 + F1.10, feature separada no roadmap. |
| Exportação em PDF do dossiê | É F2.1 (Fase 2), fora desta fatia. |
| Gate jurídico / promoção de papel / dado registral | É F2.3 / F3.x. O papel da conta nasce sempre `CONSULTA`; a fronteira `PapelConta`/`Conta` já modelada (AD-002/GATE) não é tocada por esta feature. |
| Geometria do lote/restrições desenhada no mapa | Decisão do usuário: o painel exibe os campos do dossiê em card/painel lateral; overlay de polígono no mapa fica para uma fatia futura. |
| Migração de contas/dados pré-existentes | Decisão do usuário: os `conta_id` usados até agora são só de teste/e2e da API (F1.10); a tabela de contas nasce vazia. |
| Recuperação de conta / troca de e-mail / exclusão de conta | Não há senha a recuperar (magic link já é o mecanismo de recuperação de acesso); troca/exclusão de e-mail fica para quando houver demanda real. |
| Multi-sessão / listagem de sessões ativas / logout remoto | MVP: sessão única por cookie, sem painel de gerenciamento de sessões. |
| Rate limit de tráfego autenticado (100/h) | Já existe (F1.10/AD-011) e não muda nesta feature — só a origem da identidade muda (sessão real em vez de header manual). |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica silenciosamente indefinido.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Mecanismo de auth | Magic link por e-mail, sem senha | Decisão do usuário; menor superfície de ataque, sem storage de hash de senha | y |
| Stack de auth | Python puro na API FastAPI existente (sem Better Auth) | Better Auth exigiria runtime Node só para isso; Python puro reusa `Conta`/`ContaId` e evita segundo deploy | y |
| Arquitetura do painel | ~~SPA separado (React/Vite)~~ → **front vanilla estático (Leaflet), evoluindo `prototipos/mapa-dossie/`** — consome a API Python via `fetch` | Superseded por **AD-012**: React/Vite traz o mesmo 2º runtime Node que a spec rejeitou para o auth (linha 30/58); F1.11 tem 4 estados de UI e o protótipo já entrega o layout. React fica para F1.12+ se a UI ficar rica. | y (revisado 2026-09-10, AD-012) |
| Cookie de sessão | httpOnly, `SameSite=Lax`, `Secure`, domínio pai compartilhado (ex: painel em `app.terrametrica.xyz`, API em `api.terrametrica.xyz`, cookie com `Domain=.terrametrica.xyz`) | Evita `SameSite=None` (mais exposto a CSRF); exige só planejar subdomínios no deploy | y |
| Duração da sessão | 30 dias | Baixa fricção para uso esporádico do painel (consulta de lote não é diária) | y |
| Expiração do magic link | 15 minutos, uso único | Janela curta o suficiente para não sobrar em caixas de e-mail, longa o suficiente para abrir com calma; uso único invalida no primeiro clique | y |
| Rate limit de solicitação de magic link | 5 por hora por e-mail | Cobre reenvio legítimo sem abrir brecha de spam/bomba de e-mail contra terceiros; chaveado por e-mail (não por conta — ainda não existe conta antes do primeiro login) | y |
| Provedor de e-mail | Resend, atrás de uma porta/adapter fina (`EnviadorEmail` protocol) | API simples, bom free tier para MVP; porta fina permite trocar depois sem tocar o fluxo de auth (mesma filosofia de `RepositorioContas`/`LogAuditoria`) | y |
| Cadastro implícito | Conta é criada automaticamente no primeiro clique de um e-mail nunca visto, papel nasce `CONSULTA` | Sem paywall, sem dado pessoal a coletar (GATE-06 já garante isso na struct `Conta`) — não há nada que um passo de cadastro separado agregaria | y |
| Onde o e-mail vive | Tabela própria `credencial_login` (`email` → `conta_id`), fora da struct `Conta` do domínio | `Conta` (GATE-06) foi desenhada de propósito sem campo capaz de carregar PII — e-mail é PII mesmo sem CPF/nome. Isolar em `credencial_login` mantém essa garantia estrutural intacta; o módulo de auth é o único que lida com PII de login, o domínio do gate jurídico não muda | y |
| Better Auth vs Python puro (exceção ao kit-base) | Python puro, exceção registrada em `decisoes.md` do kit | Better Auth exigiria um 2º runtime (Node) só para magic link + sessão, faria o schema de contas nascer em outro sistema (colidindo com `Conta`/GATE-06) e acoplaria o gate jurídico (F2.3) a uma chamada de rede para saber o papel de uma conta. Nenhum recurso que justifica Better Auth (social login, 2FA, orgs/multi-tenancy) está no escopo do F1.11 ou no roadmap atual — revisitar se multi-tenancy virar requisito real | y |
| Migração de identidade existente | Tabela de contas nasce vazia | Os `conta_id` usados até agora (F1.10) foram só de teste/e2e da API, nada real para migrar | y |
| Escopo de UI do dossiê no painel | Painel lateral/card com os campos do DTO existente (`dossie_para_dict`); sem overlay de geometria no mapa | Decisão do usuário; geometria não está no DTO hoje e adicioná-la é escopo de uma fatia futura | y |
| Prefixo de requisito | `PAINEL-NN` (não `DOS-NN`) | F1.11 é uma feature nova de superfície (auth + UI), distinta da árvore de decisão do dossiê que os `DOS-NN` rastreiam; evita colisão com a numeração de `dossie-lote-rj` (até DOS-30) | y |
| E-mail inválido / malformado na solicitação de link | 422 com mensagem genérica, sem revelar se o e-mail já tem conta | Consistente com `ErroValidacao` no boundary (AD já usado em `Coordenada`); não vazar existência de conta evita enumeração de e-mails | y |
| O que acontece ao clicar um magic link expirado ou já usado | 401 com mensagem "link inválido ou expirado", sem indicar qual dos dois motivos (evita oracle de timing/enumeração) | Mesma lógica de não vazar detalhes de auth que ajudem enumeração | y |
| Logout | Endpoint que invalida a sessão corrente (apaga cookie + registro de sessão no servidor) | Necessário mesmo em MVP — sem isso, sessão de 30 dias em dispositivo compartilhado não pode ser encerrada pelo usuário | y |

**Open questions:** nenhuma — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Login por magic link ⭐ MVP

**User Story**: Como pessoa interessada em consultar um lote, quero entrar no painel informando
só meu e-mail, para não precisar criar senha nem preencher cadastro.

**Why P1**: Sem login não há conta real, e sem conta real não há sessão para o mapa consumir — é
o pré-requisito de tudo o mais nesta feature.

**Acceptance Criteria**:

1. WHEN a pessoa informa um e-mail válido na tela de login THEN o sistema SHALL gerar um token de
   login opaco, associá-lo ao e-mail com expiração de 15 minutos e uso único, e enviar um e-mail
   contendo um link com esse token via Resend.
2. WHEN a pessoa informa um e-mail malformado THEN o sistema SHALL responder `422` com mensagem
   genérica de validação, sem tentar enviar e-mail.
3. WHEN a pessoa clica um link de login válido (dentro da janela de 15 min, ainda não usado) THEN
   o sistema SHALL: (a) se o e-mail já tem conta, autenticar essa conta; (b) se o e-mail nunca foi
   visto, criar uma conta nova com papel `CONSULTA`; em ambos os casos, invalidar o token, criar
   uma sessão de 30 dias e setar um cookie httpOnly/`Secure`/`SameSite=Lax` no domínio pai.
4. WHEN a pessoa clica um link de login expirado ou já usado THEN o sistema SHALL responder `401`
   com mensagem "link inválido ou expirado", sem indicar qual das duas causas.
5. WHEN o mesmo e-mail solicita mais de 5 magic links dentro de 1 hora THEN o sistema SHALL
   responder `429` para a 6ª solicitação em diante, sem enviar e-mail adicional.
6. WHEN a pessoa acessa o painel sem cookie de sessão válido THEN o sistema SHALL redirecionar
   para a tela de login.

**Independent Test**: Solicitar magic link para um e-mail novo, capturar o token (ambiente de
teste), acessar o link, confirmar que uma conta com papel `CONSULTA` existe e o cookie de sessão
foi setado — sem tocar no mapa.

---

### P1: Mapa autenticado → dossiê no painel ⭐ MVP

**User Story**: Como conta autenticada, quero clicar num ponto do mapa e ver o dossiê daquele
lote num painel lateral, para entender as restrições sem chamar a API manualmente.

**Why P1**: É a razão de existir do painel — dar rosto visual ao motor que já funciona via API
(F1.10). Sem isso, F1.11 seria só uma tela de login sem destino.

**Acceptance Criteria**:

1. WHEN uma conta autenticada clica um ponto no mapa THEN o sistema SHALL chamar `GET /dossie`
   com esse `lat`/`lon`, autenticado pela sessão (a API resolve `conta_id` a partir da sessão, não
   mais exigindo o header `X-Conta-Id` manual do cliente do painel).
2. WHEN a resposta é `200` (tipo `dossie`) THEN o painel SHALL exibir, num painel lateral: dados
   do lote, lista de restrições, proveniência de cada campo e a `ressalva`, usando os campos já
   presentes em `dossie_para_dict` (sem desenhar geometria no mapa).
3. WHEN a resposta é `404` (tipo `sem_lote`) THEN o painel SHALL exibir a mensagem retornada e a
   lista de cobertura do município, sem quebrar a interação com o mapa.
4. WHEN a resposta é `409` (tipo `sobreposicao`) THEN o painel SHALL exibir a mensagem e a lista
   de lotes candidatos retornada pela API.
5. WHEN a resposta é `429` (cota excedida) THEN o painel SHALL exibir a mensagem de cota e o tempo
   de espera (`retry_after_segundos`) sem travar a UI.
6. WHEN a sessão expira ou é inválida durante o uso do painel THEN uma chamada a `/dossie` SHALL
   retornar `401` e o painel SHALL redirecionar para a tela de login.

**Independent Test**: Com uma sessão válida, clicar um ponto conhecido do dataset de teste (lote
existente) e conferir que o painel lateral mostra os mesmos campos que uma chamada direta a
`GET /dossie` com o `X-Conta-Id` de teste retornaria.

---

### P2: Logout

**User Story**: Como conta autenticada, quero encerrar minha sessão explicitamente, para não
deixar acesso ativo em um dispositivo compartilhado.

**Why P2**: Importante para higiene de sessão, mas não bloqueia a demonstração do valor central
(login → mapa → dossiê) da P1.

**Acceptance Criteria**:

1. WHEN uma conta autenticada aciona "sair" THEN o sistema SHALL invalidar a sessão no servidor e
   expirar o cookie no cliente.
2. WHEN uma sessão já invalidada é reapresentada em uma chamada autenticada THEN o sistema SHALL
   responder `401` como se a sessão nunca tivesse existido.

**Independent Test**: Logar, acionar logout, tentar clicar no mapa novamente e confirmar
redirecionamento para login.

---

## Edge Cases

- WHEN a pessoa solicita magic link para um e-mail que nunca existiu e nunca clica o link THEN o
  sistema SHALL não criar conta nenhuma (conta só nasce na confirmação do clique, ACtoP1-3).
- WHEN dois magic links são solicitados em sequência para o mesmo e-mail (ex: usuário clicou
  "reenviar") THEN o clique em qualquer um dos dois tokens ainda não expirados/usados SHALL
  autenticar normalmente; o outro token SHALL continuar válido até expirar por tempo ou ser usado
  (nenhuma invalidação cruzada implícita nesta fatia).
- WHEN o provedor de e-mail (Resend) falha ao enviar THEN o sistema SHALL responder `502`/erro
  explícito ao invés de `200` silencioso — a pessoa não deve pensar que um e-mail está a caminho
  se o envio falhou.
- WHEN o cookie de sessão está presente mas corrompido/inválido (não corresponde a nenhuma sessão
  ativa) THEN o sistema SHALL tratar como não autenticado (`401`/redirect), nunca levantar erro
  5xx.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PAINEL-01 | P1: Login por magic link | Execute | Verified |
| PAINEL-02 | P1: Login por magic link (e-mail malformado → 422) | Execute | Verified |
| PAINEL-03 | P1: Login por magic link (confirmação cria/autentica conta) | Execute | Verified |
| PAINEL-04 | P1: Login por magic link (token expirado/usado → 401) | Execute | Verified |
| PAINEL-05 | P1: Login por magic link (rate limit 5/h por e-mail) | Execute | Verified |
| PAINEL-06 | P1: Login por magic link (sem sessão → redirect) | Execute | Verified |
| PAINEL-07 | P1: Mapa autenticado → dossiê (chamada autenticada) | Execute | Verified |
| PAINEL-08 | P1: Mapa autenticado → dossiê (render 200 dossiê) | Execute | Verified |
| PAINEL-09 | P1: Mapa autenticado → dossiê (render 404 sem_lote) | Execute | Verified |
| PAINEL-10 | P1: Mapa autenticado → dossiê (render 409 sobreposicao) | Execute | Verified |
| PAINEL-11 | P1: Mapa autenticado → dossiê (render 429 cota) | Execute | Verified |
| PAINEL-12 | P1: Mapa autenticado → dossiê (sessão expira → redirect) | Execute | Verified |
| PAINEL-13 | P2: Logout (invalida sessão) | Execute | Verified |
| PAINEL-14 | P2: Logout (sessão invalidada → 401) | Execute | Verified |

**ID format:** `PAINEL-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 14 total, 14 mapped to tasks (T1–T10), 0 unmapped ✅ (ver `tasks.md` §Requirement Coverage)

---

## Success Criteria

Como saberemos que a feature foi bem-sucedida:

- [ ] Uma pessoa sem conta prévia consegue ir de "nunca ouviu falar do produto" a "vendo o dossiê
      de um lote no painel" sem preencher formulário de cadastro, senha, ou pagar nada.
- [ ] `consulta_log.usuario_id` e a cota de 100/h passam a ser alimentados por sessões reais do
      painel (a via `X-Conta-Id` manual continua existindo para outros clientes de API, mas o
      painel não a usa mais diretamente — usa cookie de sessão).
- [ ] Zero regressão em `GET /dossie`/`/cobertura`/`/saude` (F1.10): a superfície e o contrato
      existentes não mudam, só ganham uma forma adicional de resolver `conta_id` (sessão, além do
      header).
- [ ] `Conta` continua sem campo de nome/CPF/CNPJ (GATE-06 intacto) — o e-mail vive na tabela
      `credencial_login`, separada da fronteira do gate jurídico, não dentro de `Conta`.
