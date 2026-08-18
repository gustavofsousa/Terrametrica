# Dossiê de Lote — Rio de Janeiro (MVP)

## Problem Statement

Hoje, para saber o que é um pedaço de terra no RJ — área real, restrição ambiental, risco,
zoneamento — é preciso visitar de cinco a oito portais públicos diferentes, cada um com login,
formato e recorte próprios, e cruzar tudo à mão em software de GIS. Quem não é geoprocessador
não consegue; quem é, gasta horas por lote. O resultado é que produtor rural e incorporador
tomam decisão de compra, crédito e projeto com informação incompleta, e descobrem o passivo
depois da escritura. Este produto colapsa esse trabalho em um clique no mapa.

## Goals

- [ ] Do clique no mapa ao dossiê legível em **menos de 10 segundos** para qualquer lote coberto
- [ ] Cobrir **100% dos imóveis rurais certificados (SIGEF) do RJ** e os lotes urbanos do município do Rio de Janeiro
- [ ] Cada campo do dossiê exibe **fonte e data de extração** — zero dado órfão
- [ ] Onde não há dado, o sistema diz **"não há cobertura aqui"** em vez de devolver vazio ambíguo

## Out of Scope

Explicitamente excluído. Documentado para evitar avanço de escopo.

| Feature | Reason |
| --- | --- |
| Dados de proprietário (nome, CPF/CNPJ, ônus, cadeia dominial) | Publicidade registral (Lei 6.015/73 art. 17) autoriza consulta por certidão, não agregação e redistribuição de base. Sem caminho confirmado com o ONR, vira passivo de LGPD. O gate de permissão é arquitetado (P2), o dado não é ingerido. |
| Municípios do RJ além do Rio de Janeiro na camada urbana | Cobertura cadastral aberta dos outros 91 municípios é desconhecida. Exige inventário próprio antes de prometer. |
| Estados fora do RJ | Decisão declarada do produto. Arquitetura é preparada para federar, o MVP não federa. |
| Valuation / preço estimado do lote | Exige base de transações que não temos e responsabilidade de laudo que não queremos no MVP. |
| Edição ou correção de dado público pelo usuário | O produto lê e cruza fontes oficiais; não é canal de retificação cadastral. |
| Emissão de certidão ou documento com fé pública | Não somos cartório. O dossiê é instrumento de análise, não prova registral. |
| App móvel nativo | Painel web responsivo cobre o uso do MVP. |

---

## Assumptions & Open Questions

Toda ambiguidade está resolvida ou registrada aqui — nada fica silenciosamente indefinido.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Recorte do MVP | Rural em todo o RJ (SIGEF + CAR) mais o município do Rio como piloto urbano | Usuário não expressou preferência e delegou. Rural já tem cobertura estadual pronta; o Rio é o maior mercado urbano e publica dado aberto. Um recorte por persona escolhida. | n |
| Município urbano piloto | Rio de Janeiro (DATA.RIO / IPP) | Maior volume de negócio para a persona incorporador e portal de dados abertos mais maduro do estado. Niterói entra como segundo. | n |
| Camada de proprietário | Fora do MVP; papéis, verificação de credencial e log de auditoria são construídos vazios em P2 | Decisão do usuário. Construir o gate antes evita retrabalho quando o caminho registral for confirmado. | y |
| Existência de API do ONR para terceiros | Assumimos que **não existe** integração pública documentada até prova em contrário | Não localizada na pesquisa. Assumir ausência é o erro barato; assumir presença quebra a promessa de produto. | n |
| Autoridade do limite rural | SIGEF é o limite autoritativo; CAR é exibido como declaração do proprietário | SIGEF é certificado pelo INCRA, CAR é autodeclaratório. Inverter isso induziria o usuário a erro material. | n |
| Sistema de referência de coordenadas | SIRGAS 2000 (EPSG:4674) para armazenamento; Web Mercator (EPSG:3857) para exibição | Padrão oficial brasileiro para armazenamento; Mercator é o que as bibliotecas de tile esperam. Confirmação final em Design. | n |
| Frequência de atualização das bases | Reingestão mensal, com data de extração carimbada por camada | As fontes públicas não publicam SLA de atualização. Mensal equilibra frescor e custo até medirmos a cadência real. | n |
| Comportamento quando fontes discordam | Exibir ambas as versões lado a lado com a divergência quantificada; nunca reconciliar silenciosamente | O valor do produto é confiança. Uma reconciliação automática esconde exatamente o achado que o usuário precisa ver. | n |
| Acesso ao MVP | Requer conta autenticada, sem paywall | Necessário para log de auditoria e para medir uso real por persona antes de precificar. | n |
| Idioma | Português do Brasil na interface e no dossiê | Público exclusivamente brasileiro. | y |
| Licença do MapBiomas para uso comercial | Assumida como **não confirmada**; camada de uso do solo entra apenas se a licença permitir | Usar dado licenciado indevidamente contamina o produto inteiro. | n |
| Precisão declarada | O dossiê declara a precisão da fonte e não afirma precisão maior que ela | Polígonos públicos têm erro posicional real; alegar exatidão cria responsabilidade indevida. | n |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## Implicit-Requirement Dimensions Sweep

Varredura completa exigida pelo escopo Complex. Cada dimensão resolve em requisito ou em `N/A porque`.

| Dimension | Resolução |
| --- | --- |
| Input validation & bounds | DOS-02, DOS-24 — coordenada fora do RJ e polígono inválido são rejeitados com mensagem específica |
| Failure / partial-failure states | DOS-11, DOS-12 — dossiê parcial é entregue marcando a camada indisponível, nunca falha inteiro |
| Idempotency / retry / duplicate handling | DOS-26 — a mesma coordenada produz o mesmo dossiê enquanto a versão da base não mudar |
| Auth boundaries & rate limits | DOS-20, DOS-21, DOS-27 — papéis, limite por conta |
| Concurrency / ordering | DOS-28 — reingestão não pode servir base meio atualizada; troca é atômica por versão |
| Data lifecycle / expiry | DOS-13, DOS-29 — data de extração carimbada e aviso de base obsoleta |
| Observability | DOS-30 — toda consulta registra lote, usuário, camadas e latência |
| External-dependency failure | DOS-12 — fontes externas caídas não derrubam o dossiê, porque a base é própria |
| State-transition integrity | DOS-22 — mudança de papel de usuário é registrada e não retroage a acessos passados |

---

## User Stories

### P1: Dossiê do lote a partir de um clique no mapa ⭐ MVP

**User Story**: Como produtor rural ou incorporador, quero clicar em um ponto do mapa e receber
a ficha técnica daquele lote, para saber o que é aquele terreno sem abrir sete portais.

**Why P1**: É o produto. Sem isso não há nada para avaliar.

**Acceptance Criteria**:
1. WHEN o usuário toca um ponto do mapa que cai dentro de um imóvel rural certificado SIGEF THEN o sistema SHALL destacar o polígono do imóvel e exibir código do imóvel, área em hectares, perímetro em metros e município
2. WHEN o usuário toca um ponto do mapa que cai dentro de um lote urbano do município do Rio THEN o sistema SHALL destacar o polígono do lote e exibir a inscrição cadastral, a área do lote em metros quadrados e o logradouro
3. WHEN o usuário toca um ponto coberto pela base THEN o sistema SHALL apresentar o dossiê completo em até 10 segundos no percentil 95
4. IF o ponto tocado não está contido em nenhum polígono conhecido THEN o sistema SHALL exibir "sem lote mapeado neste ponto" junto do município e da cobertura declarada daquele município
5. IF a coordenada tocada está fora dos limites do estado do Rio de Janeiro THEN o sistema SHALL recusar a consulta com a mensagem "fora da área de cobertura: apenas RJ"
6. WHEN um ponto cai na sobreposição de dois ou mais polígonos THEN o sistema SHALL listar todos os imóveis sobrepostos e SHALL exigir que o usuário escolha um antes de montar o dossiê

**Independent Test**: Abrir o mapa em uma fazenda conhecida de Cachoeiras de Macacu e um lote conhecido de Copacabana, tocar cada um e conferir código, área e município contra o portal oficial da fonte.

---

### P1: Restrições ambientais e de risco cruzadas automaticamente ⭐ MVP

**User Story**: Como produtor rural ou incorporador, quero que o sistema cruze o lote com as
camadas ambientais e de risco, para eu saber o que limita o uso daquele terreno antes de comprar.

**Why P1**: É o diferencial. O perímetro sozinho já existe nos portais públicos; o cruzamento é o que ninguém entrega pronto.

**Acceptance Criteria**:
1. WHEN o dossiê de um lote rural é montado THEN o sistema SHALL calcular e exibir a área e o percentual do lote em Área de Preservação Permanente e em Reserva Legal segundo o CAR
2. WHEN o dossiê de qualquer lote é montado THEN o sistema SHALL indicar se o lote intersecta unidade de conservação, informando nome e categoria da unidade
3. WHEN o dossiê de qualquer lote é montado THEN o sistema SHALL indicar se o lote intersecta área suscetível a inundação ou a deslizamento segundo o INEA, informando o grau de suscetibilidade
4. The sistema SHALL expressar toda intersecção como área absoluta e percentual do lote, nunca apenas como sim ou não
5. IF uma intersecção cobre menos de 1% da área do lote THEN o sistema SHALL exibi-la marcada como "toque marginal — verificar em campo", para não gerar alarme falso por imprecisão posicional
6. The sistema SHALL declarar que os cruzamentos são indicativos e não substituem levantamento técnico ou licenciamento

**Independent Test**: Escolher um imóvel rural com Reserva Legal averbada conhecida e conferir o percentual calculado contra o extrato do próprio CAR do imóvel.

---

### P1: Proveniência e cobertura honesta ⭐ MVP

**User Story**: Como usuário que vai tomar decisão de dinheiro em cima do dossiê, quero saber
de onde veio cada número e quando ele foi extraído, para poder confiar ou ir checar na fonte.

**Why P1**: Um dossiê sem proveniência é um chute bem formatado. A confiança é o produto, não um enfeite.

**Acceptance Criteria**:
1. The sistema SHALL exibir, para cada campo do dossiê, a fonte de origem e a data de extração daquela base
2. WHEN o usuário aciona um campo do dossiê THEN o sistema SHALL oferecer o link para a consulta correspondente no portal oficial da fonte
3. WHILE a base de uma camada estiver com extração há mais de 90 dias o sistema SHALL marcar aquela camada como "possivelmente desatualizada" no dossiê
4. IF uma camada não tem cobertura para o município do lote consultado THEN o sistema SHALL exibir "camada não disponível neste município" em vez de omitir a seção
5. IF uma camada estiver indisponível no momento da consulta THEN o sistema SHALL entregar o dossiê com as demais camadas e SHALL marcar a camada faltante como "indisponível no momento da consulta"
6. The sistema SHALL manter uma página de cobertura pública informando, por município e por camada, se há dado e de qual data

**Independent Test**: Abrir um dossiê e verificar que todo número visível tem fonte e data ao lado, e que a página de cobertura reflete o mesmo estado.

---

### P2: Exportação do dossiê em PDF

**User Story**: Como corretor ou consultor, quero exportar o dossiê em PDF, para anexar em
proposta, processo ou apresentação ao cliente.

**Why P2**: O painel prova o valor; o PDF é o que circula. Importante, mas o produto existe sem ele.

**Acceptance Criteria**:
1. WHEN o usuário solicita a exportação de um dossiê THEN o sistema SHALL gerar um PDF contendo o mapa do lote, a ficha técnica, as restrições e a proveniência de cada campo
2. The PDF SHALL conter a data e a hora de geração, o identificador do lote e a versão da base usada
3. The PDF SHALL conter a ressalva de que não é documento com fé pública nem substitui certidão
4. IF a geração do PDF falhar THEN o sistema SHALL informar a falha e SHALL manter o dossiê acessível no painel

**Independent Test**: Exportar o dossiê de um lote e conferir que o PDF reproduz os mesmos valores do painel, com data e versão da base.

---

### P2: Divergência entre fontes exposta

**User Story**: Como analista, quero ver quando o SIGEF e o CAR discordam sobre o mesmo imóvel,
para não assinar um negócio em cima de um limite contestado.

**Why P2**: Alto valor analítico, mas depende da camada rural básica já funcionando.

**Acceptance Criteria**:
1. WHEN um imóvel rural tem perímetro no SIGEF e no CAR THEN o sistema SHALL exibir os dois polígonos e SHALL informar a diferença de área em hectares e em percentual
2. WHERE a diferença de área entre as fontes exceder 5% o sistema SHALL destacar o lote com o alerta "divergência entre fontes"
3. The sistema SHALL identificar o SIGEF como limite certificado e o CAR como declaração do proprietário, em todo lugar onde os dois aparecem
4. The sistema SHALL abster-se de reconciliar automaticamente os limites divergentes em um polígono único

**Independent Test**: Selecionar um imóvel com divergência conhecida entre as bases e conferir que os dois polígonos e o percentual de diferença aparecem.

---

### P2: Gate de permissão jurídica arquitetado, sem dado pessoal

**User Story**: Como operador do produto, quero papéis, verificação de credencial e auditoria
já construídos, para poder habilitar a camada registral no dia em que o caminho jurídico estiver
confirmado, sem reescrever o sistema.

**Why P2**: Estrutural. Não entrega valor visível hoje, mas evita retrabalho e é pré-condição do próximo passo.

**Acceptance Criteria**:
1. The sistema SHALL atribuir a toda conta exatamente um papel entre "consulta" e "habilitado juridicamente"
2. WHERE a camada registral estiver desligada o sistema SHALL exibir a seção de proprietário como "indisponível nesta versão" para todos os papéis
3. IF uma conta de papel "consulta" solicitar dado registral THEN o sistema SHALL negar com HTTP 403 e SHALL registrar a tentativa
4. WHEN uma conta é promovida a "habilitado juridicamente" THEN o sistema SHALL registrar quem promoveu, quando e sob qual credencial verificada
5. The sistema SHALL registrar em log imutável toda consulta a dado registral, com identidade, finalidade declarada, lote e instante
6. The sistema SHALL abster-se de persistir nome, CPF ou CNPJ de proprietário em qualquer tabela do produto nesta versão

**Independent Test**: Criar uma conta de cada papel, tentar acessar a seção registral com ambas e conferir a negativa, o 403 e as entradas de log.

---

### P3: Consulta por polígono próprio

**User Story**: Como técnico, quero desenhar um polígono ou subir um KML/GeoJSON, para analisar
uma área que ainda não está mapeada nas bases oficiais.

**Why P3**: Amplia o alcance para áreas sem cadastro, mas o MVP já resolve o caso principal sem isso.

**Acceptance Criteria**:
1. WHEN o usuário desenha um polígono fechado sobre o mapa THEN o sistema SHALL rodar os mesmos cruzamentos de restrição usados para lotes cadastrados
2. IF o arquivo enviado exceder 10 MB ou contiver geometria inválida THEN o sistema SHALL recusar o envio identificando o motivo específico
3. The sistema SHALL marcar todo dossiê originado de polígono do usuário como "área informada pelo usuário — sem respaldo cadastral"

**Independent Test**: Desenhar um polígono sobre uma unidade de conservação conhecida e conferir que a intersecção é detectada e o dossiê vem marcado como área informada.

---

## Edge Cases

- IF o polígono da fonte estiver topologicamente inválido THEN o sistema SHALL corrigi-lo na ingestão e SHALL marcar o registro como "geometria corrigida na ingestão"
- IF um imóvel rural cruzar a divisa de dois municípios THEN o sistema SHALL listar todos os municípios interceptados em vez de escolher um
- IF um imóvel rural do RJ ultrapassar a divisa do estado THEN o sistema SHALL calcular as áreas apenas sobre a porção dentro do RJ e SHALL declarar isso no dossiê
- IF a reingestão mensal produzir uma base com menos de 90% do número de feições da versão anterior THEN o sistema SHALL rejeitar a publicação daquela versão e SHALL manter a anterior em serviço
- WHEN o usuário consulta o mesmo lote duas vezes sob a mesma versão de base THEN o sistema SHALL retornar exatamente o mesmo dossiê
- IF uma conta exceder 100 consultas de dossiê por hora THEN o sistema SHALL responder HTTP 429 e SHALL informar quando a cota se renova
- WHILE uma reingestão estiver em curso o sistema SHALL continuar servindo a versão publicada anterior, sem misturar versões dentro de um mesmo dossiê
- IF a base de uma camada não for atualizada por mais de 180 dias THEN o sistema SHALL exibir um aviso persistente na página de cobertura

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| DOS-01 | P1: Dossiê do lote | Design | Pending |
| DOS-02 | P1: Dossiê do lote | Design | Pending |
| DOS-03 | P1: Dossiê do lote | Design | Pending |
| DOS-04 | P1: Dossiê do lote | Design | Pending |
| DOS-05 | P1: Dossiê do lote | Design | Pending |
| DOS-06 | P1: Restrições | Design | Pending |
| DOS-07 | P1: Restrições | Design | Pending |
| DOS-08 | P1: Restrições | Design | Pending |
| DOS-09 | P1: Restrições | Design | Pending |
| DOS-10 | P1: Proveniência | Design | Pending |
| DOS-11 | P1: Proveniência | Design | Pending |
| DOS-12 | P1: Proveniência | Design | Pending |
| DOS-13 | P1: Proveniência | Design | Pending |
| DOS-14 | P2: Exportação PDF | - | Pending |
| DOS-15 | P2: Exportação PDF | - | Pending |
| DOS-16 | P2: Exportação PDF | - | Pending |
| DOS-17 | P2: Divergência entre fontes | - | Pending |
| DOS-18 | P2: Divergência entre fontes | - | Pending |
| DOS-19 | P2: Divergência entre fontes | - | Pending |
| DOS-20 | P2: Gate jurídico | - | Pending |
| DOS-21 | P2: Gate jurídico | - | Pending |
| DOS-22 | P2: Gate jurídico | - | Pending |
| DOS-23 | P3: Polígono próprio | - | Pending |
| DOS-24 | P3: Polígono próprio | - | Pending |
| DOS-25 | Edge: geometria e divisas | Design | Pending |
| DOS-26 | Edge: idempotência do dossiê | Design | Pending |
| DOS-27 | Edge: limite de consultas | - | Pending |
| DOS-28 | Edge: publicação atômica de versão | Design | Pending |
| DOS-29 | Edge: base obsoleta | Design | Pending |
| DOS-30 | Observabilidade de consultas | Design | Pending |

**ID format:** `DOS-[NUMBER]`

**Coverage:** 30 total, 0 mapeados para tarefas, 30 não mapeados ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Um usuário sem formação em GIS obtém o dossiê de um lote conhecido em menos de 2 minutos, sem ajuda
- [ ] Área e código do imóvel batem com a fonte oficial em 20 de 20 lotes conferidos manualmente (10 rurais, 10 urbanos)
- [ ] Nenhum campo do dossiê aparece sem fonte e data de extração
- [ ] Nenhum nome, CPF ou CNPJ de proprietário existe em qualquer tabela do produto
- [ ] A página de cobertura declara o estado real de cada camada por município, conferida por amostragem
