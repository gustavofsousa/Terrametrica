-- Fatia 7 (F1.11): auth por magic link + sessão. Isola 100% da PII de login (e-mail) fora da
-- struct `Conta` do domínio (GATE-06 intacto por construção). Nenhuma tabela `conta` física é
-- materializada nesta fatia (TD-006): `conta_id` é referência lógica ao conceito de domínio.
-- Tokens (magic link e sessão) são guardados como HASH, nunca o valor em claro — dump do banco
-- não concede sessão nem reuso de link.

-- e-mail ↔ conta: a ÚNICA tabela com PII de login. Fora da fronteira do gate jurídico.
CREATE TABLE IF NOT EXISTS credencial_login (
    email      text PRIMARY KEY,
    conta_id   text NOT NULL,
    criado_em  timestamptz NOT NULL DEFAULT now()
);

-- magic links emitidos. Uso único (usado_em NULL = ainda não usado), expira em 15 min.
CREATE TABLE IF NOT EXISTS login_token (
    hash_token text PRIMARY KEY,
    email      text NOT NULL,
    criado_em  timestamptz NOT NULL DEFAULT now(),
    expira_em  timestamptz NOT NULL,
    usado_em   timestamptz
);

-- índice do rate limit 5/h por e-mail (conta tokens numa janela).
CREATE INDEX IF NOT EXISTS idx_login_token_email_criado ON login_token (email, criado_em);

-- sessões ativas. Guarda HASH do token de sessão, expira em 30 dias.
CREATE TABLE IF NOT EXISTS sessao (
    hash_sessao text PRIMARY KEY,
    conta_id    text NOT NULL,
    criado_em   timestamptz NOT NULL DEFAULT now(),
    expira_em   timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessao_conta ON sessao (conta_id);
