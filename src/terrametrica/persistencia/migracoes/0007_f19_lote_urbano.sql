-- F1.9: lote urbano (SIGeo Niterói, AD-006). Mesmo versionamento por base do lote rural (AD-008).
CREATE TABLE IF NOT EXISTS lote_urbano (
    id text NOT NULL,
    municipio text NOT NULL,
    inscricao_cadastral text,
    logradouro text,
    bairro text,
    geom geometry(MultiPolygon, 4674) NOT NULL,
    geometria_corrigida boolean NOT NULL DEFAULT false,
    versao_base_id text NOT NULL REFERENCES versao_base (id),
    PRIMARY KEY (id, versao_base_id)
);

CREATE INDEX IF NOT EXISTS idx_lote_urbano_geom ON lote_urbano USING GIST (geom);

-- A intersecção passa a valer para lote rural OU urbano: a FK só para `lote_rural` deixa de caber.
-- INVARIANT: ids não colidem entre as tabelas — o urbano carrega prefixo de município (`niteroi:`).
ALTER TABLE intersecao_materializada
    DROP CONSTRAINT IF EXISTS intersecao_materializada_lote_id_versao_base_id_fkey;
