# Anatomia do Dossiê

O dossiê é a unidade de entrega do produto. Este documento define o que ele mostra, em que
ordem e de onde vem cada campo. É o contrato entre produto, design e engenharia.

**Regra que vale para toda linha deste documento:** nenhum campo aparece sem fonte e data de
extração. Onde não há dado, o dossiê declara ausência de cobertura — nunca devolve vazio.

---

## Ordem de leitura

As seções aparecem nesta ordem, porque é a ordem em que a pergunta do usuário se forma:
*o que é isso → posso usar? → posso confiar?*

1. Identificação
2. Geometria
3. Restrições e alertas
4. Divergência entre fontes (só rural, só quando existe)
5. Proveniência

---

## 1. Identificação — "o que é isso"

### Lote rural

| Campo | Fonte | Observação |
| --- | --- | --- |
| Código do imóvel rural | SIGEF / INCRA | Identificador certificado |
| Município (ou municípios) | SIGEF + malha IBGE | Imóvel que cruza divisa lista todos |
| Denominação | SIGEF | Quando declarada |
| Situação da certificação | SIGEF | Certificado, em análise |

### Lote urbano (município do Rio)

| Campo | Fonte | Observação |
| --- | --- | --- |
| Inscrição cadastral | DATA.RIO / IPP | Chave do cadastro do IPTU |
| Logradouro e número | DATA.RIO / IPP | |
| Bairro | DATA.RIO / IPP | |
| Quadra e lote (PAL) | GeoPAL | Quando o lote tem projeto de alinhamento aprovado |

---

## 2. Geometria — "qual o tamanho e o formato"

| Campo | Rural | Urbano |
| --- | --- | --- |
| Área | Hectares | Metros quadrados |
| Perímetro | Metros | Metros |
| Testada | — | Metros (quando derivável do PAL) |
| Polígono no mapa | Destacado ao clique | Destacado ao clique |

**Área calculada, não copiada.** A área exibida é recalculada a partir da geometria em projeção
equivalente, e comparada com a área declarada na fonte. Divergência acima do limiar aparece
como alerta, não é escondida.

**Porção fora do estado.** Imóvel que ultrapassa a divisa do RJ tem as áreas calculadas apenas
sobre a porção dentro do estado, e o dossiê declara isso.

---

## 3. Restrições e alertas — "posso usar isso"

Esta é a seção que justifica o produto. Toda intersecção é expressa como **área absoluta e
percentual do lote** — nunca como sim ou não.

| Alerta | Fonte | Aplica a |
| --- | --- | --- |
| Área de Preservação Permanente (APP) | CAR / SICAR | Rural |
| Reserva Legal | CAR / SICAR | Rural |
| Unidade de conservação (nome e categoria) | INEA, ICMBio | Rural e urbano |
| Suscetibilidade a inundação | INEA | Rural e urbano |
| Suscetibilidade a deslizamento | INEA | Rural e urbano |
| Corpos d'água e mananciais | INEA, ANA | Rural e urbano |

### Duas regras que evitam alarme falso

**Toque marginal.** Intersecção abaixo de 1% da área do lote aparece marcada como
"toque marginal — verificar em campo". Polígonos públicos têm erro posicional real; tratar
um encostão de 30 cm como restrição destrói a credibilidade do produto inteiro.

**Indicativo, não licenciamento.** Toda a seção carrega a declaração de que os cruzamentos são
indicativos e não substituem levantamento técnico ou processo de licenciamento.

---

## 4. Divergência entre fontes — "esse limite é contestado"

Aparece apenas em lote rural que existe nas duas bases.

| Elemento | Comportamento |
| --- | --- |
| Polígono SIGEF | Exibido, rotulado como **limite certificado** |
| Polígono CAR | Exibido, rotulado como **declaração do proprietário** |
| Diferença de área | Em hectares e em percentual |
| Alerta de divergência | Acionado acima de 5% de diferença |
| Polígono reconciliado | **Não existe.** Reconciliar automaticamente esconderia o achado |

---

## 5. Proveniência — "posso confiar nisso"

| Elemento | Comportamento |
| --- | --- |
| Fonte por campo | Nome da base de origem |
| Data de extração | Quando aquela camada foi ingerida |
| Link para a fonte | Leva à consulta correspondente no portal oficial |
| Aviso de base antiga | Camada extraída há mais de 90 dias é marcada "possivelmente desatualizada" |
| Camada indisponível | Entregue o resto do dossiê e marque a faltante — nunca falhe inteiro |
| Camada sem cobertura | "camada não disponível neste município" — a seção aparece, declarando a ausência |

---

## Estados que não são o caminho feliz

Estes estados são parte do produto, não tratamento de erro. São eles que sustentam a confiança.

| Situação | O que o dossiê faz |
| --- | --- |
| Clique fora de qualquer polígono conhecido | Informa o município e a cobertura declarada daquele município |
| Clique fora do estado do RJ | Recusa: "fora da área de cobertura: apenas RJ" |
| Clique em sobreposição de polígonos | Lista todos os imóveis sobrepostos e exige escolha antes de montar o dossiê |
| Município sem camada urbana | Declara explicitamente que não há camada urbana ali |
| Geometria corrigida na ingestão | Marca o registro como "geometria corrigida na ingestão" |

---

## A seção que não existe nesta versão

**Proprietário.** Nome, CPF/CNPJ, ônus e cadeia dominial não aparecem, e não estão em nenhuma
tabela do produto. A seção aparece como "indisponível nesta versão" para todos os papéis de
usuário. A razão está em [riscos.md](riscos.md) e a decisão em `.specs/STATE.md` (AD-002).

---

## Página de cobertura

Fora do dossiê, mas parte do mesmo contrato de honestidade: uma página pública que informa,
**por município e por camada**, se há dado e de qual data. Cobertura irregular é fato estrutural
do estado — declarada, vira característica; escondida, vira bug percebido.
