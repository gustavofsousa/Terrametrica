# Modelo de domínio — estado atual

Este documento é o mapa visual de `src/terrametrica/dominio/modelos.py`, o hub do vocabulário ubíquo
do projeto. A definição de cada termo em linguagem de produto (SIGEF, CAR, APP, testada...) está no
[glossário](produto/glossario.md). Este arquivo mostra a **forma** dos tipos. Ele não redefine o
vocabulário.

Dois princípios de `AGENTS.md` moldam tudo abaixo:

- **Tornar estados ilegais irrepresentáveis** — conjuntos fechados (enum/união), não string/bool
  livres.
- **Validar no boundary** — os construtores (`__post_init__`) rejeitam dado inválido na borda. O
  código interno confia no tipo.

---

## Identidade do lote — união fechada

```mermaid
classDiagram
    class LoteRural {
        +str lote_id
        +tuple municipios
        +str codigo_sigef
        +SituacaoCertificacao situacao
        +AreaHa area
        +float perimetro_m
        +str denominacao
    }
    class LoteUrbano {
        +str lote_id
        +str municipio
        +str inscricao_cadastral
        +AreaM2 area
        +float perimetro_m
        +str logradouro
        +str bairro
    }
    class LoteHit
    note for LoteHit "uniao fechada: LoteRural | LoteUrbano"
    LoteHit <|-- LoteRural
    LoteHit <|-- LoteUrbano
```

`LoteRural` guarda a área em **hectares** (unidade do imóvel rural). `LoteUrbano` guarda a área em
**m²** (unidade do lote urbano). A montagem do dossiê normaliza para m² internamente
(`_area_do_lote_m2`), só para comparar com a área da interseção. Ela nunca converte a área exibida ao
usuário. Essa área mantém a unidade natural de cada tipo.

NOTE: Este documento descreve o snapshot da Fatia 2, como `docs/arquitetura.md`. Na época, `LoteUrbano`
existia no domínio sem linha de ingestão nem tabela Postgres.

---

## Resultado da montagem — união fechada de 4 casos

```mermaid
classDiagram
    class Dossie {
        +LoteHit lote
        +tuple itens_restricao
        +Mapping proveniencia
        +tuple camadas_ausentes
        +tuple camadas_sem_cobertura
        +tuple camadas_desatualizadas
        +str ressalva
    }
    class ForaDoRJ {
        +str mensagem
    }
    class SemLote {
        +str municipio
        +tuple cobertura
        +str mensagem
    }
    class Sobreposicao {
        +tuple candidatos
        +str mensagem
    }
    class ResultadoDossie
    note for ResultadoDossie "uniao fechada: Dossie | SemLote | Sobreposicao | ForaDoRJ"
    ResultadoDossie <|-- Dossie
    ResultadoDossie <|-- SemLote
    ResultadoDossie <|-- Sobreposicao
    ResultadoDossie <|-- ForaDoRJ

    class ItemRestricao {
        +TipoRestricao tipo
        +str nome
        +AreaM2 area_intersecao
        +float pct_do_lote
        +bool marginal
    }
    class CoberturaCamada {
        +Camada camada
        +bool tem_dado
        +date data_extracao
    }
    class Proveniencia {
        +str fonte
        +date data_extracao
        +str link_oficial
    }

    Dossie --> LoteHit
    Dossie --> ItemRestricao
    Dossie --> Proveniencia
    SemLote --> CoberturaCamada
    Sobreposicao --> LoteHit
```

`ResultadoDossie = Dossie | SemLote | Sobreposicao | ForaDoRJ` é o tipo de retorno de
`montar_dossie`. A árvore de decisão completa está em `docs/arquitetura.md`. A união fechada impede,
no type-check (`mypy strict`), que o código que consome o dossiê esqueça um dos quatro casos.

Dentro de `Dossie`, o código trata três casos como diferentes. Eles não são sinônimos de "sem dado":

| Campo | Significa |
| --- | --- |
| `camadas_sem_cobertura` | O município não tem essa camada mapeada (fato estrutural, DOS-11) |
| `camadas_ausentes` | A camada existe no produto, mas esta versão não tem carimbo de proveniência (DOS-12) |
| `camadas_desatualizadas` | Tem proveniência, mas a extração passou de 90 dias (DOS-13) |

Nenhum dos três aparece como "vazio" ambíguo (AD-005: proveniência é requisito, não enfeite).

---

## Value objects e enums de suporte

```mermaid
classDiagram
    class Coordenada {
        +float lat
        +float lon
    }
    class AreaM2 {
        +float valor
        +em_hectares() AreaHa
    }
    class AreaHa {
        +float valor
        +em_metros_quadrados() AreaM2
    }
    class VersaoBase {
        +str id
        +date criada_em
    }
    class Camada {
        <<enumeration>>
        LOTE_RURAL
        LOTE_URBANO
        APP
        RESERVA_LEGAL
        UNIDADE_CONSERVACAO
        INUNDACAO
        DESLIZAMENTO
        CORPO_DAGUA
    }
    class TipoRestricao {
        <<enumeration>>
        APP
        RESERVA_LEGAL
        UNIDADE_CONSERVACAO
        INUNDACAO
        DESLIZAMENTO
        CORPO_DAGUA
        +camada() Camada
    }
    TipoRestricao --> Camada : camada derivada, sem drift
```

`Coordenada` valida a faixa global de lat/lon no `__post_init__`. A contenção no RJ (DOS-05) é
responsabilidade do `Protocol` `LimiteEstado`, não deste value object. Assim o produto pode federar
outras UFs no futuro sem reescrever `Coordenada`. `AreaM2`/`AreaHa` rejeitam valor negativo e se
convertem entre si. Mas eles **nunca se misturam sem conversão explícita**. Não há um tipo `Area`
genérico que esconda a unidade.

`TipoRestricao.camada` é uma property, não um campo duplicado. A camada de origem de uma restrição
sempre sai do próprio tipo. Por isso as duas listas nunca divergem por esquecimento.

---

## Gate jurídico (P2) — sem dado pessoal

```mermaid
classDiagram
    class Conta {
        +str id
        +PapelConta papel
    }
    class PapelConta {
        <<enumeration>>
        CONSULTA
        HABILITADO_JURIDICAMENTE
    }
    class EntradaAuditoria {
        +str id
        +datetime ts
        +str conta_id
        +TipoEventoAuditoria tipo
        +str finalidade
        +str lote_id
        +str promovido_por
        +str credencial_verificada
    }
    class ResultadoAcesso
    note for ResultadoAcesso "uniao fechada: Permitido | Negado"
    class Permitido
    class Negado
    ResultadoAcesso <|-- Permitido
    ResultadoAcesso <|-- Negado

    class EstadoSecao
    note for EstadoSecao "unica variante hoje: Indisponivel<br/>pronta para Disponivel futura sem quebrar assinatura"
    class Indisponivel
    EstadoSecao <|-- Indisponivel

    Conta --> PapelConta
    Conta --> ResultadoAcesso
    Conta --> EntradaAuditoria
```

O detalhe estrutural que carrega a decisão de produto (AD-002): **`Conta` não tem nenhum campo que
guarde nome, CPF ou CNPJ de proprietário.** A ausência de dado pessoal é uma garantia de tipo. Não é
uma regra validada em runtime que alguém pode esquecer de checar. Para adicionar esse dado, é
preciso mudar a classe.

---

## Onde o vocabulário vira comportamento

O domínio (`dominio/modelos.py`) não faz I/O nem contém regra de decisão. Ele guarda só a forma dos
dados. As regras que operam sobre essa forma vivem em módulos separados:

| Módulo | O que decide |
| --- | --- |
| `dossie/montagem.py` | A árvore de 4 ramos que produz `ResultadoDossie` |
| `geometria/regras.py` | `classificar_intersecao` (marginal < 1%) e `avaliar_divergencia` (SIGEF × CAR, alerta > 5%) |
| `autorizacao/regras.py` | `avaliar_acesso_registral` e `estado_secao_proprietario` |

A ligação desses módulos aos *ports* e adapters está em `docs/arquitetura.md`.
