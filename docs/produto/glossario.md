# Glossário

Termos que aparecem no produto e na documentação. Escrito para quem não vem de geoprocessamento
nem de direito registral.

## Fontes e sistemas

**SIGEF** — Sistema de Gestão Fundiária do INCRA. Guarda os perímetros de imóveis rurais
**certificados**: alguém mediu com precisão topográfica e o INCRA validou. É o limite
autoritativo no nosso produto.

**SNCI** — sistema anterior ao SIGEF. Seu acervo continua relevante para imóveis certificados
antes da transição.

**Acervo Fundiário** — portal do INCRA de onde se baixam as bases fundiárias em shapefile.

**CAR / SICAR** — Cadastro Ambiental Rural. O proprietário **declara** o perímetro do imóvel e
suas áreas ambientais. É obrigatório, mas autodeclaratório: não passa por certificação. No
produto aparece como declaração, nunca como limite legal.

**INEA** — Instituto Estadual do Ambiente do RJ. Fonte das unidades de conservação estaduais,
corpos d'água e áreas suscetíveis a inundação e deslizamento, nos 92 municípios.

**DATA.RIO / IPP** — portal de dados abertos do município do Rio, mantido pelo Instituto
Pereira Passos. Fonte da camada urbana do MVP.

**GeoPAL** — consulta aos Projetos de Alinhamento (PAL) aprovados no município do Rio.

**ONR** — Operador Nacional do Sistema de Registro Eletrônico de Imóveis, criado pela Lei
13.465/2017. Centraliza o acesso aos cartórios de registro de imóveis do país.

**SREI** — Sistema de Registro Eletrônico de Imóveis, operado pelo ONR.

**MapBiomas** — série histórica de uso e cobertura do solo do Brasil. Uso condicionado à
confirmação de licença comercial.

## Conceitos de terra

**Lote** — unidade urbana de propriedade, com inscrição cadastral no município (é o que paga IPTU).

**Imóvel rural** — unidade rural, identificada por código no SIGEF e por número no CAR. Não
coincide necessariamente com "fazenda" no uso coloquial.

**Matrícula** — o registro do imóvel no cartório. É onde vive a informação de propriedade e de
ônus. **Não é ingerida por este produto.**

**Inscrição cadastral** — a chave do lote no cadastro imobiliário municipal.

**Testada** — a medida da frente do lote, voltada para o logradouro. Determina muito do que se
pode construir.

**APP — Área de Preservação Permanente** — faixa protegida por lei (margem de rio, topo de
morro, encosta íngreme). Restringe uso mesmo em propriedade privada.

**Reserva Legal** — percentual da propriedade rural que deve manter vegetação nativa. No RJ, 20%.

**Unidade de conservação** — área protegida por ato do poder público, com categoria e regras
próprias.

**Sobreposição** — quando dois ou mais imóveis reivindicam a mesma área. Sinal de possível
litígio de limite.

## Conceitos técnicos

**Polígono** — a forma fechada que representa o limite do lote no mapa.

**Shapefile (.shp)** — formato de arquivo de dado geográfico vetorial. Como as fontes públicas
distribuem seus limites. Vem sempre acompanhado de arquivos irmãos (.shx, .dbf).

**GeoJSON** — formato aberto de dado geográfico, legível na web. O que o painel consome.

**CRS / SRC** — sistema de referência de coordenadas: como coordenadas viram posições na Terra.
Armazenamos em SIRGAS 2000 (EPSG:4674), o padrão oficial brasileiro; exibimos em Web Mercator
(EPSG:3857), o que as bibliotecas de mapa esperam.

**Georreferenciamento** — amarrar a geometria de um imóvel a coordenadas reais no terreno.

**Intersecção** — a área comum entre o lote e uma camada de restrição. É a operação que produz
os alertas do dossiê.

**Proveniência** — o registro de qual fonte produziu cada dado e quando ele foi extraído.

## Conceitos jurídicos

**Publicidade registral** — princípio da Lei 6.015/73, art. 17: qualquer pessoa pode obter
certidão do registro **sem declarar motivo ou interesse**. Sustenta a consulta pontual, não a
agregação de base.

**LGPD** — Lei 13.709/2018, de proteção de dados pessoais. Dado público de origem não vira dado
livre para agregação e redistribuição.

**Fé pública** — a qualidade que faz um documento valer como prova por si. Cartório tem; o
dossiê **não tem**, e diz isso em cada exportação.

**Cadeia dominial** — a sequência histórica de proprietários de um imóvel. Fora do escopo desta
versão.

**Ônus e gravames** — restrições registradas sobre o imóvel (hipoteca, penhora, usufruto). Fora
do escopo desta versão.
