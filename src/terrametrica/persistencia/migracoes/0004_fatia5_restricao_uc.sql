-- Fatia 5: Unidade de Conservação (UC) como camada de restrição.
-- A tabela `restricao` já é genérica (tipo discriminador) desde a 0003. Aqui só estendemos o
-- CHECK para admitir 'unidade_conservacao'. As demais camadas do INEA/ICMBio (inundação,
-- deslizamento, corpo d'água) entram cada uma na sua fatia, com sua própria extensão do CHECK
-- quando a fonte real for verificada (evitamos liberar tipos que ainda não sabemos ingerir).

ALTER TABLE restricao DROP CONSTRAINT IF EXISTS restricao_tipo_check;

ALTER TABLE restricao ADD CONSTRAINT restricao_tipo_check
    CHECK (tipo IN ('app', 'reserva_legal', 'unidade_conservacao'));
