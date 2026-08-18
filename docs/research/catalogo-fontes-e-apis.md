# Catálogo de fontes, APIs públicas e geosserviços

**Data:** 2026-08-18 · **Escopo:** Estado do Rio de Janeiro (UF 33)

> **Aviso que vale para o documento inteiro.** O ambiente de desenvolvimento bloqueia HTTPS para
> hosts `.gov.br` (403 na política de egress). **Nenhum endpoint abaixo foi chamado nesta sessão.**
> As URLs vêm de documentação oficial e de fontes secundárias confiáveis, e cada linha carrega um
> nível de confiança. A checklist da Fase 0 continua obrigatória antes de qualquer código.

**Como ler a coluna Acesso:**

| Sigla | Significado | Por que importa |
| --- | --- | --- |
| `WFS` | Web Feature Service — devolve as feições, com filtro espacial e por atributo | Ingestão incremental, sem baixar o país inteiro |
| `WMS` | Web Map Service — devolve imagem renderizada | Só serve para exibir, não para cruzar |
| `REST` | API JSON própria | Melhor caso: barato de automatizar |
| `SHP` | Download de arquivo (shapefile/GeoPackage) | Funciona, mas é lote inteiro e manual |

---

## 1. Camada rural — limites de imóveis

| Fonte | Entrega | Acesso | Confiança | Nota operacional |
| --- | --- | --- | --- | --- |
| **INCRA — SIGEF** | Parcelas certificadas: código do imóvel, área, perímetro | `SHP` `WMS` | Alta | Mais de 1 milhão de parcelas no país, ~262 Mha. Portal interativo exige gov.br prata/ouro desde out/2023; o **download** é relatado como aberto — verificar |
| **INCRA — Acervo Fundiário** | SIGEF + SNCI legado, assentamentos, quilombolas, parcelas públicas | `SHP` `WMS` | Alta | Filtro por UF na origem. Base do perímetro rural do produto |
| **INCRA — SNCR** | Cadastro rural declaratório: área, município, titular | — | Média | **Contém titular. Não ingerir** — ver decisão AD-002 |
| **SICAR / CAR** | Perímetro declarado, APP, Reserva Legal, vegetação nativa, área consolidada, hidrografia, declividade >45°, uso restrito | `SHP` por UF/município | Alta | Download estadual em `car.gov.br/publico/estados/downloads`; consulta pública em `consultapublica.car.gov.br`. Existe também download por número de CAR |

**Armadilha conhecida:** SIGEF e CAR discordam com frequência sobre o mesmo imóvel. Ver AD-003 —
os dois são armazenados, nenhum é reconciliado.

---

## 2. Camada urbana — lotes

| Fonte | Entrega | Acesso | Confiança | Nota operacional |
| --- | --- | --- | --- | --- |
| **SIGeo Niterói** ⭐ piloto | Cadastro imobiliário, plantas de loteamento, base municipal completa | `WFS` `WMS` `REST` `SHP` | **Alta** | ArcGIS Hub em `dados-geoniteroi.opendata.arcgis.com`. Download em CSV, KML, GeoJSON, GeoTIFF, PNG. **A melhor via de ingestão municipal do estado** |
| **DATA.RIO / IPP** | Lotes, logradouros, uso do solo, dinâmica imobiliária | `REST` `SHP` | Alta | Segundo município. Hub ArcGIS. Granularidade de lote a confirmar |
| **GeoPAL** (Rio) | Projetos de Alinhamento aprovados | — | Média | Fonte de testada e alinhamento |
| **Outros 90 municípios** | — | — | **Desconhecida** | Maior incerteza do projeto. Exige inventário um a um |

---

## 3. Camada ambiental e de risco

| Fonte | Entrega | Acesso | Confiança | Licença |
| --- | --- | --- | --- | --- |
| **GEOINEA (INEA-RJ)** | UCs estaduais, APP, corpos d'água, mananciais, suscetibilidade a inundação e deslizamento, relevo — **para os 92 municípios** | `SHP` `WMS` + ArcGIS Online | Alta | A confirmar |
| **ICMBio** | Unidades de conservação federais, cavernas | `WFS` `WMS` via INDE | Alta | Dado aberto federal |
| **ANA** | Massas d'água, hidrografia, saneamento | `WFS` `WMS` `REST` | Alta | `dadosabertos.ana.gov.br` |
| **SGB / CPRM** | **Setorização de risco geológico R3 (alto) e R4 (muito alto)**, por município | `SHP` | Alta | Mapeia apenas onde há edificação habitada. Complemento direto da persona urbana |
| **MapBiomas** | Uso e cobertura do solo, série histórica | `REST` `SHP` | Alta | **CC-BY — livre inclusive para uso comercial**, mediante citação |
| **MapBiomas Alerta** | Alertas de perda de vegetação nativa validados em imagem de alta resolução | `REST` documentada | Alta | CC-BY. `plataforma.alerta.mapbiomas.org/api` |
| **MapBiomas Água** | Série temporal de superfície de água | `REST` (OpenAPI) | Alta | CC-BY. `plataforma.agua.mapbiomas.org/api/docs/` |
| **TerraBrasilis / INPE** | PRODES, DETER | `WFS` em `terrabrasilis.dpi.inpe.br/geoserver/ows` | Alta | Foco amazônico; relevância marginal para o RJ, mas o padrão WFS é exemplar |

**Achado de valor para a persona urbana:** a setorização de risco do SGB/CPRM (R3/R4) é mais
acionável que "suscetibilidade" genérica — ela aponta setores com edificação habitada em risco
alto e muito alto. Vale entrar já na Fase 1.

---

## 4. Camadas de referência e enriquecimento

| Fonte | Entrega | Acesso | Confiança |
| --- | --- | --- | --- |
| **IBGE — API de Malhas** | Malhas municipais, estaduais, distritais em GeoJSON / TopoJSON / SVG | `REST` `v3` | **Alta — documentada** |
| **IBGE — API de Localidades** | UFs, municípios, distritos, regiões metropolitanas | `REST` | **Alta — documentada** |
| **IBGE — CNEFE 2022** | **106,8 milhões de endereços, 100% georreferenciados pela primeira vez**: logradouro, número, CEP, setor censitário, quadra, face, lat/lon, tipo de unidade | `SHP` / microdados | **Alta** | 
| **IBGE — Faces de logradouro / setores censitários** | Geometria de quadra e face | `SHP` | Alta |
| **INDE — Catálogo de Geosserviços** | Catálogo federado de WMS/WFS/WCS de órgãos federais, estaduais e municipais | `WFS` `WMS` | Alta |
| **OpenStreetMap / Overpass** | Edificações, uso do solo, arruamento, POIs | `REST` (Overpass QL) | Alta — **ODbL**, redistribuição comercial permitida sob os termos |
| **BrasilAPI** | CEP, CNPJ, DDD, bancos, IBGE | `REST` open source | Alta |

**CNEFE é o achado silencioso deste levantamento.** É a única base nacional que amarra endereço a
coordenada de forma exaustiva. Para a camada urbana ela resolve o problema que nenhuma prefeitura
resolve: dado que o usuário busque por endereço em vez de clicar no mapa, e nos 91 municípios sem
cadastro aberto, ela sustenta pelo menos uma resposta parcial em vez de silêncio.

> **Cuidado de LGPD:** CNEFE traz nomes de estabelecimentos e tipo de unidade. Ingerir apenas os
> campos de endereço e coordenada; nunca nomes associados a domicílio.

---

## 5. Camada registral

| Fonte | Situação | Confiança |
| --- | --- | --- |
| **ONR / SREI** | Portal para o cidadão: certidão on-line, visualização de matrícula, pesquisa de bens por CPF/CNPJ | Alta que o portal existe |
| **API do ONR para terceiros** | **Não localizada** em nenhuma das buscas | Marcado como incerto — assumimos ausência |

**Serviços comerciais intermediários existem** (revendas de consulta a CAR, CNPJ e matrícula por
API). Podem destravar a Fase 3 sem integração direta, mas movem o risco de LGPD para dentro do
produto em vez de eliminá-lo: continuamos sendo o agregador. Avaliar apenas com parecer jurídico.

---

## 6. Concorrência mapeada

| Quem | O que faz | Leitura |
| --- | --- | --- |
| **Campo Certo** | Due diligence rural automatizada: CAR, IBAMA, embargos, sobreposições em um relatório | Concorrente mais direto na persona agro. Foco em conformidade e passivo, não em exploração pelo mapa |
| Consultorias de regularização fundiária | Serviço humano, por projeto | Mercado que valida a dor; preço e prazo são o nosso contraste |

**Onde nos diferenciamos, à luz disso:** os concorrentes atacam *due diligence rural*, um ato
pontual e caro por imóvel. Nossa proposta é *exploração pelo mapa* — o usuário não sabe qual
imóvel quer analisar até ver o mapa. E somos os únicos com camada urbana no mesmo produto.

**Onde eles nos ganham hoje:** embargos do IBAMA e autuações. Não estão no nosso escopo e são um
sinal forte de passivo. Candidato natural à Fase 2.

---

## 7. Ordem de ataque recomendada

Por relação entre valor entregue e custo de ingestão:

| # | Fonte | Por quê primeiro |
| --- | --- | --- |
| 1 | IBGE Malhas + Localidades | `REST` documentada, resolve o recorte territorial em horas |
| 2 | SIGeo Niterói | `WFS` — prova a camada urbana inteira num município só |
| 3 | INCRA SIGEF (RJ) | Um download, cobre a camada rural do estado inteiro |
| 4 | SICAR (RJ) | Segundo download; destrava APP, Reserva Legal e a divergência |
| 5 | GEOINEA | Cobre os 92 municípios de uma vez nas camadas de restrição |
| 6 | SGB/CPRM setorização | Alto valor para a persona urbana, volume pequeno |
| 7 | CNEFE | Grande, mas destrava busca por endereço e cobertura parcial nos 91 municípios |
| 8 | MapBiomas + Alerta | `REST`, CC-BY, entra sem atrito |
| 9 | OSM / Overpass | Contexto visual e edificações onde não há cadastro |

## Fontes

- [INCRA — imóveis rurais certificados](https://www.gov.br/pt-br/servicos/obter-coordenadas-e-baixar-os-arquivos-dos-imoveis-ruras-certificados) · [SIGEF](https://sigef.incra.gov.br/) · [dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/sistema-de-gestao-fundiaria---sigef)
- [SICAR — consulta pública](https://consultapublica.car.gov.br/) · [downloads por estado](https://www.car.gov.br/publico/estados/downloads)
- [HUB SIGeo Niterói](https://www.sigeo.niteroi.rj.gov.br/) · [ArcGIS Hub Niterói](https://dados-geoniteroi.opendata.arcgis.com/)
- [DATA.RIO](https://www.data.rio/)
- [INEA — informações geoespaciais](http://www.inea.rj.gov.br/biodiversidade-territorio/informacoes-geoespaciais/)
- [SGB/CPRM — setorização de riscos geológicos](https://www.sgb.gov.br/saiba-mais-setorizacao-de-riscos-geologicos)
- [ICMBio — dados geoespaciais](https://www.gov.br/icmbio/pt-br/assuntos/dados_geoespaciais) · [ANA — dados abertos](https://dadosabertos.ana.gov.br/)
- [IBGE — API de malhas](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3) · [API de localidades](https://servicodados.ibge.gov.br/api/docs/localidades) · [CNEFE](https://www.ibge.gov.br/estatisticas/sociais/populacao/38734-cadastro-nacional-de-enderecos-para-fins-estatisticos.html)
- [INDE — catálogo de geosserviços](https://inde.gov.br/CatalogoGeoservicos) · [visualizador](https://visualizador.inde.gov.br/)
- [MapBiomas — termos de uso](https://brasil.mapbiomas.org/termos-de-uso/) · [API Alerta](https://plataforma.alerta.mapbiomas.org/api) · [API Água](https://plataforma.agua.mapbiomas.org/api/docs/)
- [TerraBrasilis / INPE — geosserviços](https://terrabrasilis.dpi.inpe.br/tag/geoservicos/)
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) · [BrasilAPI](https://github.com/brasilapi/brasilapi)
- [Campo Certo — due diligence rural automatizada](https://campocerto.basis.app.br/)
