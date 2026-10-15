# Riscos

Cinco riscos podem matar ou deformar o produto. Cada um tem uma mitigação já embutida na
especificação. Não são preocupações soltas.

---

## 1. Jurídico — a camada de proprietário (alto)

**O risco:** tratar "dado público" como "dado livre". A Lei 6.015/73, art. 17, garante que
qualquer pessoa obtenha **certidão** do registro sem declarar motivo. Isso sustenta a *consulta
pontual*. Não sustenta baixar, agregar e servir uma base "proprietário → imóveis" como camada de
mapa. A LGPD não isenta o dado público de origem quando alguém o agrega e redistribui. A mudança de
escala é, ela própria, um novo tratamento.

**Agravante:** não achamos documentação pública de API do ONR para terceiros. Construir produto sobre
uma integração que pode não existir é a forma mais cara de descobrir isso.

**Mitigação já decidida (AD-002):** nesta versão, o produto não ingere nem persiste nenhum nome, CPF ou
CNPJ. A Fase 2 constrói vazios os papéis, a verificação de credencial e o log imutável de auditoria.
A camada só liga se a Fase 0 confirmar um caminho defensável.

**Sinal de que o risco virou realidade:** alguém propõe "só guardar em cache para acelerar".

> WARNING: Nada aqui é parecer jurídico. Antes de ligar a camada registral, um advogado
> especializado em proteção de dados e direito registral deve revisar a decisão.

---

## 2. Cobertura urbana irregular (alto)

**O risco:** é provável que 91 dos 92 municípios do RJ não publiquem lote cadastral aberto. Se o
produto se apresentar como "mapa de lotes do RJ" e não devolver nada em Petrópolis, o usuário
conclui que o produto está errado. Ele não conclui que o dado não existe.

**Mitigação já decidida:** uma página pública declara a cobertura por município e por camada. Uma
mensagem explícita de ausência substitui o vazio. A comunicação de produto diz "rural em todo o RJ,
urbano em Niterói", nunca "lotes do RJ".

**Sinal de que o risco virou realidade:** suporte recebendo "o app não encontra meu terreno".

---

## 3. Qualidade e discordância do dado de origem (médio-alto)

**O risco:** o CAR é autodeclaratório. Ele contém sobreposições, polígonos inválidos e áreas que não
batem com o SIGEF. Se o produto apresentar isso como verdade única, ele propaga o erro com uma
camada de credibilidade por cima. Isso é pior que não existir.

**Mitigação já decidida (AD-003):**

- O SIGEF tem o rótulo de limite certificado. O CAR tem o rótulo de declaração do proprietário.
- O dossiê exibe e quantifica a divergência, com **zero reconciliação automática**.
- O sistema recalcula a área da geometria e compara com a declarada.
- A ingestão corrige a geometria inválida e marca o registro.

**Sinal de que o risco virou realidade:** um usuário toma decisão errada citando o dossiê.

---

## 4. Dependência de fontes que não controlamos (médio)

**O risco:** os portais mudam endereço, formato e política de acesso sem aviso. O INCRA passou a
exigir login gov.br nos portais interativos em outubro de 2023. Uma quebra silenciosa da ingestão
serve dado velho como se fosse novo.

**Mitigação já decidida (AD-004, AD-005):**

- Base própria: a consulta do usuário não depende de um portal do governo de pé.
- Cada camada carrega a data de extração. Acima de 90 dias, um aviso automático aparece. Acima de
  180 dias, o aviso fica persistente.
- Se uma reingestão produz menos de 90% das feições da versão anterior, o sistema a **rejeita**. A
  versão anterior continua em serviço.

**Sinal de que o risco virou realidade:** uma camada com data de extração parada há meses.

---

## 5. Responsabilidade sobre a decisão do usuário (médio)

**O risco:** alguém compra uma área, descobre um passivo que o dossiê não mostrou e nos
responsabiliza. A precisão posicional do dado público é limitada. A ausência de uma restrição na
nossa base não prova a ausência dela no mundo.

**Mitigação já decidida:**

- O dossiê declara a precisão da fonte. Ele nunca afirma precisão maior que ela.
- O dossiê declara os cruzamentos como indicativos. Eles não substituem levantamento técnico nem
  licenciamento.
- Uma intersecção abaixo de 1% recebe a marca "toque marginal — verificar em campo".
- O PDF carrega a ressalva de que não tem fé pública. Não emitimos laudo nem valuation.

**Sinal de que o risco virou realidade:** o time começa a discutir "quanta certeza dar" em vez
de "quanta incerteza mostrar".

---

## O padrão comum

Quatro dos cinco riscos têm a mesma mitigação de fundo: **declarar a incerteza, não escondê-la**.
Isso não é cautela jurídica defensiva. É o que torna o dossiê útil para uma decisão de dinheiro.
Ninguém pode usar como prova um produto que finge certeza.
