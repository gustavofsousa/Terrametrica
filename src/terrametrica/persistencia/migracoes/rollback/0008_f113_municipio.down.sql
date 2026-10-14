-- Rollback manual da 0008 (MUN-09). O runner só lê migracoes/*.sql e ignora esta pasta.
-- Desfaz só o que a 0008 criou. Nenhuma tabela de lote, restrição ou ponteiro de lote é tocada.
DELETE FROM proveniencia WHERE camada = 'municipio';
DELETE FROM ponteiro_publicado WHERE camada = 'municipio';
ALTER TABLE proveniencia DROP COLUMN IF EXISTS sha256;
DROP TABLE IF EXISTS municipio;
DELETE FROM schema_migrations WHERE nome_arquivo = '0008_f113_municipio.sql'
