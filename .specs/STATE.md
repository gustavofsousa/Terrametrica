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

## Handoff

**Branch:** `main`
**Fase atual:** Execute concluído para a **Fatia 3 — CAR como camada de restrição (APP + Reserva
Legal)** (`tasks.md`, seção Fatia 3, T15–T20). Validação **PASS** por Verifier independente (author
≠ verifier, worktree isolado) registrada em `.specs/features/dossie-lote-rj/validation.md` (seção
Fatia 3): gate verde (ruff 0, mypy strict 0, 111 passed — +17 vs baseline 94), sensor 3/4 mutantes
mortos na 1ª rodada; o 4º sobrevivente (M2, `area_m2 > 0` do `intersecoes.py`) foi fechado com um
teste de toque-de-borda área-zero (confirmado matar o mutante). DOS-07 e DOS-08 marcados
`✅ Verified` em `spec.md`.
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
**Tech debt:** TD-001 (malha municipal, `municipio_em`) segue aberto — não era necessário nesta
fatia (município vem do `cod_imovel`). **TD-002 aberto nesta fatia** — `cobertura` nunca é semeada
por nenhuma ingestão, então toda seção de restrição aparece "sem cobertura no município" (DOS-11)
mesmo com dado ingerido; pré-existente (nem SIGEF semeia), não regressão. Fechar antes do painel web.
**Lição registrada:** `L-001` (`.specs/LESSONS.md`, status candidate) — testar toque-de-borda
área-zero em spatial join, o teste de "sem sobreposição" com polígonos disjuntos não cobre isso.
**Próximo passo:** candidatos para a próxima fatia, em ordem de valor: (a) demais camadas de
restrição do INEA/ICMBio (UC, inundação, deslizamento, corpo d'água) — mesmo padrão de `restricao`,
fecha o resto das ACs de "Restrições ambientais"; (b) seed de `cobertura` (fecha TD-002, destrava
DOS-11 honesto); (c) camada urbana Niterói via SIGeo (82.199 feições, EPSG:31983, reprojeção nova);
(d) CAR papel P2 (divergência SIGEF×CAR, AD-003); (e) malha municipal IBGE (fecha TD-001). Sem
bloqueio técnico em nenhuma.

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
