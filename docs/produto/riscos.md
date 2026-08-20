# Riscos

Cinco riscos podem matar ou deformar o produto. Cada um tem uma mitigação já embutida na
especificação — não são preocupações soltas.

---

## 1. Jurídico — a camada de proprietário (alto)

**O risco:** tratar "dado público" como "dado livre". A Lei 6.015/73, art. 17, garante que
qualquer pessoa obtenha **certidão** do registro sem declarar motivo. Isso sustenta a *consulta
pontual*. Não sustenta baixar, agregar e servir uma base "proprietário → imóveis" como camada de
mapa. A LGPD não isenta dado público de origem quando ele é agregado e redistribuído — a
mudança de escala é, ela própria, um novo tratamento.

**Agravante:** não localizamos documentação pública de API do ONR para terceiros. Construir
produto sobre uma integração que talvez não exista é a forma mais cara de descobrir isso.

**Mitigação já decidida (AD-002):** nenhum nome, CPF ou CNPJ é ingerido ou persistido nesta
versão. Papéis, verificação de credencial e log imutável de auditoria são construídos vazios na
Fase 2. A camada só liga se a Fase 0 confirmar caminho defensável.

**Sinal de que o risco virou realidade:** alguém propõe "só guardar em cache para acelerar".

> Nada aqui é parecer jurídico. Antes de ligar a camada registral, isso precisa passar por
> advogado especializado em proteção de dados e direito registral.

---

## 2. Cobertura urbana irregular (alto)

**O risco:** 91 dos 92 municípios do RJ provavelmente não publicam lote cadastral aberto. Se o
produto se apresentar como "mapa de lotes do RJ" e devolver nada em Petrópolis, o usuário
conclui que o produto está errado — não que o dado não existe.

**Mitigação já decidida:** cobertura declarada por município e por camada, em página pública, e
mensagem explícita de ausência no lugar de vazio. Comunicação de produto fala em "rural em todo
o RJ, urbano em Niterói", nunca em "lotes do RJ".

**Sinal de que o risco virou realidade:** suporte recebendo "o app não encontra meu terreno".

---

## 3. Qualidade e discordância do dado de origem (médio-alto)

**O risco:** o CAR é autodeclaratório e contém sobreposições, polígonos inválidos e áreas que
não batem com o SIGEF. Se o produto apresentar isso como verdade única, ele propaga erro com
uma camada de credibilidade por cima — pior que não existir.

**Mitigação já decidida (AD-003):** SIGEF rotulado como limite certificado, CAR como declaração
do proprietário, divergência exibida e quantificada, **zero reconciliação automática**. Área
recalculada da geometria e comparada com a declarada. Geometria inválida é corrigida na ingestão
e o registro fica marcado.

**Sinal de que o risco virou realidade:** um usuário toma decisão errada citando o dossiê.

---

## 4. Dependência de fontes que não controlamos (médio)

**O risco:** portais mudam endereço, formato e política de acesso sem aviso. O INCRA passou a
exigir login gov.br nos portais interativos em outubro de 2023. Uma quebra silenciosa de
ingestão serve dado velho como se fosse novo.

**Mitigação já decidida (AD-004, AD-005):** base própria — consulta do usuário não depende de
portal do governo estar de pé. Data de extração carimbada por camada, aviso automático acima de
90 dias, aviso persistente acima de 180. Reingestão que produza menos de 90% das feições da
versão anterior é **rejeitada**, e a versão anterior continua em serviço.

**Sinal de que o risco virou realidade:** uma camada com data de extração parada há meses.

---

## 5. Responsabilidade sobre a decisão do usuário (médio)

**O risco:** alguém compra uma área, descobre um passivo que o dossiê não mostrou, e nos
responsabiliza. Precisão posicional de dado público é limitada, e a ausência de uma restrição
na nossa base não prova sua ausência no mundo.

**Mitigação já decidida:** o dossiê declara a precisão da fonte e não afirma precisão maior que
ela. Cruzamentos são declarados indicativos, não substitutos de levantamento técnico ou
licenciamento. Intersecção abaixo de 1% é marcada como "toque marginal — verificar em campo".
O PDF carrega a ressalva de que não tem fé pública. Não emitimos laudo nem valuation.

**Sinal de que o risco virou realidade:** o time começa a discutir "quanta certeza dar" em vez
de "quanta incerteza mostrar".

---

## O padrão comum

Quatro dos cinco riscos têm a mesma mitigação de fundo: **declarar a incerteza em vez de
escondê-la**. Isso não é cautela jurídica defensiva — é o que torna o dossiê utilizável para
decisão de dinheiro. Um produto que finge certeza é um produto que ninguém pode usar como prova
de nada.
