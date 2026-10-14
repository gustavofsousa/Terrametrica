# Mapa do Lote no RJ Design

**Spec**: `.specs/features/mapa-do-lote-rj/spec.md` (r1)
**Status**: Approved (2026-10-14) — E2E com pytest-playwright (AD-017)

---

## Architecture Overview

Três fatias verticais, nesta ordem. Cada uma fecha com testes verdes e pode ir para produção
sozinha.

1. **Base (MUN-01..09):** a carga ingere a malha municipal na mesma versão do resto. O
   `municipio_em` passa a funcionar e a cobertura passa a ter os 92 municípios.
2. **API (MAPA-04, 06, 07, MUN-03, 08):** o `/dossie` devolve a geometria do lote e o nome do
   município. Uma rota pública nova devolve o contorno do RJ.
3. **Front (MAPA-01..05, 08..19):** MapLibre no lugar do Leaflet. A lógica pura fica em módulos
   ESM testáveis por `node --test`. O `mapa.js` só liga DOM e MapLibre.

```mermaid
graph TD
    subgraph Carga["Carga local (carregar_base)"]
        L[ingerir_limite_rj<br/>geobr 2025, resolução completa] --> P
        M[ingerir_municipios_rj NOVO<br/>geobr 2025, 92 municípios] --> P
        S[SIGEF / CAR / UC / Niterói] --> P
        P[materializar_intersecoes → semear_cobertura<br/>agora com os 92 municípios] --> G[publicar_versao<br/>guarda inclui 'municipio']
    end
    G --> DB[(PostGIS<br/>municipio NOVO + tabelas atuais)]
    DB --> R[RepositorioLotesPostGIS<br/>municipio_em real · geometrias_de NOVO · contorno_estado NOVO]
    R --> A[FastAPI: /dossie + geometria · /mapa/contorno NOVO · /cobertura/estado + nome]
    A --> F[app/: mapa.js (MapLibre 6.14.0 + OpenFreeMap)<br/>dossie.js · painel.js · consultas.js · url.js · geometria.js]
```

**Approach (Large):** a spec já fixou as escolhas de produto: geometria dentro do `/dossie`, front
vanilla (AD-012), basemap OpenFreeMap. A medição desta fase fixou a fonte da malha (geobr completo).
A única alternativa real que sobrou é o harness de E2E. Ela está em "Testing Seams" com
recomendação.

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --- | --- | --- |
| Padrão de ingestão geobr | `src/terrametrica/ingestao/limite_rj.py` | `ingerir_municipios_rj` copia a forma: geobr → `to_crs(4674)` → `corrigir_geometria` → `para_multipolygon` → INSERT sem commit |
| Correção de geometria | `src/terrametrica/ingestao/validacao_geometria.py` | Reuso direto |
| Guarda + swap atômico | `src/terrametrica/ingestao/publicar.py` | Entra a camada `municipio` em `_CAMADAS_PUBLICADAS` e `_QUERY_CONTAGEM_POR_CAMADA` |
| Semeadura de cobertura | `src/terrametrica/ingestao/cobertura.py` | Troca a origem do conjunto de municípios (ver AD-016) |
| Orquestrador da carga | `src/terrametrica/ingestao/carregar_base.py` | Uma chamada nova logo após `ingerir_limite_rj` |
| Repositório PostGIS | `src/terrametrica/persistencia/repositorio_lotes_postgis.py` | `municipio_em` real; dois métodos de leitura novos |
| Projeção DTO | `src/terrametrica/api/dto.py` | `sem_lote_para_dict` e `_lote_para_dict` ganham campos |
| View model puro | `app/dossie.js` + `app/tests/dossie.test.mjs` | Ganha os estados `fora_do_rj` e `erro_rede` e os campos de área e geometria |
| Escape de HTML | `app/mapa.js` `esc()` | Move para `painel.js`; continua obrigatório em todo texto da API |
| Template MapLibre testado | skill `map-ux` `assets/map-app-template.html` | Fonte do padrão de seleção por `feature-state`, URL, bottom sheet, `padding` |

### Integration Points

| System | Integration Method |
| --- | --- |
| PostGIS | Migração `0008_f113_municipio.sql` (aditiva) + `rollback/0008_f113_municipio.down.sql` (manual, fora do glob do runner) |
| OpenFreeMap | `https://tiles.openfreemap.org/styles/positron` carregado pelo MapLibre no navegador |
| unpkg | `maplibre-gl@6.14.0` (`.mjs` + `.css`), mesma CDN já usada pelo Leaflet |

---

## Components

### `ingerir_municipios_rj` (novo)

- **Purpose**: Gravar os 92 municípios do RJ na versão em construção.
- **Location**: `src/terrametrica/ingestao/municipios_rj.py`
- **Interfaces**:
  - `ingerir_municipios_rj(versao: VersaoBase, conexao, *, ler=_ler_geobr) -> RelatorioCamada`. Se não vierem exatamente 92 códigos `33xxxxx` com geometria, levanta `MalhaIncompleta` (MUN-04).
  - `sha256_canonico(gdf) -> str`: o SHA-256 do GeoJSON das feições ordenadas por código (MUN-05).
- **Dependencies**: geobr (já no `pyproject`), psycopg.
- **Reuses**: `limite_rj.py`, `validacao_geometria.py`.
- **Idempotência (MUN-06)**: `DELETE FROM municipio WHERE versao_base_id = %s` antes do INSERT, na mesma transação.

### `ingerir_limite_rj` (ajuste)

- **Mudança**: `simplified=False`. Com isso a borda do estado e a união da malha coincidem.
- **Por quê**: medido em 2026-10-14. O contorno simplificado deixa 1 lote SIGEF real fora do RJ (ele vira 422) e ~25 km² de frestas entre o estado e os municípios. A carga é refeita de qualquer modo para a malha, então o custo é zero.

### `RepositorioLotesPostGIS` (extensão)

- **Interfaces**:
  - `municipio_em(coord, versao) -> Municipio | None`: `ST_Contains` na `municipio` da versão. Deixa de levantar `NotImplementedError` (fecha TD-001).
  - `geometrias_de(lote_ids: Sequence[str], versao) -> dict[str, dict]`: `UNION ALL` de `lote_rural.geom_sigef` e `lote_urbano.geom` com `ST_AsGeoJSON(geom, 6)`.
  - `contorno_estado(versao) -> dict`: `ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.0005), 5)` de `limite_estado`. É só para desenho; o teste de "dentro do RJ" continua na geometria completa.
  - `cobertura_de_todos()` passa a devolver o nome de cada município, ordenado por nome (MUN-08).
- **Reuses**: o estilo de SQL e de mapeamento de linhas atual.

### Domínio (ajuste mínimo)

- `Municipio(codigo: str, nome: str)`: value object novo em `dominio/modelos.py`.
- `SemLote.municipio: Municipio | None`. O valor `None` cobre o ponto dentro do RJ que não cai em nenhum município.
- A porta `RepositorioLotes.municipio_em` muda de assinatura. O fake em `tests/fakes/repositorio_fake.py` acompanha.
- `montar_dossie` não muda de lógica. Ele já chama `municipio_em` e `cobertura_de`. Se vier `None`, a cobertura é uma tupla vazia.

### API (extensão, continua fina — AD-007)

- `/dossie` 200: `lote.geometria` (GeoJSON). 409: `candidatos[].geometria`. A geometria vem de `geometrias_de` depois de montar o dossiê, e a rota só orquestra.
- `/dossie` 404: `municipio` (código ou `null`), `municipio_nome`, `cobertura`.
- `GET /mapa/contorno` (novo, público como `/cobertura/estado`): Feature GeoJSON do RJ com `Cache-Control: public, max-age=86400` e `ETag` igual ao id da versão publicada.
- `consulta_log`: sem campo novo (MAPA-10).

### Front (`app/`)

| Módulo | Responsabilidade | Puro? | Teste |
| --- | --- | --- | --- |
| `dossie.js` | Resposta HTTP → view model. Estados `dossie`, `sem_lote`, `sobreposicao`, `cota`, `fora_do_rj` (novo), `erro_rede` (novo). Área formatada (ha/m²), perímetro, geometria | sim | `node --test` |
| `consultas.js` (novo) | "O último clique vence": cada consulta recebe um número de sequência, e só a resposta do maior número chega ao painel (MAPA-11) | sim (recebe `fetch` injetado) | `node --test` com respostas fora de ordem |
| `url.js` (novo) | `lerSelecao(search) → {lat, lon} \| null` com validação de número e bbox do RJ; `escreverSelecao(lat, lon)` com 6 casas | sim | `node --test` |
| `geometria.js` (novo) | `bboxDe(geojson)` para Polygon e MultiPolygon; `mascaraFora(contorno)`: retângulo do mundo com o RJ como furo | sim | `node --test` |
| `painel.js` (novo) | View model → HTML com `esc()`; foco no título e `aria-busy` | quase (só string) | `node --test` no HTML gerado |
| `mapa.js` | Liga MapLibre, fontes e camadas, eventos, `history.replaceState`, Esc, `padding` da câmera a partir do retângulo do painel | não | E2E |
| `estilos.css` | Layout de duas colunas; `@media (max-width: 640px)` vira bottom sheet ≤ 50vh | — | E2E |

**Camadas do mapa (de baixo para cima):** basemap `positron` → `fora-rj` (máscara, `fill-opacity`
0,35) → `rj-contorno` (linha) → `lote-candidatos` (tracejado, 409) → `lote-selecionado` (fill + linha).
Os rótulos do basemap ficam por cima: `beforeId` = primeira camada `symbol`.

---

## Data Models

```sql
-- 0008_f113_municipio.sql (aditiva)
CREATE TABLE IF NOT EXISTS municipio (
    codigo text NOT NULL CHECK (codigo ~ '^[0-9]{7}$'),
    nome text NOT NULL,
    uf text NOT NULL,                        -- '33'; a UF é dimensão (expansão F4.5)
    geom geometry(MultiPolygon, 4674) NOT NULL,
    versao_base_id text NOT NULL REFERENCES versao_base (id),
    PRIMARY KEY (codigo, versao_base_id)
);
CREATE INDEX IF NOT EXISTS idx_municipio_geom ON municipio USING GIST (geom);
ALTER TABLE proveniencia ADD COLUMN IF NOT EXISTS sha256 text;   -- NULL para as camadas atuais

-- rollback/0008_f113_municipio.down.sql (manual; o runner só lê migracoes/*.sql)
DELETE FROM proveniencia WHERE camada = 'municipio';
DELETE FROM ponteiro_publicado WHERE camada = 'municipio';
ALTER TABLE proveniencia DROP COLUMN IF EXISTS sha256;
DROP TABLE IF EXISTS municipio;
DELETE FROM schema_migrations WHERE nome_arquivo = '0008_f113_municipio.sql';
```

**Contrato de resposta (trecho):**

```jsonc
// 200
{ "lote": { "natureza": "rural", "area_ha": 12.4, "perimetro_m": 1530.2,
            "geometria": { "type": "MultiPolygon", "coordinates": [...] } , ... } }
// 404
{ "mensagem": "...", "municipio": "3304557", "municipio_nome": "Rio de Janeiro", "cobertura": [...] }
```

---

## Testing Seams

| Seam | Existing or New | What a test asserts through it | Reuses |
| --- | --- | --- | --- |
| `ingerir_municipios_rj(..., ler=)` | Existing pattern (função de ingestão) + parâmetro `ler` | 92 gravados; 91 → `MalhaIncompleta` e nada publicado; duas cargas → 92 linhas; SHA estável | fixture GeoJSON pequena em `tests/fixtures/municipio/` (3 municípios + caso 92 sintético) |
| `RepositorioLotesPostGIS` contra PostGIS | Existing (`tests/integration`) | `municipio_em` acha o código; ponto no mar → `None`; `geometrias_de` devolve `[lon, lat]` com 6 casas | harness de integração atual |
| `create_app` + `TestClient` | Existing (`tests/integration/api`) | Corpos 200/404/409/422 e `/mapa/contorno` com `ETag` | `test_api_e2e.py` |
| Migração + rollback | Existing runner + **novo** script down | Migrar → rollback → `/dossie` 200 de um lote conhecido (MUN-09) | harness de integração |
| Módulos puros do front | Existing (`node --test` em `app/tests/`) | View model, último-clique-vence, URL, bbox, máscara, HTML escapado | `dossie.test.mjs` |
| **Navegador real** | **New — precisa do seu ok** | MAPA-01 (nenhuma requisição a `tile.openstreetmap.org`), 02, 03, 08, 12..19 | ver abaixo |

**Harness de E2E: recomendação.** Uso `pytest-playwright` como dependência só de dev no
`pyproject`. O servidor é o uvicorn com a app real. Na fixture, a rota do estilo OpenFreeMap é
interceptada e servida com um estilo mínimo local, para o teste não depender de rede.

- **Prós:** fica no runner que o projeto já usa (`pytest`), sem Node e sem `node_modules`, e a AD-012 continua intacta no deploy. É a única forma de provar MAPA-01 de modo automático.
- **Contras:** baixa o Chromium (~150 MB) na máquina de dev. É mais um tipo de teste para manter.
- **Alternativa:** checagem manual pelo Playwright MCP, registrada no `validation.md` (lição candidata L-002). É mais barata agora, mas regressão de UI passa calada.

---

## Error Handling Strategy

| Error Scenario | Vital or peripheral? | Handling | User Impact |
| --- | --- | --- | --- |
| geobr fora na carga | vital para a carga, nunca para o request | `RuntimeError` com mensagem de rede, como `limite_rj`; a versão não publica | Nenhum: a versão anterior continua publicada |
| Malha com ≠ 92 municípios | vital | `MalhaIncompleta` com a contagem; não publica (MUN-04) | Nenhum |
| OpenFreeMap fora | peripheral | `map.on("error")` no estilo → aviso "Mapa base indisponível" no painel; contorno e clique continuam (MAPA-03) | Mapa sem fundo, consulta funciona |
| `/mapa/contorno` falha | peripheral | Mapa abre sem contorno e sem máscara; o clique continua | Perde a moldura do RJ |
| Rede falha no `/dossie` | vital | Estado `erro_rede` com "Tentar de novo" para o mesmo ponto (MAPA-18) | Mensagem + botão |
| Resposta antiga chega depois da nova | vital | Descartada por `consultas.js` (MAPA-11) | Nenhum |
| Clique fora do RJ (422) | esperado | Estado `fora_do_rj` (MAPA-05) | Mensagem clara |

**Timeout:** `fetch` do `/dossie` com `AbortController` de 15 s, que vira `erro_rede`. A lição de
contenção pede timeout em toda chamada de saída.

---

## Risks & Concerns

| Concern | Location | Impact | Mitigation |
| --- | --- | --- | --- |
| `limite_estado` simplificado | `src/terrametrica/ingestao/limite_rj.py:38` (`read_state` sem `simplified`) | 1 lote SIGEF real recusado como fora do RJ; frestas de ~25 km² entre o estado e os municípios | `simplified=False` nesta feature (ver Components) |
| `cobertura` não é versionada e só faz upsert | `ingestao/cobertura.py`, AD-009 | Município que perde dado mantém a linha antiga | Já registrado em TD-002 (concern aceito). Com 92 municípios fixos, o efeito não piora |
| Sem harness de navegador | `app/` | Regressão visual e de interação passa calada | Harness de E2E (decisão acima) |
| OpenFreeMap sem SLA | externo | Mapa sem fundo se o serviço cair | MAPA-03 degrada; gatilho de revisita: tráfego alto → Protomaps auto-hospedado (RFD nesse momento) |
| MapLibre e estilo em CDNs de terceiros | `app/index.html` | CDN fora → mapa não carrega | Mesmo risco aceito hoje com o Leaflet no unpkg; versão fixada |
| Lição candidata L-001 (toque de borda em join espacial) | `ingestao/intersecoes.py` | Sinal anterior não confirmado; esta feature não cria join de área | Nenhuma ação; `municipio_em` é ponto-em-polígono |

---

## Tech Decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Fonte da malha | geobr 2025, resolução completa | Mesma fonte e ano do `limite_estado`; união = estado (medido) |
| Onde a geometria entra na API | Leitura separada `geometrias_de` chamada pela rota, não no value object do lote | O domínio do dossiê não carrega dado de desenho; `montar_dossie` fica intocado |
| Contorno do RJ | Rota `/mapa/contorno` com cache HTTP, simplificado só para desenho | Uma fonte da verdade (`limite_estado` publicado); nada fixo no código |
| Rollback | Script SQL manual em `migracoes/rollback/` | O runner não tem *down*; criar um runner de rollback seria gold-plating |
| Conjunto de municípios da cobertura | Tabela `municipio` da versão | Supersede parte da AD-009 (ver AD-016 abaixo) |

**Project-level (registradas em `.specs/STATE.md`):** AD-015, AD-016 e AD-017.

- **AD-015** — O mapa do painel usa MapLibre GL JS 6.14.0 (ESM, sem build) e o basemap OpenFreeMap `positron`. Nunca usa `tile.openstreetmap.org`. Isso supersede a linha "Leaflet + tiles OSM" da AD-012; o resto da AD-012 continua.
- **AD-016** — A malha municipal (geobr 2025, resolução completa) é camada versionada da base. Ela define o conjunto de municípios da cobertura e substitui a origem `lote_rural.municipios` da AD-009. Toda tabela geográfica nova carrega `uf` para a expansão F4.5.
