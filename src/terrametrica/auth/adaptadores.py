"""Adaptadores reais das ports de auth (Fatia 7, T5) — Postgres + Resend.

Implementações de I/O na borda: os 3 repositórios recebem a `conexao` de fora (como os repos
existentes em `persistencia/`), e o `EnviadorResend` fala HTTP com a API do Resend. As regras e a
orquestração (T2/T4) não sabem que este arquivo existe — só os contratos de `auth/portas.py`.

`consumir` é atômico via `UPDATE ... WHERE usado_em IS NULL AND expira_em > agora RETURNING`: dois
cliques simultâneos disputam a mesma linha; só o primeiro casa o WHERE e recebe o registro.
"""

from datetime import datetime
from uuid import uuid4

import httpx
import psycopg

from terrametrica.auth.regras import Email, RegistroToken
from terrametrica.dominio.modelos import PapelConta

_INSERT_TOKEN = """
    INSERT INTO login_token (hash_token, email, expira_em)
    VALUES (%(hash_token)s, %(email)s, %(expira_em)s)
"""

# Atômico: casa o WHERE só se o token está não-usado e não-expirado; marca usado na mesma query.
_CONSUMIR_TOKEN = """
    UPDATE login_token
       SET usado_em = %(agora)s
     WHERE hash_token = %(hash_token)s
       AND usado_em IS NULL
       AND expira_em > %(agora)s
    RETURNING hash_token, email, expira_em, usado_em
"""

_CONTAR_JANELA = """
    SELECT count(*) FROM login_token
     WHERE email = %(email)s AND criado_em >= %(desde)s
"""

_CONTA_DE_EMAIL = "SELECT conta_id FROM credencial_login WHERE email = %(email)s"

_CRIAR_CREDENCIAL = """
    INSERT INTO credencial_login (email, conta_id) VALUES (%(email)s, %(conta_id)s)
"""

_INSERT_SESSAO = """
    INSERT INTO sessao (hash_sessao, conta_id, expira_em)
    VALUES (%(hash_sessao)s, %(conta_id)s, %(expira_em)s)
"""

_CONTA_DE_SESSAO = """
    SELECT conta_id FROM sessao
     WHERE hash_sessao = %(hash_sessao)s AND expira_em > %(agora)s
"""

_DELETAR_SESSAO = "DELETE FROM sessao WHERE hash_sessao = %(hash_sessao)s"


class RepositorioCredencialPostgres:
    """e-mail ↔ conta em `credencial_login`. Cria `conta_id` (a fatia não materializa `conta`)."""

    def __init__(self, conexao: psycopg.Connection) -> None:
        self._conexao = conexao

    def conta_de_email(self, email: Email) -> str | None:
        with self._conexao.cursor() as cursor:
            cursor.execute(_CONTA_DE_EMAIL, {"email": email.valor})
            linha = cursor.fetchone()
        return linha[0] if linha else None

    def criar_conta_para_email(self, email: Email, papel: PapelConta) -> str:
        conta_id = str(uuid4())  # TD-006: id lógico, sem tabela `conta` física ainda.
        with self._conexao.cursor() as cursor:
            cursor.execute(_CRIAR_CREDENCIAL, {"email": email.valor, "conta_id": conta_id})
        self._conexao.commit()
        return conta_id


class RepositorioTokenPostgres:
    """Magic links em `login_token`. `consumir` é uso único à prova de corrida."""

    def __init__(self, conexao: psycopg.Connection) -> None:
        self._conexao = conexao

    def salvar(self, hash_token: str, email: Email, expira_em: datetime) -> None:
        with self._conexao.cursor() as cursor:
            cursor.execute(
                _INSERT_TOKEN,
                {"hash_token": hash_token, "email": email.valor, "expira_em": expira_em},
            )
        self._conexao.commit()

    def consumir(self, hash_token: str, agora: datetime) -> RegistroToken | None:
        with self._conexao.cursor() as cursor:
            cursor.execute(_CONSUMIR_TOKEN, {"hash_token": hash_token, "agora": agora})
            linha = cursor.fetchone()
        self._conexao.commit()
        if linha is None:
            return None
        hash_t, email, expira_em, usado_em = linha
        return RegistroToken(
            hash_token=hash_t, email=Email(email), expira_em=expira_em, usado_em=usado_em
        )

    def contar_na_janela(self, email: Email, desde: datetime) -> int:
        with self._conexao.cursor() as cursor:
            cursor.execute(_CONTAR_JANELA, {"email": email.valor, "desde": desde})
            linha = cursor.fetchone()
        assert linha is not None  # count(*) sempre retorna uma linha
        return int(linha[0])


class RepositorioSessaoPostgres:
    """Sessões em `sessao`. Guarda hash, expira por tempo, invalidar é DELETE idempotente."""

    def __init__(self, conexao: psycopg.Connection) -> None:
        self._conexao = conexao

    def criar(self, conta_id: str, hash_sessao: str, expira_em: datetime) -> None:
        with self._conexao.cursor() as cursor:
            cursor.execute(
                _INSERT_SESSAO,
                {"hash_sessao": hash_sessao, "conta_id": conta_id, "expira_em": expira_em},
            )
        self._conexao.commit()

    def conta_de_sessao(self, hash_sessao: str, agora: datetime) -> str | None:
        with self._conexao.cursor() as cursor:
            cursor.execute(_CONTA_DE_SESSAO, {"hash_sessao": hash_sessao, "agora": agora})
            linha = cursor.fetchone()
        return linha[0] if linha else None

    def invalidar(self, hash_sessao: str) -> None:
        with self._conexao.cursor() as cursor:
            cursor.execute(_DELETAR_SESSAO, {"hash_sessao": hash_sessao})
        self._conexao.commit()


class EnviadorResend:
    """Envia o magic link via API do Resend. Levanta em falha (→ 502): nunca finge que enviou.

    `transporte` é injetável (um `httpx.Client` fake nos testes) para não bater na rede real.
    """

    def __init__(
        self,
        api_key: str,
        remetente: str,
        *,
        transporte: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._remetente = remetente
        self._transporte = transporte or httpx.Client(base_url="https://api.resend.com")

    def enviar_magic_link(self, email: Email, link: str) -> None:
        resposta = self._transporte.post(
            "/emails",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "from": self._remetente,
                "to": [email.valor],
                "subject": "Seu link de acesso à Terramétrica",
                "html": (
                    f'<p>Clique para entrar: <a href="{link}">{link}</a> '
                    "(expira em 15 min).</p>"
                ),
            },
        )
        resposta.raise_for_status()  # 4xx/5xx do Resend → exceção → 502 na rota
