# Fontes de dados geoespaciais — Estado do Rio de Janeiro

**Status:** levantamento inicial (Knowledge Verification Chain, passos 3–4: busca web + documentação oficial).
**Data:** 2026-08-18
**Escopo:** RJ (33) — 92 municípios.

> **Aviso de confiabilidade.** O ambiente de desenvolvimento atual bloqueia acesso HTTPS
> direto aos hosts `.gov.br` (política de egress: 403 no CONNECT). Portanto **nenhum endpoint
> abaixo foi testado por requisição real nesta sessão**. Cada linha carrega um nível de
> confiança. Nada aqui deve virar código antes de passar pela checklist de verificação
> (seção final). Onde não há confirmação, está escrito "a verificar" — não foi inventado.

---

## 1. Camada rural — limites de imóveis

| Fonte | O que entrega | Formato | Confiança | Observações |
|---|---|---|---|---|
| **INCRA — Acervo Fundiário** | Parcelas certificadas SIGEF + acervo legado SNCI, assentamentos, quilombolas | Shapefile por UF | Alta (documentado em portais oficiais e dados.gov.br) | Download por camada + UF. Desde out/2023 o portal interativo exige login gov.br (nível prata/ouro); o **download de shapefile** é relatado como aberto — **a verificar**. |
| **INCRA — SIGEF** | Parcelas georreferenciadas certificadas, com código do imóvel e área | Shapefile / consulta | Alta | Base primária para o perímetro rural. |
| **SICAR / CAR** | Perímetro do imóvel rural declarado, APP, Reserva Legal, vegetação nativa, área consolidada, hidrografia, declividade >45°, uso restrito | Shapefile + planilha, por UF/município | Alta | **É declaratório**, não certificado — sobreposições e autodeclaração incorreta são comuns. Tratar como *declaração*, nunca como *limite legal*. |

**Ponto crítico de produto:** SIGEF e CAR discordam com frequência sobre o mesmo imóvel. O
dossiê precisa mostrar as duas versões e a divergência, não escolher uma silenciosamente.

---

## 2. Camada urbana — lotes

| Fonte | Cobertura | Confiança | Observações |
|---|---|---|---|
| **DATA.RIO / IPP** (município do Rio) | Lotes, logradouros, uso do solo, dinâmica imobiliária | Alta (portal existe, hub ArcGIS) | Publica GeoService/GeoJSON via ArcGIS Hub. Granularidade exata da camada de lote — **a verificar**. |
| **GeoPAL** (Rio) | Projetos de Alinhamento (PAL) aprovados | Média | Útil para alinhamento/testada; formato de saída — a verificar. |
| **SIGeo Niterói** | Cadastro imobiliário municipal | Média-alta | Portal existe e é citado como referência de SIG municipal no RJ. |
| **Demais 90 municípios** | — | **Baixa / desconhecida** | **Esta é a maior incerteza do projeto.** A maioria dos municípios do RJ provavelmente não publica lote cadastral em formato aberto. Requer levantamento município a município. |

**Consequência de arquitetura:** a cobertura urbana será *irregular por município*. O app precisa
de um conceito de **cobertura declarada** por camada/município, exibido ao usuário — senão o
silêncio vira erro percebido ("o app está errado" quando na verdade é "não há dado ali").

---

## 3. Camada de restrições e contexto

| Fonte | O que entrega | Confiança |
|---|---|---|
| **GEOINEA (INEA-RJ)** | Unidades de conservação, APP, corpos d'água, mananciais, áreas suscetíveis a deslizamento e inundação, relevo — para os 92 municípios | Alta (portal ArcGIS Online, download shp/kml/GeoTIFF) |
| **IBGE** | Malhas territoriais, hidrografia, setores censitários, relevo | Alta |
| **ICMBio** | Unidades de conservação federais | Alta |
| **MapBiomas** | Uso e cobertura do solo, alertas de desmatamento, série histórica | Alta (licença a verificar para uso comercial) |
| **ANA** | Recursos hídricos | Média-alta |

---

## 4. Camada registral / proprietário — o ponto jurídico

Resumo do que a lei sustenta hoje:

- **Lei 6.015/73, art. 17** — princípio da publicidade registral: qualquer pessoa pode obter
  certidão do registro **sem declarar o motivo ou interesse**. O dado registral é público *por
  requisição de certidão*.
- **Lei 13.465/2017** — institui o **ONR**, operador do SREI; centraliza o acesso às unidades
  registrais em um ponto único na internet. Serviços: certidão on-line, visualização eletrônica
  de matrícula, **pesquisa de bens por CPF/CNPJ**.
- **LGPD (Lei 13.709/2018)** — dado público por origem **não vira dado livre para agregação
  e redistribuição**. A publicidade registral autoriza a *consulta pontual mediante certidão*;
  ela não autoriza construir e servir uma base agregada de "proprietário → imóveis" como camada
  de mapa.

**Leitura técnica (não é parecer jurídico):**

1. Perímetros, áreas, restrições ambientais e códigos de imóvel — **base própria, sem problema**.
2. Nome do proprietário, CPF/CNPJ, valor de transação, ônus e gravames — **não devem ser
   ingeridos e armazenados na base própria**. O caminho defensável é **passagem viva**: o app
   dispara uma consulta ao ONR/cartório **no ato**, sob identidade do usuário habilitado, exibe
   o resultado e **registra o acesso em log de auditoria** — sem cache persistente do conteúdo
   pessoal.
3. "Permissão jurídica" no app não é um booleano do produto: é **credencial verificável**
   (OAB ativa, procuração, ou vínculo contratual) + **finalidade declarada** + **trilha de
   auditoria**. Sem isso, o recurso é passivo de LGPD, não diferencial.

> **Marcado como incerto (passo 5 da cadeia):** não localizei nesta sessão documentação pública
> de uma **API do ONR para integração de terceiros** (vs. o portal web para o cidadão). Isso
> precisa ser confirmado direto com o ONR antes de qualquer promessa de produto. Se não houver
> API, a camada registral vira *deep link + upload de certidão*, não integração automática.

---

## 5. Checklist de verificação (fazer antes de qualquer código de ingestão)

- [ ] Baixar 1 shapefile do Acervo Fundiário/SIGEF filtrado por RJ e medir: nº de feições, CRS, validade dos polígonos
- [ ] Baixar CAR do RJ (1 município piloto) e medir sobreposição SIGEF × CAR
- [ ] Confirmar se DATA.RIO expõe camada de **lote** (não só quadra/bairro) e em qual endpoint
- [ ] Confirmar formato e licença de saída do SIGeo Niterói
- [ ] Inventariar os 92 municípios: quem publica lote cadastral aberto (planilha de cobertura)
- [ ] Confirmar licença do MapBiomas para uso comercial
- [ ] Contatar ONR sobre existência/condições de API para terceiros
- [ ] Definir CRS canônico do projeto (candidato: SIRGAS 2000 / EPSG:4674 para armazenamento, 3857 para tiles) — decidir em Design

## Fontes

- [INCRA — obter coordenadas e arquivos dos imóveis rurais certificados](https://www.gov.br/pt-br/servicos/obter-coordenadas-e-baixar-os-arquivos-dos-imoveis-ruras-certificados)
- [SIGEF — Sistema de Gestão Fundiária](https://sigef.incra.gov.br/)
- [dados.gov.br — conjunto SIGEF](https://dados.gov.br/dados/conjuntos-dados/sistema-de-gestao-fundiaria---sigef)
- [SICAR — consulta pública](https://consultapublica.car.gov.br/)
- [DATA.RIO](https://www.data.rio/)
- [HUB SIGeo Niterói](https://www.sigeo.niteroi.rj.gov.br/)
- [INEA — informações geoespaciais](http://www.inea.rj.gov.br/biodiversidade-territorio/informacoes-geoespaciais/)
- [ONR — Operador Nacional do Registro de Imóveis](https://www.onr.org.br/)
- [CNJ — SREI](https://www.cnj.jus.br/sistemas/srei/)
- [Lei 6.015/73](https://www.lexml.gov.br/urn/urn:lex:br:federal:lei:1973-12-31;6015)
