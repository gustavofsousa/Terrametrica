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
**Fase atual:** Execute concluído para a **Fatia 1 — núcleo de domínio** (`tasks.md` T1–T5).
Validação PASS registrada em `.specs/features/dossie-lote-rj/validation.md` (46 unit tests,
ruff + mypy strict verdes, sensor de discriminação 6/6 mutantes mortos).
**Commits:** `b851aec` (T1 scaffold) · `3925023` (T2 domínio) · `74f236d` (T3 geometria) ·
`aea1e36` (T4 ports) · `7445455` (T5 montagem). Nada pendente de commit no código.
**O que existe agora:** pacote `terrametrica` puro (sem I/O) — `dominio/modelos.py` (value objects,
enums fechados, união de resultados), `geometria/regras.py` (marginal 1% + divergência 5%),
`dossie/portas.py` (Protocols `RepositorioLotes`/`LimiteEstado`), `dossie/montagem.py`
(árvore de decisão `montar_dossie`), fake em memória em `tests/fakes/`.
**Refinamentos de contrato vs tasks.md:** `proveniencia_de -> Proveniencia | None` e novo
`municipio_em(coord, versao) -> str` (necessários p/ DOS-12 e DOS-04). Ver `validation.md`.
**Escopo entregue:** apenas a lógica de domínio. As ACs de usuário (DOS-01/03 fim-a-fim) **não**
estão demonstráveis ainda — faltam as fatias de infra. `spec.md` mantido em Pending de propósito
(não superdeclarar).
**Próximo passo:** Fatia 2 (adaptador PostGIS + ingestão versionada). Depois: página de cobertura,
API FastAPI + observabilidade, web MapLibre.

**Fase 0 — destravada e verificada por navegação real (2026-09-03):**
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
- **CAR — ainda pendente:** "Base de Downloads" não exige login e tem RJ disponível (dado de
  2026-09-03), com as 9 camadas do catálogo (perímetro, APP, reserva legal etc.) — mas cada
  download é **gated por reCAPTCHA**, resolvido manualmente pelo usuário — ver
  `docs/research/pendencias-humano.md` item 6. Depois de baixado, medir feições/CRS/validade e a
  **sobreposição SIGEF×CAR** (AD-003) fica automatizável.
- **Licença SIGeo Niterói confirmada:** liberada, com atribuição obrigatória (item 1 de
  `pendencias-humano.md`, fechado).

**Bloqueios conhecidos:** nenhum bloqueio de egress na máquina local. Fontes rurais exigem ação
humana pontual para baixar o arquivo (login gov.br p/ SIGEF; resolver captcha p/ CAR) — depois
disso a medição segue por agente. A camada urbana (Niterói) já está pronta para prototipar
ingestão real sem depender de ação humana adicional.
