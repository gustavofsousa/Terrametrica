-- Fatia 6: log de observabilidade de consultas (DOS-30).
-- Uma linha por consulta a /dossie — inclusive quando o resultado não é um Dossie (fora do RJ,
-- sobreposição): a consulta aconteceu. `conta_id` é o identificador opaco vindo do header
-- `X-Conta-Id` (AD-011). Nenhum dado pessoal de proprietário (AD-002) — só identidade de conta,
-- lote consultado, camadas retornadas e latência. Não versionada (é registro de evento, não base).

CREATE TABLE IF NOT EXISTS consulta_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    conta_id text NOT NULL,
    lote_id text,
    camadas text[] NOT NULL DEFAULT '{}',
    latencia_ms integer NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_consulta_log_conta_ts ON consulta_log (conta_id, ts);
