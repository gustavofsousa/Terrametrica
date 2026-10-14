-- F1.8: malha municipal do RJ (AD-016). Mesmo versionamento por base do lote rural (AD-008).
CREATE TABLE IF NOT EXISTS municipio (
    codigo text NOT NULL CHECK (codigo ~ '^[0-9]{7}$'),
    nome text NOT NULL,
    uf text NOT NULL,
    geom geometry(MultiPolygon, 4674) NOT NULL,
    versao_base_id text NOT NULL REFERENCES versao_base (id),
    PRIMARY KEY (codigo, versao_base_id)
);

CREATE INDEX IF NOT EXISTS idx_municipio_geom ON municipio USING GIST (geom);

-- SHA-256 do conteúdo ingerido (MUN-05). NULL para as camadas anteriores à malha.
ALTER TABLE proveniencia ADD COLUMN IF NOT EXISTS sha256 text;
