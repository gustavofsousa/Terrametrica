# Mapa do Lote no RJ (F1.8 + F1.13) Specification

## Problem Statement

O painel (F1.11) é um mapa genérico: o usuário clica às cegas num basemap, recebe um pin solto e
nunca vê o contorno do lote que o dossiê descreve. O basemap vem de `tile.openstreetmap.org`, que a
política da OSMF proíbe em produto, e o painel está público desde a AD-014. O clique sem lote
quebra em produção (`municipio_em` levanta `NotImplementedError`, TD-001), e o clique fora do RJ
mostra "Erro inesperado — HTTP 422". Esta feature transforma o painel num mapa do estado do RJ que
mostra o lote, resolve o município e declara cada estado da consulta.

## Goals

- [ ] Clique num lote → o contorno do lote aparece no mapa e o painel mostra área e perímetro.
- [ ] Nenhuma requisição do produto vai para `tile.openstreetmap.org`.
- [ ] O mapa abre enquadrado no RJ, não sai do RJ e marca o que fica fora dele.
- [ ] Clique em qualquer ponto do RJ sem lote → nome do município + cobertura, nunca HTTP 500.
- [ ] A página de cobertura lista os 92 municípios do RJ pelo nome.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Camada de fundo com todos os lotes (PMTiles ou Martin + `ST_AsMVT`) | Exige infraestrutura para servir tiles. É decisão MACRO: abrir RFD própria quando o painel tiver uso |
| Busca por endereço / geocodificação | Nova fonte externa e novo fluxo; nenhum pedido de usuário hoje |
| Desenho da divergência SIGEF × CAR (dois perímetros) | É a F2.2 (v0.4) |
| Outros estados | AD-001: recorte só RJ, como experimento. Fora do RJ fica com menos detalhe; nada que já existe fora do RJ é retirado. A expansão (F4.5) só adiciona ingestão |
| Basemap auto-hospedado (Protomaps PMTiles) | OpenFreeMap basta no volume atual; revisitar com tráfego (ver Assumptions) |
| Migração do front para React | AD-012 continua: front vanilla, sem build step |
| Tema escuro | Nenhum pedido; o basemap claro (positron) não compete com o contorno do lote |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Motor do mapa | MapLibre GL JS `6.14.0` via `unpkg` ESM, sem build | Mantém a AD-012 (sem Node no deploy). Supersede só a linha "Leaflet + tiles OSM" da AD-012 — registrar AD nova no Design | y — padrão da skill, aceito 2026-10-14 |
| Basemap | OpenFreeMap, estilo `positron`, sem chave | Padrão da skill `web-map`. Sem SLA (doação): reverter custa trocar uma URL | y — padrão da skill, aceito 2026-10-14 |
| Onde vem a geometria do lote | Dentro da resposta `200`/`409` de `GET /dossie` | Um clique = uma requisição. Endpoint de tiles fica fora de escopo | y — padrão da skill, aceito 2026-10-14 |
| CRS da geometria devolvida | Coordenadas EPSG:4674 emitidas como GeoJSON sem reprojeção | SIRGAS 2000 e WGS84 diferem < 1 m; reprojetar não muda o que o usuário vê | y — padrão da skill, aceito 2026-10-14 |
| Precisão da geometria | 6 casas decimais (~0,1 m) | Limita o tamanho da resposta sem perda visível | y — padrão da skill, aceito 2026-10-14 |
| Fonte da malha municipal **[revised r1]** | `geobr.read_municipality(year=2025, code_muni=33, simplified=False)` | O projeto já usa geobr 2025 para `limite_estado`. Medido em 2026-10-14: na resolução completa a união dos 92 municípios é igual ao estado (diferença 0); na simplificada sobram ~25 km² de frestas | y — padrão da skill, aceito 2026-10-14 |
| Resolução e ano da malha **[revised r1]** | Resolução completa, ano 2025 (13,7 MB em GeoJSON para 92 feições) | Medido; o tamanho só pesa na carga, nunca no request | y — padrão da skill, aceito 2026-10-14 |
| Onde a malha vive | Tabela versionada sob o mesmo ponteiro atômico (AD-008) | O município de uma versão não pode vir de outra versão | y — padrão da skill, aceito 2026-10-14 |
| Chave do município | Código IBGE de 7 dígitos (texto), nunca o nome | Convenção atual de `lote_rural.municipios` e `lote_urbano.municipio` | y — convenção existente |
| Ponto na divisa entre municípios | `ST_Contains`, igual a `lote_em`: ponto exato na divisa → nenhum município | Mesma semântica de borda já testada no projeto; caso de medida zero para um clique | y — padrão da skill, aceito 2026-10-14 |
| UF como dimensão | Malha e contorno chaveados por UF (`33`), nunca fixos no código | Expandir para outro estado (F4.5) custa só ingestão, não redesenho | y — pedido do usuário, 2026-10-14 |
| Contorno do RJ no mapa | Derivado de `limite_estado` da versão publicada, simplificado | Dado já ingerido; não cria fonte nova | y — padrão da skill, aceito 2026-10-14 |
| Limite para "celular" | Viewport com largura ≤ 640 px | Corte comum de layout; ajustável sem mudar o requisito | y — padrão da skill, aceito 2026-10-14 |

**Open questions:** nenhuma. O usuário aceitou em 2026-10-14 os padrões recomendados pelas skills do plugin `maps`.
Qualquer troca que pede RFD volta para ele com prós e contras.

---

## Implicit-requirement dimensions

| Dimension | Resolution |
| --- | --- |
| Input validation & bounds | MAPA-13 (parâmetros de URL inválidos), MUN-05 (exatamente 92 municípios, código `33xxxxx`) |
| Failure / partial-failure states | MAPA-03 (basemap falhou), MAPA-18 (rede falhou), MUN-04 (ingestão incompleta não publica) |
| Idempotency / retry / duplicate handling | MUN-06 (reingerir a malha na mesma versão não duplica linhas) |
| Auth boundaries & rate limits | N/A because a feature não muda identidade nem cota: `GET /dossie` segue a AD-011/AD-014 e a rota do contorno do RJ é pública como `/cobertura/estado` |
| Concurrency / ordering | MAPA-11 (resposta de um clique antigo nunca sobrescreve a do clique novo) |
| Data lifecycle / expiry | MAPA-10 (geometria nunca entra no `consulta_log`); malha segue o ciclo de versão da base (AD-008) |
| Observability | MUN-04 (relatório da ingestão com contagem), N/A para o front because o projeto não tem telemetria de cliente |
| External-dependency failure | MAPA-03 (OpenFreeMap fora), MUN-04 (API do IBGE fora na carga — nunca no request, AD-004) |
| State-transition integrity | MAPA-11, MAPA-14 (seleção ↔ URL ↔ painel sempre consistentes) |

---

## User Stories

### P1: Basemap permitido e mapa focado no RJ ⭐ MVP

**User Story**: Como visitante do painel, quero um mapa do estado do RJ que carregue de forma legal
e estável, para saber onde o produto tem resposta.

**Why P1**: O basemap atual viola a política de uso da OSMF num painel público (AD-014) e pode ser
bloqueado sem aviso.

| ID | Requirement (WHEN / THEN) | Must not | Verification | Priority |
| --- | --- | --- | --- | --- |
| MAPA-01 | WHEN o painel carrega THEN o mapa SHALL usar MapLibre `6.14.0` com o estilo OpenFreeMap `positron` e mostrar a atribuição "© OpenStreetMap" e "OpenFreeMap" | fazer qualquer requisição a `tile.openstreetmap.org` | E2E: inspeção das requisições de rede no navegador | Required |
| MAPA-02 | WHEN o painel carrega THEN a câmera SHALL enquadrar o bbox do RJ | travar o arraste fora do RJ (a expansão para outros estados vem depois) | E2E: posição inicial | Required |
| MAPA-03 | WHEN o estilo do basemap falha ao carregar THEN o painel SHALL mostrar o aviso "Mapa base indisponível" | mostrar tela branca sem mensagem | E2E com a rota do estilo bloqueada | Required |
| MAPA-04 | WHEN o painel carrega THEN o mapa SHALL desenhar o contorno do RJ da versão publicada e SHALL atenuar a área fora dele (menos detalhe, mesmo basemap) | buscar o contorno numa fonte externa no request (AD-004) | Teste de API da rota do contorno + E2E visual | Required |
| MAPA-05 | WHEN o clique cai fora do RJ (HTTP 422) THEN o painel SHALL mostrar o estado `fora_do_rj` com o texto "Fora do estado do Rio de Janeiro" | mostrar "Erro inesperado" | `node --test` no view model (`dossie.js`) | Required |

**Independent Test**: abrir o painel com a rede inspecionada; nenhum host `tile.openstreetmap.org`;
o RJ ocupa a tela e o entorno aparece atenuado.

---

### P1: O lote clicado aparece no mapa ⭐ MVP

**User Story**: Como corretor ou comprador de terra, quero ver no mapa o contorno do lote do dossiê.
Assim confirmo que é o lote certo antes de confiar nos números.

**Why P1**: É a promessa do produto ("um clique no mapa, o dossiê do lote"). Se não há contorno, o
usuário não sabe se o dossiê é do lote que ele quer.

| ID | Requirement (WHEN / THEN) | Must not | Verification | Priority |
| --- | --- | --- | --- | --- |
| MAPA-06 | WHEN `GET /dossie` devolve 200 THEN o corpo SHALL conter `lote.geometria` como GeoJSON `Polygon`/`MultiPolygon` em ordem `[lon, lat]` com no máximo 6 casas decimais | mudar a área/perímetro calculados (seguem sobre `geography`) | Teste de integração da API contra PostGIS | Required |
| MAPA-07 | WHEN `GET /dossie` devolve 409 THEN cada candidato SHALL conter sua `geometria` | omitir a geometria de algum candidato | Teste de integração da API | Required |
| MAPA-08 | WHEN o painel recebe um 200 THEN o mapa SHALL desenhar o contorno e o preenchimento do lote como "selecionado" e SHALL enquadrar o lote com `padding` que não fica sob o painel | animar a câmera se `prefers-reduced-motion: reduce` | E2E: contorno visível + bbox do lote dentro da área livre | Required |
| MAPA-09 | WHEN o painel recebe um 200 THEN o painel SHALL mostrar a área (ha para rural, m² para urbano) e o perímetro em m | omitir a fonte e a data dessa área (AD-005) | `node --test` no view model | Required |
| MAPA-10 | WHEN uma consulta é registrada THEN o `consulta_log` SHALL guardar os mesmos campos de hoje | gravar geometria no `consulta_log` | Teste de integração existente do log | Required |
| MAPA-11 | WHEN o usuário clica de novo antes da resposta anterior chegar THEN o mapa e o painel SHALL mostrar só a resposta do último clique | deixar uma resposta antiga sobrescrever a nova | `node --test` do controlador de consultas com respostas fora de ordem | Required |
| MAPA-12 | WHEN o painel recebe um 409 THEN o mapa SHALL desenhar todos os candidatos com contornos distinguíveis e a lista SHALL destacar o candidato sob o cursor | desenhar os candidatos com o estilo de "selecionado" | E2E | Should |

**Independent Test**: clicar num lote SIGEF conhecido da fixture; o contorno aparece, o mapa
enquadra o lote e o painel mostra área em ha, perímetro e proveniência.

---

### P1: O clique sem lote resolve o município (F1.8, fecha TD-001) ⭐ MVP

**User Story**: Como visitante, quero saber em que município cliquei e que dado existe ali.
Isso vale também quando não há lote mapeado: quero ver a cobertura, não um erro.

**Why P1**: Hoje esse caminho quebra em produção com o adapter real (TD-001). Todo clique numa
área sem lote é uma falha visível.

| ID | Requirement (WHEN / THEN) | Must not | Verification | Priority |
| --- | --- | --- | --- | --- |
| MUN-01 | WHEN a carga da base roda THEN a ingestão SHALL gravar os 92 municípios do RJ (código IBGE + nome + geometria) na versão em construção | buscar a malha durante um request (AD-004) | Teste de integração da ingestão com fixture da malha | Required |
| MUN-02 | WHEN o clique cai no RJ e fora de qualquer lote THEN `municipio_em` SHALL devolver o código IBGE do município que contém o ponto | levantar `NotImplementedError` | Teste de integração contra PostGIS | Required |
| MUN-03 | WHEN `GET /dossie` devolve 404 THEN o corpo SHALL conter `municipio` (código), `municipio_nome` e a cobertura desse município, e o painel SHALL mostrar o nome | mostrar o código cru ao usuário | Teste de API + `node --test` no view model | Required |
| MUN-04 | WHEN a malha baixada não tem exatamente 92 municípios com código `33xxxxx` e geometria válida THEN a ingestão SHALL falhar com relatório de contagem e a versão SHALL NOT ser publicada | publicar uma versão com malha parcial | Teste de unidade com malha incompleta | Required |
| MUN-05 | WHEN a malha é ingerida THEN a proveniência SHALL citar "IBGE — Malha Municipal", o ano da malha, a data de extração e o SHA-256 do GeoJSON canônico (feições ordenadas por código) **[revised r1]** | gravar malha sem proveniência (AD-005) | Teste de integração | Required |
| MUN-06 | WHEN a malha é ingerida duas vezes na mesma versão THEN a tabela SHALL ter 92 linhas para essa versão | duplicar município | Teste de integração | Required |
| MUN-07 | WHEN `semear_cobertura` roda THEN a cobertura SHALL ter uma linha por município × camada para os 92 municípios, com `tem_dado=false` onde não há dado | deixar um município ausente da cobertura | Teste de integração | Required |
| MUN-08 | WHEN a página de cobertura carrega THEN ela SHALL listar os 92 municípios pelo nome, em ordem alfabética | mostrar código IBGE no lugar do nome | `node --test` em `cobertura.js` + teste de API | Required |
| MUN-09 | WHEN a migração da malha é revertida THEN o script de rollback SHALL remover só a tabela da malha, a coluna `proveniencia.sha256`, e as linhas da camada `municipio` em `proveniencia` e em `ponteiro_publicado`, e as versões publicadas anteriores SHALL continuar servindo `/dossie` 200 | apagar ou alterar `lote_rural`, `lote_urbano`, `restricao` ou as linhas de `ponteiro_publicado` das outras camadas | Teste de integração: migrar → reverter → `/dossie` de um lote conhecido | Required |

**Independent Test**: clicar no Centro da cidade do Rio de Janeiro (sem camada urbana, sem SIGEF); o painel mostra
"Nenhum lote neste ponto", o nome do município e a tabela de cobertura dele.

---

### P2: A seleção vive na URL

**User Story**: Como usuário, quero copiar o link do lote que estou vendo e mandar para outra
pessoa, para ela abrir o mesmo dossiê.

**Why P2**: Faz o dossiê circular (tese da v0.4) sem esperar o PDF da F2.1.

| ID | Requirement (WHEN / THEN) | Must not | Verification | Priority |
| --- | --- | --- | --- | --- |
| MAPA-13 | WHEN a página abre com `?lat=&lon=` válidos e dentro do bbox do RJ THEN o painel SHALL consultar esse ponto e enquadrar o resultado; WHEN os parâmetros são inválidos ou fora do bbox THEN o painel SHALL ignorá-los | fazer request com parâmetros inválidos | `node --test` do parser de URL + E2E | Should |
| MAPA-14 | WHEN o usuário clica num ponto THEN a URL SHALL mudar para `?lat=&lon=` (6 casas) via `history.replaceState`; WHEN o usuário aperta Esc THEN a seleção, o contorno e os parâmetros SHALL ser removidos | criar uma entrada de histórico por clique | E2E | Should |

**Independent Test**: clicar num lote, copiar a URL, abrir em aba nova; o mesmo lote aparece
selecionado.

---

### P2: O painel funciona no celular

**User Story**: Como corretor em campo, quero consultar um lote pelo celular, para checar antes de
uma visita.

**Why P2**: Uso em campo é o caso real da persona; o layout atual divide a tela em duas colunas.

| ID | Requirement (WHEN / THEN) | Must not | Verification | Priority |
| --- | --- | --- | --- | --- |
| MAPA-15 | WHEN a largura da viewport é ≤ 640 px THEN o painel SHALL virar uma folha inferior (bottom sheet) com no máximo 50% da altura e o mapa SHALL ocupar a largura inteira | cobrir o lote selecionado com a folha (o enquadramento usa `padding` inferior) | E2E com viewport 390×844 | Should |
| MAPA-16 | WHEN a folha inferior está aberta THEN o mapa SHALL continuar recebendo cliques e gestos na área visível | bloquear o mapa com uma camada invisível | E2E com toque simulado | Should |

**Independent Test**: abrir num viewport de celular, tocar num lote; o contorno aparece acima da
folha e a folha mostra o dossiê.

---

### P2: Estados de espera, erro e acessibilidade

**User Story**: Como usuário, quero saber sempre o que o mapa está fazendo, para não clicar de novo
nem achar que quebrou.

**Why P2**: Hoje o erro de rede some no painel e o mapa não dá sinal de espera.

| ID | Requirement (WHEN / THEN) | Must not | Verification | Priority |
| --- | --- | --- | --- | --- |
| MAPA-17 | WHEN uma consulta está em andamento THEN o painel SHALL ter `aria-busy="true"` e mostrar "Consultando o lote…" | manter o contorno do lote anterior como "selecionado" durante a espera | `node --test` + E2E | Should |
| MAPA-18 | WHEN a consulta falha por rede THEN o painel SHALL mostrar a mensagem de falha e um botão "Tentar de novo" que repete o mesmo ponto | perder o ponto clicado | E2E com a API bloqueada | Should |
| MAPA-19 | WHEN um resultado chega THEN o foco SHALL ir para o título do painel e a região SHALL ser anunciada (`aria-live`) | roubar o foco durante o arraste do mapa | E2E com leitura da árvore de acessibilidade | Could |

**Independent Test**: bloquear a API no navegador e clicar; aparece a falha com "Tentar de novo";
liberar a API e clicar no botão; o dossiê aparece.

---

### P3: A documentação reflete o produto real

**User Story**: Como pessoa nova no projeto, quero que o README descreva o que já existe, para não
ler "zero código HTTP" num projeto com API e deploy.

| ID | Requirement (WHEN / THEN) | Must not | Verification | Priority |
| --- | --- | --- | --- | --- |
| DOC-01 | WHEN a feature fecha THEN a seção "Estado atual" do README SHALL listar a API, o painel, a página de cobertura, o deploy (AD-013) e esta feature | manter a frase "camada HTTP/API … zero código" | Revisão manual | Could |

---

## Edge Cases

- WHEN o clique cai no mar dentro do contorno do RJ e fora de todo município THEN o 404 SHALL trazer `municipio: null`.
  O painel SHALL mostrar "Ponto fora de município mapeado".
- WHEN o lote é um `MultiPolygon` com partes distantes THEN o enquadramento SHALL cobrir todas as partes.
- WHEN o lote tem área menor que um pixel no zoom atual THEN o enquadramento SHALL aproximar até o zoom máximo do estilo.
- WHEN o lote é o maior do SIGEF RJ (2.301 vértices, 55 KB em GeoJSON, medido) THEN a resposta SHALL trazer a geometria completa, sem simplificar. **[revised r1]**
- WHEN o usuário arrasta o mapa (sem clique) THEN nenhuma consulta SHALL ser feita.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| MAPA-01..05 | P1: Basemap e foco no RJ | Specify | Pending |
| MAPA-06..12 | P1: Lote no mapa | Specify | Pending |
| MUN-01..09 | P1: Município (F1.8, TD-001) | Specify | Pending |
| MAPA-13..14 | P2: URL | Specify | Pending |
| MAPA-15..16 | P2: Celular | Specify | Pending |
| MAPA-17..19 | P2: Espera, erro, a11y | Specify | Pending |
| DOC-01 | P3: README | Specify | Pending |

**Coverage:** 29 total, 0 mapped to tasks, 29 unmapped ⚠️ (Tasks phase pending)

**Revisions:** r1 (2026-10-14, Design) — fonte da malha, forma do SHA-256 e o caso de geometria grande mudaram após medir as fontes. Nenhuma garantia ficou mais fraca.

**Supersedes:** a linha "desenhar a geometria do lote no mapa — fora de escopo" da spec
`painel-web-conta` e da spec `lote-urbano-niteroi`.

---

## Success Criteria

- [ ] Zero requisições a `tile.openstreetmap.org` numa sessão E2E completa.
- [ ] 100% dos cliques em lote da fixture desenham o contorno do lote retornado.
- [ ] Zero HTTP 500 em `/dossie` para pontos dentro do RJ (o caminho TD-001 fecha).
- [ ] A página de cobertura lista 92 municípios pelo nome.
- [ ] O fluxo clique → contorno → dossiê funciona num viewport de 390×844.
