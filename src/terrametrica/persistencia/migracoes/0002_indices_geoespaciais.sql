-- Fatia 2: índices GiST para as consultas geoespaciais dos adapters PostGIS
-- (ST_Contains em `lote_em`/`LimiteEstadoPostGIS.contem`) — sem eles, cada consulta
-- faz sequential scan nas tabelas de geometria.

CREATE INDEX IF NOT EXISTS idx_lote_rural_geom_sigef ON lote_rural USING GIST (geom_sigef);

CREATE INDEX IF NOT EXISTS idx_limite_estado_geom ON limite_estado USING GIST (geom);
