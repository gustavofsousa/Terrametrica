# Stack open source

Levantamento do que já existe pronto e maduro, para não reconstruir nada que a comunidade
geoespacial resolveu melhor. Uma recomendação por camada, com a alternativa relevante e o motivo.

> Decisões de arquitetura são da fase Design. Este documento é insumo, não decisão — exceto onde
> diz "decidido", que reflete o log em `.specs/STATE.md`.

---

## 1. Ingestão

| Papel | Recomendado | Alternativa | Por quê |
| --- | --- | --- | --- |
| Acesso a bases oficiais brasileiras | **geobr** (IPEA) | requisição direta | Cobre 27 conjuntos oficiais com geometria atualizada, projeção e topologia **harmonizadas**. Existe em R e Python. Poupa semanas de limpeza |
| Leitura e conversão de formatos | **GDAL / OGR** | — | Padrão de fato. Lê shapefile, GeoPackage, KML, GeoJSON e escreve direto no PostGIS via `ogr2ogr` |
| Manipulação em memória | **GeoPandas + Shapely** | — | Validação, correção de geometria, cálculo de área e intersecção antes de gravar |
| Reprojeção | **pyproj** | — | SIRGAS 2000 (EPSG:4674) ↔ Web Mercator (EPSG:3857) ↔ UTM para cálculo de área |
| Consumo de WFS | **OWSLib** | requisição HTTP direta | Essencial para Niterói, ICMBio e ANA: paginação e filtro espacial sem escrever o protocolo à mão |
| Dados do OSM | **Overpass API** + **osm2pgsql** | extratos do Geofabrik | Edificações e arruamento onde não há cadastro municipal. ODbL |

**Por que geobr primeiro:** o valor dele não é baixar — é a harmonização. Bases oficiais
brasileiras chegam com projeções inconsistentes e topologia quebrada; o geobr já resolveu isso
para os conjuntos que cobre.

---

## 2. Armazenamento e processamento

| Papel | Recomendado | Alternativa | Por quê |
| --- | --- | --- | --- |
| Banco espacial | **PostgreSQL + PostGIS** | — | *Decidido (AD-004).* Índice GiST, `ST_Intersection`, `ST_Area` em geografia, e `ST_AsMVT` para servir tiles direto do banco |
| Análise exploratória | **DuckDB + extensão spatial** | — | Ler shapefile e Parquet sem carregar no banco. Ideal para a Fase 0: medir uma base antes de decidir ingerir |
| Validação de geometria | `ST_IsValid` / `ST_MakeValid` | GeoPandas | O CAR tem polígonos inválidos. Corrigir **na ingestão** e marcar o registro |

**Operação que sustenta o produto inteiro:** `ST_Intersection(lote, restrição)` com índice GiST.
É ela que transforma "público mas disperso" em "cruzado em milissegundos". Cache do resultado por
versão de base, não recálculo por consulta.

---

## 3. Servir o mapa

Aqui está o achado mais útil do levantamento.

| Papel | Recomendado | Alternativa | Por quê |
| --- | --- | --- | --- |
| Biblioteca de mapa | **MapLibre GL JS** | Leaflet, OpenLayers | Fork livre do Mapbox GL, sem chave de API e sem licença proprietária. Renderiza tile vetorial em GPU — é o "arrastar como Google Maps" |
| Mapa base | **PMTiles + Protomaps** | tile server próprio, Mapbox | **Um único arquivo estático** com o mapa base inteiro, lido pelo navegador por HTTP range request. Sem servidor de tiles, sem banco, sem chave de API. Hospeda em S3/R2/CDN |
| Tiles das nossas camadas | **`ST_AsMVT` no PostGIS** via **Martin** | pg_tileserv, tegola | Martin é o mais rápido dos servidores de tile sobre PostGIS; pg_tileserv é mais simples de configurar |
| Pré-geração de tiles | **tippecanoe** | — | Para camadas que mudam pouco (limites municipais, UCs): gerar uma vez, servir por CDN |
| Geometria no cliente | **Turf.js** | — | Medições e testes espaciais leves no navegador, sem ida ao servidor |

**Por que isso importa mais do que parece.** A referência do produto é o Google Maps, mas
depender do Google significa chave de API, cota, custo por carregamento e termos que restringem
o que se pode fazer com o dado exibido. MapLibre + PMTiles entrega a mesma sensação de uso com
**zero dependência proprietária** — coerente com a tese de ser dono do próprio motor de dados.

**Combinação prática:** mapa base em PMTiles estático + nossas camadas em MVT dinâmico do
PostGIS. O base nunca muda entre reingestões; as camadas mudam. Separá-los evita regerar
gigabytes por causa de um polígono corrigido.

---

## 4. Publicação de dados e API

| Papel | Recomendado | Alternativa | Por quê |
| --- | --- | --- | --- |
| API geoespacial padronizada | **pygeoapi** | GeoServer | Implementa OGC API Features. Relevante quando a Fase 4 vender o motor para terceiros |
| Servidor OGC completo | **GeoServer** | — | Maduro e pesado. Só se precisarmos publicar WMS/WFS para fora |
| Catálogo de camadas | **STAC** | — | Padrão para versionar e datar coleções — encaixa direto na exigência de proveniência |

**STAC merece atenção.** Nossa regra de "fonte e data em cada campo" é, no fundo, um problema de
catálogo de dados versionado. STAC é o padrão que a comunidade já construiu para isso; adotá-lo
evita inventar um esquema de metadados caseiro.

---

## 5. Ferramentas de trabalho

| Papel | Recomendado | Por quê |
| --- | --- | --- |
| Inspeção visual | **QGIS** | Abrir a base bruta e olhar antes de escrever código de ingestão. Insubstituível na Fase 0 |
| Consulta exploratória OSM | **Overpass Turbo** | Testar uma consulta Overpass no navegador antes de automatizar |
| Conversão pontual | **`ogr2ogr`** | Uma linha resolve o que uma tarde de script resolveria pior |

---

## 6. O que NÃO usar, e por quê

| Tentação | Problema |
| --- | --- |
| Google Maps Platform como base | Chave, cota, custo por carregamento e termos que restringem o uso do dado exibido. Contraria a tese do produto |
| Mapbox GL JS (v2+) | Licença proprietária desde a v2. MapLibre é o fork livre e resolve o mesmo |
| Servir GeoJSON cru dos polígonos para o navegador | O estado do RJ em GeoJSON derruba o navegador. Tile vetorial existe exatamente por isso |
| Recalcular intersecção a cada consulta | `ST_Intersection` sobre camadas grandes é caro. Materializar por versão de base |
| Reconstruir download e limpeza que o geobr já faz | Trabalho sem diferencial competitivo |

---

## 7. Esboço de arquitetura

```
FONTES OFICIAIS                 INGESTÃO                ARMAZENAMENTO
INCRA/SIGEF  ──┐
SICAR/CAR    ──┤                geobr                  ┌──────────────┐
SIGeo Niterói──┼──►  OWSLib / ogr2ogr / GDAL  ──►      │ PostgreSQL   │
GEOINEA      ──┤     GeoPandas + Shapely (validação)   │ + PostGIS    │
SGB/CPRM     ──┤     pyproj (SIRGAS 2000)              │ versionado   │
IBGE/CNEFE   ──┤                                       │ por extração │
MapBiomas    ──┘                                       └──────┬───────┘
                                                              │
                                          ┌───────────────────┴─────────┐
                                          │                             │
                                    ST_AsMVT → Martin            API do dossiê
                                          │                             │
                                          ▼                             ▼
                                   ┌─────────────────────────────────────┐
                                   │  MapLibre GL JS                     │
                                   │  base: PMTiles estático (Protomaps) │
                                   │  camadas: MVT do PostGIS            │
                                   └─────────────────────────────────────┘
```

## Fontes

- [geobr — IPEA (R e Python)](https://github.com/ipeaGIT/geobr) · [documentação](https://ipeagit.github.io/geobr/)
- [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/) · [PMTiles no MapLibre](https://maplibre.org/maplibre-gl-js/docs/examples/pmtiles-source-and-protocol/)
- [Protomaps — o mapa aberto em um arquivo](https://protomaps.com/api) · [PMTiles docs](https://docs.protomaps.com/pmtiles/maplibre)
- [PostGIS — vector tiles dinâmicos](https://www.crunchydata.com/blog/dynamic-vector-tiles-from-postgis)
- [Comparativo tegola / martin / pg_tileserv](https://dev.to/mierune/comparing-postgis-backend-vectortile-servers-tegolamartinpgtileserv-5c6n)
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) · [Overpass Turbo](https://overpass-turbo.eu/)
- [BrasilAPI](https://github.com/brasilapi/brasilapi)
