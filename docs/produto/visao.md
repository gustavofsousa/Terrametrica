# Visão do Produto

## O problema

Um pedaço de terra no Rio de Janeiro é um objeto opaco. As perguntas básicas: qual a área real, o
que limita o uso, que risco ele carrega, se o limite é contestado. Para responder, a pessoa visita
de cinco a oito portais públicos, cada um com login, formato e recorte próprios. Depois cruza tudo à
mão em software de GIS.

Isso produz dois perdedores:

- **Quem não é geoprocessador não consegue.** O produtor rural e o corretor compram, financiam e
  projetam com informação incompleta. Eles descobrem o passivo depois da escritura.
- **Quem é geoprocessador gasta horas por lote.** Ele refaz o mesmo trabalho manual e não acumula
  nada reutilizável.

O dado existe e é público. O que não existe é o cruzamento.

## O que o produto é

Um mapa do estado do Rio de Janeiro onde **um clique devolve o dossiê do lote**. O polígono acende.
Aparecem a ficha técnica, as restrições ambientais e de risco já cruzadas, e a fonte e a data de
cada número.

A referência mental é o Google Maps, não um portal de GIS: mapa limpo, uma camada de inteligência
por cima, resposta imediata, zero treinamento.

## O que o produto não é

| Não é | Por quê |
| --- | --- |
| Um cartório | Não emitimos documento com fé pública. O dossiê é instrumento de análise, não prova registral. |
| Um laudo de avaliação | Não estimamos preço. Isso exige base de transações que não temos e responsabilidade técnica que não queremos assumir no MVP. |
| Um portal de GIS | Não pedimos ao usuário que entenda camadas, projeções ou shapefiles. Se ele precisar saber o que é um CRS, falhamos. |
| Um canal de retificação cadastral | Lemos e cruzamos fontes oficiais. Corrigir o dado público é com o órgão que o produziu. |
| Um proxy de portais do governo | Os dados são baixados e materializados em base própria. Se o portal do INCRA cair, o produto continua de pé. |

## A tese

Três apostas sustentam o produto. Se alguma cair, o produto muda.

**1. O valor está no cruzamento, não no dado.** O perímetro sozinho já é público e gratuito.
Ninguém paga por ele. Ninguém entrega pronto, em dez segundos, uma frase como "20% deste terreno
está em Reserva Legal e ele encosta em área suscetível a deslizamento".

**2. Confiança é o produto.** Um número sem origem é um chute bem formatado. Todo campo do dossiê
carrega fonte e data. Se não há dado, o sistema declara ausência de cobertura. Ele nunca devolve um
vazio ambíguo. Isso é caro de construir, e é o que separa uma ferramenta de decisão de um
brinquedo.

**3. Divergência entre fontes é achado, não defeito.** O CAR é autodeclaratório: o proprietário
desenha o próprio perímetro. O INCRA certifica o SIGEF. Se os dois discordam, há potencial litígio
de limite. Mostramos os dois lado a lado, com a diferença quantificada. Nunca reconciliamos em
silêncio.

## Quem usa

### Produtor rural e consultoria agro

**Dor:** descobrir tarde que parte da área comprada é Reserva Legal, é APP ou está em unidade de
conservação. Ou não provar a conformidade ambiental para ter acesso a crédito.

**O que pesa no dossiê:** área real em hectares, percentual em APP e Reserva Legal, unidades de
conservação interceptadas, divergência entre o que o CAR declara e o que o SIGEF certifica.

**Momento de uso:** antes de comprar, antes de financiar, antes de arrendar.

### Corretor, incorporador e investidor

**Dor:** avaliar um terreno urbano sem saber o que se pode construir nele, nem que risco ele
carrega. Descobrir a restrição depois da proposta assinada.

**O que pesa no dossiê:** área e testada do lote, inscrição cadastral, suscetibilidade a
inundação e deslizamento, proximidade de unidade de conservação.

**Momento de uso:** triagem de oportunidade, due diligence antes da proposta, defesa da proposta
diante do cliente.

### As duas personas compartilham o mesmo dossiê

Muda só a seção que pesa mais. Isso é de propósito: um produto, duas leituras, nenhum branch de
código por persona.

## Como o valor chega

O **painel web interativo** é a superfície principal. Ali o valor aparece em segundos, e ali
iteramos rápido.

O **PDF exportável** é o artefato que circula. O usuário o anexa numa proposta, num processo ou numa
apresentação. O PDF leva data, hora, identificador do lote, versão da base e a ressalva de que não
tem fé pública.

## Como saberemos que funcionou

- Um usuário sem formação em GIS obtém o dossiê de um lote conhecido em menos de 2 minutos, sem ajuda.
- A área e o código do imóvel batem com a fonte oficial em 20 de 20 lotes conferidos à mão.
- Nenhum campo do dossiê aparece sem fonte e data.
- Nenhum nome, CPF ou CNPJ de proprietário existe em qualquer tabela do produto.
