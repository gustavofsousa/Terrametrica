# Cobertura urbana — inventário dos 92 municípios do RJ

> Fecha o item de checklist "inventariar os 92 municípios: quem publica lote cadastral aberto" de
> `docs/research/fontes-de-dados-rj.md`. Consolida a pesquisa entregue pelo usuário em 2026-09-03
> (`levantamento-lotes-cadastrais.md` + 8 CSVs regionais + `triagem_geral_rj.csv` consolidado) mais
> a lacuna de 6 municípios preenchida por pesquisa adicional na mesma data.

## Resultado

| Categoria | Municípios | % |
| --- | --- | --- |
| Publica lote cadastral vetorial aberto (confirmado) | 0 | 0% |
| Parcial — WebGIS/PDF/acesso restrito, sem export confirmado | 6 | 6,6% |
| Ambíguo — precisa verificação manual direta | 9 | 9,9% |
| Não — nenhuma fonte espacial aberta identificada | 75 | 82,4% |
| Excluído do escopo desta pesquisa (RJ capital) | 1 | — |

**Total coberto: 91 dos 92 municípios do estado** (+ Niterói, já tratado à parte como piloto
confirmado em `fontes-de-dados-rj.md`). RJ capital (a capital) foi excluída do escopo desta
pesquisa por instrução do usuário — segue tratada separadamente como candidata a segundo
município via DATA.RIO/IPP (AD-006), granularidade ainda **a verificar**.

## Achado central

**Nenhum município fluminense, fora Niterói, tem download direto confirmado de lote cadastral em
formato vetorial aberto** (SHP/GeoJSON/GPKG/WFS). O cenário dominante é ausência total de geoportal
(82%) — a hipótese de AD-006 ("a maioria não publica") estava certa, e agora tem número: **75 de
91**, não uma suposição.

Os 6 casos "Parcial" (São Gonçalo, Campos dos Goytacazes, Macaé, Volta Redonda, Barra Mansa,
Petrópolis) têm sistema de geoprocessamento ativo, mas nenhum expõe export vetorial confirmado de
lote — são consulta visual (clique no mapa) ou exigem login profissional. **Macaé é o mais
promissor**: portal GeoMacaé tem seção de shapefiles por tema, mas não confirmado se cobre a
camada de lote/parcela especificamente — candidato natural a próxima verificação manual.

## Lacuna preenchida (2026-09-03)

O levantamento original cobriu 84 municípios avaliados + a capital (excluída). Comparado à lista
oficial do IBGE (92 municípios, `servicodados.ibge.gov.br/api/v1/localidades/estados/33/municipios`),
faltavam **6**: Aperibé, Engenheiro Paulo de Frontin, Itaocara, Mendes, Rio das Flores, São
Francisco de Itabapoana. Pesquisados por busca no catálogo ArcGIS Online (0 resultados para todos)
e no catálogo `dadosabertos.rj.gov.br` (só datasets estaduais temáticos que citam o município, sem
camada cadastral) — todos classificados **Não**, coerente com o padrão dos demais municípios
pequenos. Linhas adicionadas ao final de `triagem_geral_rj.csv`.

## Arquivos nesta pasta

- `levantamento-lotes-cadastrais.md` — relatório original completo (metodologia, ressalvas,
  destaques, recomendações, referências)
- `triagem_geral_rj.csv` — tabela consolidada, **91 municípios** (fonte de verdade desta pasta)
- `Metropolitana.csv`, `Baixadas_Litorâneas.csv`, `Norte_Fluminense.csv`, `Médio_Paraíba.csv`,
  `Serrana.csv`, `Costa_Verde.csv`, `Centro-Sul_Fluminense.csv`, `Noroeste_Fluminense.csv` — o
  mesmo dado fatiado por região (redundante com o consolidado, mantido por fidelidade à pesquisa
  original; **não** foram atualizados com os 6 municípios da lacuna — usar o consolidado)

## Próxima ação recomendada (não urgente, não bloqueia MVP)

Os 6 "Parcial" + 9 "Ambíguo" (15 municípios) são os únicos com chance real de virar fonte de dado.
Verificação manual direta (abrir cada portal, testar se existe REST Service ArcGIS oculto por
varredura de subdomínio, ou contato via LAI com a secretaria de planejamento/fazenda) é trabalho
de baixo volume que pode ser feito quando a Fatia urbana (além de Niterói) virar prioridade — não
antes disso.
