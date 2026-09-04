# Dados brutos — RJ (Fase 0)

> Esta pasta está no `.gitignore` (regra `data/raw/`) — os arquivos aqui **nunca vão pro repo**.
> Existe só no disco local. Se sumir, dá pra rebaixar seguindo os links abaixo; nada aqui é fonte
> única de verdade — a fonte de verdade é o portal oficial.

Baixados em 2026-09-03 durante a verificação da Fase 0 (ver
`docs/research/fontes-de-dados-rj.md` para a análise/medição completa desses arquivos).

| Arquivo | Fonte | O que é |
| --- | --- | --- |
| `Sigef-Brasil-RJ.zip` | [certificacao.incra.gov.br/csv_shp/export_shp.py](https://certificacao.incra.gov.br/csv_shp/export_shp.py) (login GOV.BR) | SIGEF — "Imóvel certificado SIGEF Total", RJ. 14.664 feições, EPSG:4674. |
| `AREA-IMOVEL.zip` | [consultapublica.car.gov.br/publico/estados/downloads](https://consultapublica.car.gov.br/publico/estados/downloads) (RJ → Perímetros dos imóveis) | CAR — perímetro declarado dos imóveis rurais. 69.105 feições, EPSG:4674. |
| `APPS.zip` | idem, camada "Área de Preservação Permanente" | CAR — APP. Não medido em detalhe ainda. |
| `AREA-CONSOLIDADA.zip` | idem, camada "Área Consolidada" | CAR — área consolidada. Não medido em detalhe ainda. |
| `AREA-POUSIO.zip` | idem, camada "Área de Pousio" | CAR — área de pousio. Não medido em detalhe ainda. |
| `HIDROGRAFIA.zip` | idem, camada "Hidrografia" | CAR — hidrografia. Não medido em detalhe ainda. |
| `RESERVA-LEGAL.zip` | idem, camada "Reserva Legal" | CAR — reserva legal. Não medido em detalhe ainda. |
| `SERVIDAO-ADMINISTRATIVA.zip` | idem, camada "Servidão Administrativa" | CAR — servidão administrativa. Não medido em detalhe ainda. |
| `USO-RESTRITO.zip` | idem, camada "Uso Restrito" | CAR — uso restrito. Não medido em detalhe ainda. |
| `VEGETACAO-NATIVA.zip` | idem, camada "Remanescente de Vegetação Nativa" | CAR — vegetação nativa remanescente. Não medido em detalhe ainda. |

Só `Sigef-Brasil-RJ.zip` e `AREA-IMOVEL.zip` foram efetivamente medidos (feições, CRS, validade,
sobreposição SIGEF×CAR) — as outras 7 camadas do CAR foram baixadas juntas (mesmo fluxo, mesmo
captcha) mas ainda não analisadas. Servem de amostra pronta para quando a Fatia 2 (ingestão) for
desenhada, sem precisar repetir o login/captcha.
