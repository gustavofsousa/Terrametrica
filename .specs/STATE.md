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

### AD-006 — Piloto urbano: município do Rio de Janeiro
**Data:** 2026-08-18
**Decisão:** A camada urbana do MVP cobre apenas o município do Rio (DATA.RIO / IPP). Niterói é o segundo.
**Razão:** Maior mercado para a persona incorporador e portal de dados abertos mais maduro do estado.
**Consequência:** A página de cobertura precisa deixar explícito que 91 municípios não têm camada urbana.

## Handoff

**Branch:** `claude/lote-dossier-rj-app-qxe897`
**Fase atual:** Specify concluída, aguardando confirmação do usuário antes de Design.
**Artefatos:** `docs/research/fontes-de-dados-rj.md`, `.specs/features/dossie-lote-rj/spec.md`,
`.specs/features/dossie-lote-rj/context.md`.
**Próximo passo:** com o spec aprovado, rodar Design (escopo Large/Complex exige design.md).
**Bloqueios conhecidos:** o ambiente de desenvolvimento bloqueia HTTPS para hosts `.gov.br`,
então nenhum endpoint de fonte foi testado por requisição real. A checklist de verificação em
`docs/research/fontes-de-dados-rj.md` precisa rodar em ambiente com egress liberado antes de
qualquer código de ingestão.
