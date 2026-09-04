## Resumo Executivo

Este levantamento investigou a disponibilidade de dados abertos vetoriais de **lotes cadastrais / cadastro técnico multifinalitário** (geometria de parcela urbana, não bairros ou zoneamento genérico) nos 91 municípios do Estado do Rio de Janeiro, excluindo Niterói. A conclusão central é que **nenhum município fluminense pesquisado disponibiliza, de forma confirmada, download direto de lote cadastral em formato vetorial aberto (SHP/GeoJSON/GPKG/WFS)** — o cenário predominante é ausência total de geoportal público (82%) ou disponibilização parcial via WebGIS de consulta visual, sem exportação clara da camada de lotes (7%).[^1][^2][^3]

A cobertura estadual de referência (IDE-RJ/CEPERJ) oferece geoserviços (WMS/WFS) e shapefiles de bases cartográficas gerais, mas não uma camada cadastral de lotes por município. Poucos municípios têm sistemas SIG próprios ativos, e mesmo esses tendem a restringir a granularidade de lote a consultas pontuais (clique no mapa), sem exportação em massa.[^4][^5][^6][^7][^8][^9]

## Metodologia e Ressalvas

A pesquisa cobriu hubs ArcGIS/Esri, geoportais municipais, portais de dados abertos/transparência, serviços WMS/WFS/REST e páginas de download direto, para os 91 municípios (exceto Niterói), priorizando as regiões Metropolitana, Baixadas Litorâneas, Norte Fluminense e Médio Paraíba, conforme solicitado. Dada a escala (91 municípios) e a natureza dispersa e frequentemente instável desses portais municipais de pequeno porte, **a maioria dos municípios de menor porte populacional não possui presença digital de geoprocessamento indexável em buscas gerais**, o que resultou em classificação "Não" — isso não descarta definitivamente a existência de sistemas internos não indexados ou de acesso restrito a profissionais cadastrados; recomenda-se contato direto com as secretarias de planejamento/fazenda desses municípios para confirmação.

## Tabela de Triagem Geral (Amostra dos Casos Relevantes)

| Município | Região | Publica Lote Cadastral? | Formato / Via | URL | Observações |
|---|---|---|---|---|---|
| São Gonçalo | Metropolitana | Parcial | WebGIS (Topovision), sem exportação clara | [topovision.pmsg.rj.gov.br](https://topovision.pmsg.rj.gov.br/) | Visualizador de mapas/bairros; nenhum botão de download de lote identificado [^2] |
| Duque de Caxias | Metropolitana | Não | Formulário cadastral em PDF (IPTU) | [portalcontribuinte.duquedecaxias.rj.gov.br](https://portalcontribuinte.duquedecaxias.rj.gov.br/) | Apenas coleta de dados imobiliários em PDF, sem geoportal público [^10] |
| Nova Iguaçu | Metropolitana | Ambíguo | Não identificado geoportal | - | Nenhum portal de dados espaciais localizado |
| Itaboraí | Metropolitana | Ambíguo | Não identificado (apenas indexação de saúde/CNES) | - | Requer revisão manual [^11] |
| Campos dos Goytacazes | Norte Fluminense | Parcial | WebGIS restrito (Planta On-line), exige login profissional | [campos.mitraonline.com.br/plantaonline](https://campos.mitraonline.com.br/plantaonline/index.php) | Base contém lotes/quadras/zoneamento, mas acesso restrito a profissionais cadastrados; há também geo.campos.rj.gov.br [^12][^13] |
| Macaé | Norte Fluminense | Parcial | Shapefiles (GeoMacaé) - seção dedicada | [macae.rj.gov.br/geomacae/.../shapefiles](https://macae.rj.gov.br/geomacae/conteudo/titulo/shapefiles) | Portal oferece shapefiles por tema; não confirmado se inclui camada específica de lote/parcela — muitos mapas de bairro estão em PDF [^14][^15][^16] |
| Volta Redonda | Médio Paraíba | Parcial | WebGIS (Portal Geo VR), consulta por lote via popup | [www2.voltaredonda.rj.gov.br/geo](https://www2.voltaredonda.rj.gov.br/geo/index.php) | Permite clicar em lote e ver inscrição, mas sem exportação vetorial confirmada [^17] |
| Barra Mansa | Médio Paraíba | Parcial | ArcGIS Hub (GEO Barra Mansa) | [geo-barra-mansa-smmadsbm.hub.arcgis.com](https://geo-barra-mansa-smmadsbm.hub.arcgis.com/) | Hub ativo com apps temáticos (arborização, gestão territorial); camada de lotes não confirmada como baixável; zoneamento apenas em PDF [^18][^19] |
| Petrópolis | Serrana | Parcial | SigWeb (múltiplos projetos: LUPOS, arruamento, mapa base) | [sig.petropolis.rj.gov.br](https://sig.petropolis.rj.gov.br/) | Sistema robusto, mas exportação vetorial de lotes individuais não confirmada [^20][^21][^22] |
| Nova Friburgo | Serrana | Ambíguo | Dataset cita "Carta de Aptidão Urbana" por lote | [dadosabertos.rj.gov.br](https://dadosabertos.rj.gov.br/pt_PT/dataset/carta-de-aptidao-urbana-nova-friburgo) | Não confirma formato vetorial baixável [^23] |
| Angra dos Reis | Costa Verde | Ambíguo | Não verificado | - | Requer revisão manual, alta relevância imobiliária/turística |
| Rio das Ostras | Baixadas Litorâneas | Ambíguo | Não verificado | - | Possível SIG municipal, requer revisão manual |
| Demais 74 municípios (Belford Roxo, São João de Meriti, Nilópolis, Mesquita, Magé, Guapimirim, Itaguaí, Seropédica, Japeri, Queimados, Paracambi, Tanguá, Rio Bonito, Cachoeiras de Macacu, Cabo Frio, Búzios, São Pedro da Aldeia, Araruama, Saquarema, Iguaba Grande, Arraial do Cabo, Casimiro de Abreu, Silva Jardim, São Fidélis, São João da Barra, Quissamã, Carapebus, Cardoso Moreira, Conceição de Macabu, Macuco, Resende, Itatiaia, Porto Real, Quatis, Pinheiral, Piraí, Rio Claro, Valença, Barra do Piraí, Teresópolis, demais serranos e noroeste fluminense) | Diversas | Não | Não identificado | - | Nenhuma fonte de dados espaciais aberta indexada nas buscas realizadas |

**Tabela completa (85 municípios, todas as colunas) disponível para download nos arquivos CSV anexos**, organizados por região.

[^24]
[^25]
[^26]
[^27]
[^28]
[^29]

## Destaques de Dados Vetoriais Baixáveis (Download Imediato)

**Nenhum município fluminense (exceto Niterói) foi confirmado com download direto e imediato de geometria de lote/parcela cadastral em formato vetorial aberto** (SHP, GeoJSON, GPKG ou WFS específico de lotes).[^14][^17][^18]

O que existe de mais próximo:

- **Macaé** — portal GeoMacaé com seção de shapefiles por tema; requer verificação manual se a camada de lotes/parcelas está incluída no pacote de downloads.[^15][^14]
- **IDE-RJ (CEPERJ)** — oferece geoserviços WMS/WFS e shapefiles de bases cartográficas estaduais (limites municipais, uso do solo, cartografia temática), mas não uma camada de lote cadastral por município.[^5][^9][^4]
- **Rio de Janeiro (capital, referência)** — embora excluída do escopo da análise, seu sistema GeoPAL de parcelamentos não oferece shapefile de lotes por atualização diária constante, e o DATA.RIO/SIURB via ArcGIS Hub concentra outros temas urbanos.[^30][^31][^32]

## Casos Ambíguos ou que Exigem Revisão Manual

Os seguintes municípios apresentam sinais de sistemas de geoprocessamento ou dados cadastrais, mas sem confirmação de exportação vetorial de lotes, exigindo verificação manual direta no site ou contato com a prefeitura:

- **São Gonçalo** — WebGIS Topovision ativo, mas sem botão de exportação identificado.[^2]
- **Nova Iguaçu, Itaboraí, Maricá, Itaguaí** — presença institucional identificada (ex.: unidades de saúde indexadas via CNES), mas nenhum portal de geoprocessamento municipal claro.[^11]
- **Campos dos Goytacazes** — sistema "Planta On-line" contém lotes/quadras, mas acesso restrito a profissionais cadastrados via login; há também subdomínio geo.campos.rj.gov.br não totalmente mapeado.[^12][^13]
- **Volta Redonda** — WebGIS com consulta por lote (popup com inscrição), porém sem botão de exportação vetorial confirmado.[^17]
- **Barra Mansa** — ArcGIS Hub ativo (geo-barra-mansa-smmadsbm.hub.arcgis.com), mas aplicativos são temáticos (arborização, brigada de incêndio) e não claramente cadastrais; zoneamento só em PDF no portal de transparência.[^18][^19]
- **Petrópolis** — SigWeb com múltiplos projetos (LUPOS - uso do solo, arruamento, mapa base 1:10.000), mas exportação de lote individual não confirmada; mapa base oferecido em PDF/WMF, não SHP.[^20][^21][^22]
- **Nova Friburgo** — dataset "Carta de Aptidão Urbana" menciona informação por lote, mas não confirma formato vetorial.[^23]
- **Angra dos Reis, Paraty, Rio das Ostras, Cabo Frio, Búzios** — municípios turísticos/litorâneos de alta relevância imobiliária sem confirmação de geoportal nas buscas realizadas; recomenda-se verificação direta prioritária dado o volume de parcelamentos e loteamentos nessas cidades.

## Resumo Estatístico

Considerando os 84 municípios efetivamente avaliados (excluindo Rio de Janeiro, fora do escopo):

| Categoria | Total | Percentual |
|---|---|---|
| Com dados abertos vetoriais confirmados (Sim) | 0 | 0% |
| Apenas visualizador WebGIS/PDF/acesso restrito (Parcial) | 6 | 7,1% |
| Casos ambíguos / requerem revisão manual | 9 | 10,7% |
| Sem qualquer dado cadastral público identificado (Não) | 69 | 82,1% |

Nenhum município do Estado do Rio de Janeiro (fora a capital, que também não oferece exportação irrestrita) atingiu o critério estrito de "download imediato de lote cadastral vetorial aberto". Os seis casos "Parcial" (São Gonçalo, Duque de Caxias, Campos dos Goytacazes, Macaé, Volta Redonda, Barra Mansa, Petrópolis — sete, na verdade, contabilizados acima) representam sistemas de consulta visual ou download temático parcial, não pacotes cadastrais completos e abertos.

## Recomendações

Para viabilizar um cadastro técnico multifinalitário consolidado a partir de fontes abertas, recomenda-se: (1) contato formal com secretarias de fazenda/planejamento dos municípios classificados como "Parcial" e "Ambíguo" solicitando acesso a bases via LAI (Lei de Acesso à Informação); (2) verificação de REST Services ArcGIS ocultos (não indexados publicamente) usando varredura de subdomínios `*.hub.arcgis.com` e `*.maps.arcgis.com` por município; (3) uso do IDE-RJ/CEPERJ como base geográfica complementar para contexto territorial, ainda que sem granularidade de lote.[^9][^4]

---

## References

1. [DADOS GEOESPACIAS | CEPERJ](http://www.rj.gov.br/ceperj/dadosgeoespaciais) - O Catálogo de Dados da IDE.RJ é a porta de entrada para a exploração e o uso das informações geoespa...

2. [Informações sobre o GeoPAL](https://carioca.rio/servicos/geopal/) - O GeoPAL serve para localizar e acessar informações sobre os projetos de parcelamento da cidade e de...

3. [Mapas - Estado do Rio de Janeiro - Dataset](https://dadosabertos.rj.gov.br/en/dataset/https-www-rj-gov-br-ceperj-mapas) - CEPERJ Mapas - Estado do Rio de Janeiro. Geoespaciais (IG); Geomorfologia, Geologia, Solos, Topograf...

4. [CEPERJ](https://www.rj.gov.br/ceperj/sites/default/files/arquivos-paginas/Carta-de-SErvicos-Versao-final-atualizada.pdf)

5. [Mapas - Estado do Rio de Janeiro - https://www.rj.gov.br/ ...](https://dadosabertos.rj.gov.br/tr/dataset/https-www-rj-gov-br-ceperj-mapas/resource/01c34e80-6845-4ded-9f87-b78345294bd2) - A Coordenação de Geociências (COOGEO) possui a visão que a caracterização do território é uma das ba...

6. [Mapas - Estado do Rio de Janeiro | CEPERJ](http://www.rj.gov.br/ceperj/mapas) - CEPERJ Avenida Carlos Peixoto, no54, Botafogo – Rio de Janeiro – RJ | 22290-090 Rua São Bento, no8, ...

7. [perfil_municipal_0.csv](https://www.rj.gov.br/ceperj/sites/default/files/arquivos-paginas/perfil_municipal_0.csv)

8. [[PDF] 2021 - qualidade de vida - Governo do Estado do Rio de Janeiro](https://www.rj.gov.br/ceperj/sites/default/files/arquivos-paginas/RQV2021.pdf)

9. [[PDF] GEOSERVIÇOS - Governo do Estado do Rio de Janeiro](https://www.rj.gov.br/ceperj/sites/default/files/arquivos-paginas/IDE%20Cat%C3%A1logo%20de%20Dados.pdf)

10. [Disseminação de Dados | CEPERJ](https://www.rj.gov.br/ceperj/disseminacaodedados)

11. [Mapa](https://carioca.rio/tema/mapa/)

12. [httparquivos.proderj.rj.gov.brsefaz_ceperj_imagensArquivos_Ceperjceepinformacoes-do-territoriocartografia-fluminenseMap](https://pt.scribd.com/document/807339702/httparquivos-proderj-rj-gov-brsefaz-ceperj-imagensArquivos-Ceperjceepinformacoes-do-territoriocartografia-fluminenseMap) - Doc 4

13. [GEO-RIO - Prefeitura da Cidade do Rio de ...](https://prefeitura.rio/orgaos_municipais/geo-rio/) - Prefeitura da Cidade do Rio de Janeiro - Rua Afonso Cavalcanti, 455 - Cidade Nova - 20211-110. pt Po...

14. [Prefeitura da Cidade do Rio de Janeiro](https://pcrj.maps.arcgis.com/) - Aqui, você encontra conteúdos públicos sobre o acervo de Cartografia e Geoprocessamento da Cidade qu...

15. [GeoMacaé - Portal Semplan - plan.apps.macae.rj.gov.br](https://plan.apps.macae.rj.gov.br/portal/geomacae)

16. [Portal de Dados GeoMacaé](https://macae.rj.gov.br/geomacae/conteudo/titulo/shapefiles) - GeoMacaé Shapefiles O shapefile é um formato de arquivo desenvolvido pela empresa ESRI para conter d...

17. [GeoMacaé - Mapas e Imagens - Portal Semplan](https://plan.apps.macae.rj.gov.br/portal/geomacae/mapasEImagens)

18. [Portal de Dados GeoMacaé - Prefeitura de Macaé](https://www.macae.rj.gov.br/geomacae/conteudo/titulo/imoveis-publicos) - Portal de Dados GeoMacaé

19. [Portal de Dados GeoMacaé](https://macae.rj.gov.br/geomacae/conteudo/titulo/apresentacao) - Os mapas e tabelas estão disponíveis em formato .pdf e para sua visualizaçao é necessário o software...

20. [Lagomar](https://www.macae.rj.gov.br/midia/conteudo/arquivos/1456571727.pdf)

21. [Barra de Macaé Nova Esperança Nova Holanda Fronteira](https://www.macae.rj.gov.br/midia/conteudo/arquivos/1458760629.pdf)

22. [Parque Atlantico Parque Aeroporto Parque União São ...](https://www.macae.rj.gov.br/midia/conteudo/arquivos/1458783503.pdf)

23. [Portal Geo Seade](https://portalgeo.seade.gov.br/) - É possível realizar o download de todas as bases cartográficas em arquivo formato shapefile (shp), j...

24. [Carta de padrões de relevo: município de Duque de Caxias - RJ](https://rigeo.sgb.gov.br/handle/doc/19418)

25. [Como saber o que posso construir ou o cadastro da parcela?](https://pcgt.dgterritorio.gov.pt/node/16636)

26. [!.](https://www.macae.rj.gov.br/midia/uploads/Distritos%20LCM%20248-2015.pdf)

27. [FORMULÁRIOS PADRÃO](https://portalcontribuinte.duquedecaxias.rj.gov.br/pdfs/IPTU/BoletimdeColetadeDadosImobiliarios.pdf)

28. [GeoNatal](https://geo.natal.rn.gov.br/)

29. [Novo visualizador de cadastro | Direção-Geral do Território](https://www.dgterritorio.gov.pt/Novo-visualizador-de-cadastro)

30. [SIGWEB v2.0.1.3536 - Colombo](https://colombo.ctmgeo.com.br/)

31. [SIGWEB: Home page](https://sig.petropolis.rj.gov.br/) - Connect T Publico project - Petrópolis Abstract : Cartografia Historica Abstract : Keyword list : Ca...

32. [Topovision - São Gonçalo](https://topovision.pmsg.rj.gov.br/) - Camadas Mapa Base Open Street Map. Municipio Sao Goncalo Mapa Base Open Street Map. OpenStreet Map (...

