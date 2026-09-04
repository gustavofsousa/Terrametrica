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

## Handoff

**Branch:** `main`
**Fase atual:** Execute concluído para a **Fatia 2 — adaptador PostGIS + ingestão SIGEF (walking
skeleton)** (`tasks.md`, seção Fatia 2, T6–T14). Validação PASS registrada em
`.specs/features/dossie-lote-rj/validation.md` (seção Fatia 2): gate verde (ruff 0, mypy strict 0,
94 passed — 30 de integração), sensor de discriminação 3/3 mutantes mortos.
**Commits (Fatia 2):** `7409f9f` design+tasks · `6bbc532` T6 infra dev · `e7848b5` T7 schema ·
`745f0a0` T8 conexão/migração · `d62ef3d`+`195321a` T9 adapter lotes · `1de5056` T10 adapter limite
· `6f26078` T11 ingestão limite RJ (geobr) · `1209f09` T12 ingestão SIGEF · `4fed269` T13
publicação c/ guarda+swap · `fb27b20` T14 prova e2e · `a8e2037`/`2687fba`/`1770a98` docs/validação.
Nada pendente de commit no código da Fatia 2. **Nada foi dado push** — só local.
**O que existe agora, além da Fatia 1:** `persistencia/` (conexão psycopg, runner de migração
idempotente, schema SQL 0001+0002, adapters reais `RepositorioLotesPostGIS`/`LimiteEstadoPostGIS`
implementando os *ports* de T4 sem mudá-los) e `ingestao/` (`limite_rj.py` via geobr real,
`sigef.py` a partir de arquivo local, `publicar.py` com guarda de 90%+swap atômico,
`tipos.py`/`validacao_geometria.py` compartilhados). `montar_dossie` (T5) roda sem nenhuma mudança
sobre os adapters reais — prova que os *ports* isolaram fake↔real (T14).
**Recorte desta fatia:** só SIGEF (rural). CAR, camada urbana (Niterói/SIGeo), qualquer camada de
restrição e `intersecao_materializada` ficam fora — decisão explícita pra provar o pipeline
fim-a-fim antes de somar fontes.
**Tech debt aberto:** `.specs/TECH-DEBT.md` TD-001 — `municipio_em` levanta `NotImplementedError`
(sem malha municipal IBGE nesta fatia); `lote_rural.municipios` guarda código IBGE bruto, não
nome. Revisitar quando a malha municipal entrar (provavelmente junto de CAR ou camada urbana).
**Gaps não-bloqueantes registrados no Verifier:** DOS-04 (`SemLote`) sem cobertura real (cai em
TD-001); DOS-26 (idempotência) não é asserido por execução dupla nesta fatia — nenhum dos dois
consta nos "Done when" de T6-T14, ver `validation.md` seção Fatia 2 para detalhe.
**Achado operacional:** houve uma sessão concorrente de outro Claude Code no mesmo repo durante
esta execução (feature `gate-juridico-p2`/`autorizacao`, commits intercalados). Sem conflito —
cada sessão só tocou seus próprios arquivos — mas vale checar com o usuário se as duas frentes
foram coordenadas.
**Próximo passo:** Fatia 3 — candidatos, em ordem de valor: (a) CAR (segunda geometria do lote
rural, AD-003) reusando o mesmo padrão de `ingestao/sigef.py`; (b) camada urbana Niterói via SIGeo
(já confirmada acessível em Fase 0, 82.199 feições); (c) malha municipal IBGE (fecha TD-001). Sem
bloqueio técnico — Fase 0 está fechada pras três.

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
