-- Fatia 2: schema PostGIS mínimo — SIGEF (imóvel rural) + limite estadual do RJ.
-- CRS canônico: SIRGAS 2000 (EPSG:4674).

CREATE EXTENSION IF NOT EXISTS postgis;

-- Dimensão de versão: publicação atômica troca o ponteiro (DOS-28).
CREATE TABLE IF NOT EXISTS versao_base (
    id text PRIMARY KEY,
    criada_em date NOT NULL,
    status text NOT NULL CHECK (status IN ('draft', 'published', 'retired')),
    feicoes_por_camada jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Swap atômico por transação: qual versão está publicada para cada camada.
CREATE TABLE IF NOT EXISTS ponteiro_publicado (
    camada text PRIMARY KEY,
    versao_base_id text NOT NULL REFERENCES versao_base (id)
);

-- Fronteira estadual (AD-001).
CREATE TABLE IF NOT EXISTS limite_estado (
    uf text NOT NULL,
    geom geometry(MultiPolygon, 4674) NOT NULL,
    versao_base_id text NOT NULL REFERENCES versao_base (id),
    PRIMARY KEY (uf, versao_base_id)
);

-- Imóvel rural: DUAS geometrias, nunca uma final (AD-003) — geom_car nula nesta fatia.
CREATE TABLE IF NOT EXISTS lote_rural (
    id text NOT NULL,
    uf text NOT NULL,
    municipios text[] NOT NULL,
    codigo_sigef text NOT NULL,
    denominacao text,
    situacao_certificacao text NOT NULL,
    geom_sigef geometry(MultiPolygon, 4674) NOT NULL,
    geom_car geometry(MultiPolygon, 4674),
    geometria_corrigida boolean NOT NULL DEFAULT false,
    versao_base_id text NOT NULL REFERENCES versao_base (id),
    PRIMARY KEY (id, versao_base_id)
);

-- Proveniência da camada nesta versão (DOS-10/05).
CREATE TABLE IF NOT EXISTS proveniencia (
    camada text NOT NULL,
    versao_base_id text NOT NULL REFERENCES versao_base (id),
    fonte text NOT NULL,
    data_extracao date NOT NULL,
    link_oficial text NOT NULL,
    PRIMARY KEY (camada, versao_base_id)
);

-- Cobertura declarada por camada e município (DOS-13) — não versionada.
CREATE TABLE IF NOT EXISTS cobertura (
    municipio text NOT NULL,
    camada text NOT NULL,
    tem_dado boolean NOT NULL,
    data_extracao date,
    PRIMARY KEY (municipio, camada)
);
