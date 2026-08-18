# Protótipo — Dossiê no Mapa

Mapa arrastável em que clicar num polígono abre o dossiê do lote. Existe para validar a
**interação** e o **layout do dossiê** antes de construir a ingestão de dados.

```bash
# abrir
open prototipos/mapa-dossie/index.html      # ou: python3 -m http.server

# testar a geometria (sem dependências)
node prototipos/mapa-dossie/tests/geom.test.mjs
```

## O que é real e o que não é

| Real | Sintético |
| --- | --- |
| A interação: arrastar, zoom na posição do cursor, pinça, seleção | Os polígonos — gerados com PRNG semeado, não são cadastro |
| O cálculo de área e perímetro (fórmula do agrimensor) | Os códigos SIGEF, inscrições cadastrais e nomes de fazenda |
| O recorte de intersecção (Sutherland–Hodgman, exato para clip convexo) | As manchas de restrição e as datas de extração |
| O esquema dos campos do dossiê e as fontes atribuídas a cada um | |
| As regras do produto: toque marginal <1%, limiar de divergência 5%, cobertura declarada | |

**Por que dado sintético.** O ambiente de desenvolvimento bloqueia HTTPS para hosts `.gov.br`,
então não foi possível ingerir base real. As regras testadas aqui independem disso.

## Regras do produto exercitadas

- **Toque marginal** — intersecção abaixo de 1% da área do lote é marcada "verificar em campo",
  em vez de virar alerta cheio. Evita alarme falso por erro posicional da fonte.
- **Divergência SIGEF × CAR** — os dois perímetros são desenhados (cheio e tracejado) e a
  diferença é quantificada em hectares e percentual. Acima de 5%, alerta. Nunca há reconciliação.
- **Proveniência por campo** — cada linha do dossiê carrega fonte e data de extração.
- **Cobertura declarada** — clicar onde não há polígono devolve a tabela de cobertura por
  município, não um vazio ambíguo.
- **Fora de cobertura** — clique fora do RJ é recusado explicitamente.

## Como isso vira produção

O protótipo desenha em canvas porque precisa ser um arquivo único e offline. Em produção, a
stack levantada em [`../../docs/research/stack-open-source.md`](../../docs/research/stack-open-source.md)
substitui o motor: **MapLibre GL JS** com base em **PMTiles** e as camadas próprias servidas como
tile vetorial pelo **PostGIS** (`ST_AsMVT`). O recorte de intersecção sai do navegador e vira
`ST_Intersection` materializado por versão de base.
