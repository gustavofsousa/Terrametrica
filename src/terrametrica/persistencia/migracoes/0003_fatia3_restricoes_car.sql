-- Fatia 3: CAR como camada de restrição (APP + Reserva Legal).
-- `restricao` já estava sketchada em design.md desde a Fatia 1 (genérica, tipo discriminador) —
-- concretizada aqui pela primeira vez, com só 'app'/'reserva_legal' populados nesta fatia.

CREATE TABLE IF NOT EXISTS restricao (
    id text NOT NULL,
    tipo text NOT NULL CHECK (tipo IN ('app', 'reserva_legal')),
    nome text NOT NULL,
    categoria text,
    grau_suscetibilidade text,
    geom geometry(MultiPolygon, 4674) NOT NULL,
    versao_base_id text NOT NULL REFERENCES versao_base (id),
    PRIMARY KEY (id, versao_base_id)
);

CREATE INDEX IF NOT EXISTS idx_restricao_geom ON restricao USING GIST (geom);

-- Read-model: intersecção lote×restrição materializada na ingestão (AD-007), não em request.
-- pct_do_lote/marginal não são colunas aqui — cálculo puro em `geometria.classificar_intersecao`,
-- rodado na leitura por `montagem.py` (contrato já existente de T4/T5).
CREATE TABLE IF NOT EXISTS intersecao_materializada (
    lote_id text NOT NULL,
    restricao_id text NOT NULL,
    area_intersecao_m2 double precision NOT NULL,
    versao_base_id text NOT NULL,
    PRIMARY KEY (lote_id, restricao_id, versao_base_id),
    FOREIGN KEY (lote_id, versao_base_id) REFERENCES lote_rural (id, versao_base_id),
    FOREIGN KEY (restricao_id, versao_base_id) REFERENCES restricao (id, versao_base_id)
);
