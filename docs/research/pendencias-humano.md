# Pendências que exigem ação humana

> Itens da Fase 0 (e correlatos) que não dão para fechar por agente — exigem login, contato
> humano, decisão de negócio/jurídica, ou navegação manual em portal sem API. Atualizado conforme
> a Fase 0 avança; ver checklist completa em `docs/research/fontes-de-dados-rj.md`.

## 1. Confirmar licença/termos de uso do SIGeo Niterói

**Link:** [dados-geoniteroi.opendata.arcgis.com](https://dados-geoniteroi.opendata.arcgis.com/) ·
página oficial [sigeo.niteroi.rj.gov.br](https://www.sigeo.niteroi.rj.gov.br/)

**O quê:** o Feature Service `Lotes` (`NGP_SMF_SEREC_A_LOTES_PUBLICO/FeatureServer/30`) foi
verificado por acesso real — 82.199 feições, sem PII — mas os **termos de uso/licença de
redistribuição** não estão no payload da API. Precisa checar a página do dataset no ArcGIS Hub.
**Por quê importa:** AD-004 monta base própria (baixa, valida, materializa) — se a licença
restringir redistribuição/uso comercial, muda a estratégia de ingestão dessa camada.
**Ação:** abrir o link do dataset no navegador, ler a seção de licença/termos, colar aqui o
resultado (ou uma captura) para eu registrar em `fontes-de-dados-rj.md`.

## 2. Contatar ONR sobre API para terceiros

**Link:** [registrodeimoveis.org.br](https://www.registrodeimoveis.org.br/) (site do ONR — canal
de contato/atendimento fica lá)

**O quê:** confirmar se o Operador Nacional de Registro (ONR/SREI) tem alguma via de integração
programática para consulta de certidão, ou se é 100% manual por portal.
**Por quê importa:** é o único caminho técnico-jurídico que poderia, no futuro, sustentar a camada
de proprietário (hoje fora do MVP por AD-002). Sem isso confirmado, a camada de proprietário
permanece bloqueada por design — não é código faltando, é decisão jurídica pendente.
**Ação:** contato institucional (e-mail/atendimento do ONR) perguntando sobre API de terceiros
para consulta de certidão/matrícula. Não é algo que um agente possa fazer.

## 3. Validar a interpretação jurídica de AD-002 com um advogado

**O quê:** AD-002 se apoia em leitura própria da Lei 6.015/73 art. 17 (publicidade registral) e da
LGPD sobre agregação de dado público. É uma leitura razoável, mas não é parecer jurídico.
**Por quê importa:** é a decisão que mais expõe o produto a risco regulatório se a camada de
proprietário for ligada um dia (ver `docs/produto/riscos.md`, risco jurídico alto).
**Ação:** revisão por advogado antes de qualquer código que toque dado de proprietário — mesmo
que isso só aconteça bem depois do MVP. Sem link — é uma consulta offline.

## 4. Push dos commits locais para o remoto

**O quê:** a branch `main` está à frente de `origin/main` (inclui os commits de verificação da
Fase 0 de hoje). Eu não faço push sem pedido explícito.
**Ação:** `git push` quando você quiser publicar. Aviso: nenhum desses commits é destrutivo, é
seguro fazer a qualquer momento.

## 5. Baixar shapefile SIGEF (Acervo Fundiário RJ) — precisa login GOV.BR

**Link:** [certificacao.incra.gov.br/csv_shp/export_shp.py](https://certificacao.incra.gov.br/csv_shp/export_shp.py)
(pede login GOV.BR na hora) · página do dataset em
[dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/sistema-de-gestao-fundiaria---sigef)

**O quê:** confirmado por navegação real (2026-09-03) que o dataset SIGEF é **ACESSO PÚBLICO,
licença CC-BY**, mas o recurso SHP exige login via SSO `sso.acesso.gov.br` — **qualquer conta
gov.br de cidadão comum serve**, não é credencial institucional.
**Por quê importa:** é o primeiro item pendente da checklist de Fase 0 (medir nº de feições, CRS,
validade dos polígonos do SIGEF filtrado por RJ) — pré-requisito antes de escrever código de
ingestão rural.
**Ação:** abrir o link, logar com sua conta gov.br, filtrar por RJ, baixar o shapefile e me passar
o arquivo (ou o caminho local) para eu medir feições/CRS/validade.

## 6. Baixar shapefile CAR (Perímetros dos imóveis, RJ) — precisa resolver reCAPTCHA

**Link:** [consultapublica.car.gov.br/publico/estados/downloads](https://consultapublica.car.gov.br/publico/estados/downloads)
(sem login)

**O quê:** confirmado por navegação real (2026-09-03) que a página acima **não exige login** e
lista RJ com dado fresco (disponibilizado 03/09/2026). O modal de download por camada (Perímetros
dos imóveis, APP, Reserva Legal etc.) é protegido por **reCAPTCHA por clique** — não tentei
contornar, é controle anti-bot legítimo.
**Por quê importa:** é o segundo item pendente da checklist de Fase 0 — preciso do perímetro CAR
de RJ para medir a sobreposição SIGEF × CAR (AD-003, o achado de maior valor do produto).
**Ação:** no link acima, clicar RJ → "Perímetros dos imóveis" → Download, resolver o captcha,
baixar o shapefile e me passar o arquivo para eu medir a sobreposição.

## 7. Inventário dos 92 municípios (cobertura urbana)

**O quê:** levantar quais dos 91 municípios restantes (fora Niterói) publicam lote cadastral
aberto, e em qual formato/via.
**Por quê importa:** é o maior ponto cego do produto (AD-006 já assume que a maioria não publica).
**Por que fica aqui e não é 100% automatizável:** dá para automatizar parte (varrer ArcGIS Online
por prefeitura), mas boa parte dos portais municipais do RJ não tem API — exige navegação manual
página a página. Posso rodar a varredura automatizável como próximo passo técnico separado; a
parte manual (sites sem padrão, PDFs, portais quebrados) precisa de alguém revisando.
**Ação sugerida:** eu rodo uma primeira varredura automatizada (ArcGIS Online + busca por
"prefeitura + cadastro + lote" por município) e te devolvo uma planilha de triagem; você confirma
os casos ambíguos.
