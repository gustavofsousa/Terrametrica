# Visão do Produto

## O problema

Um pedaço de terra no Rio de Janeiro é um objeto opaco. Para saber o que ele é — área real,
o que limita seu uso, que risco carrega, se o limite é contestado — é preciso visitar de cinco
a oito portais públicos, cada um com login, formato e recorte próprios, e cruzar tudo à mão em
software de GIS.

Isso produz dois perdedores:

- **Quem não é geoprocessador simplesmente não consegue.** O produtor rural e o corretor
  compram, financiam e projetam com informação incompleta, e descobrem o passivo depois da
  escritura.
- **Quem é geoprocessador gasta horas por lote** refazendo o mesmo trabalho manual, sem
  acumular nada reutilizável.

O dado existe e é público. O que não existe é o cruzamento.

## O que o produto é

Um mapa do estado do Rio de Janeiro onde **um clique devolve o dossiê do lote**: o polígono
acende e aparece a ficha técnica, as restrições ambientais e de risco já cruzadas, e a fonte
e a data de cada número.

A referência mental é o Google Maps, não um portal de GIS: mapa limpo, uma camada de
inteligência por cima, resposta imediata, zero treinamento.

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
Ninguém paga por ele. O que ninguém entrega pronto é "20% deste terreno está em Reserva Legal
e ele encosta em área suscetível a deslizamento" em dez segundos.

**2. Confiança é o produto.** Um número sem origem é um chute bem formatado. Todo campo do
dossiê carrega fonte e data, e onde não há dado o sistema declara ausência de cobertura em vez
de devolver vazio ambíguo. Isso é caro de construir e é exatamente o que separa uma ferramenta
de decisão de um brinquedo.

**3. Divergência entre fontes é achado, não defeito.** O CAR é autodeclaratório — o proprietário
desenha o próprio perímetro. O SIGEF é certificado pelo INCRA. Onde os dois discordam há
potencial litígio de limite. Mostramos os dois lado a lado com a diferença quantificada e
nunca reconciliamos em silêncio.

## Quem usa

### Produtor rural e consultoria agro

**Dor:** descobrir tarde que parte da área comprada é Reserva Legal, APP ou está em unidade de
conservação. Ou não conseguir provar conformidade ambiental para acessar crédito.

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

O que muda é qual seção pesa mais. Isso é deliberado: um produto, duas leituras, nenhum
branch de código por persona.

## Como o valor chega

**Painel web interativo** é a superfície principal — é onde o valor se prova em segundos e onde
iteramos rápido.

**PDF exportável** é o artefato que circula — anexado em proposta, processo ou apresentação.
Carimbado com data, hora, identificador do lote, versão da base e a ressalva de que não tem fé
pública.

## Como saberemos que funcionou

- Um usuário sem formação em GIS obtém o dossiê de um lote conhecido em menos de 2 minutos, sem ajuda
- Área e código do imóvel batem com a fonte oficial em 20 de 20 lotes conferidos manualmente
- Nenhum campo do dossiê aparece sem fonte e data
- Nenhum nome, CPF ou CNPJ de proprietário existe em qualquer tabela do produto
