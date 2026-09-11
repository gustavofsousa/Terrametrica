"""Contratos (ports) que o serviço de auth consome (Fatia 7, T3).

Só interfaces — nenhuma implementação, nenhum I/O importado. Os adaptadores reais (Postgres +
Resend) ficam em `auth/adaptadores.py` (T5); nos testes, fakes em memória cumprem estes contratos
(mesmo padrão de `autorizacao/portas.py` + `tests/fakes/`).

Todas as chaves de token são o **hash** (nunca o valor em claro): quem passa `hash_token`/
`hash_sessao` já hasheou via `auth.regras.hash_token`.
"""

from datetime import datetime
from typing import Protocol

from terrametrica.auth.regras import Email, RegistroToken
from terrametrica.dominio.modelos import PapelConta


class RepositorioCredencial(Protocol):
    """e-mail ↔ conta. A única fronteira que persiste PII de login (`credencial_login`)."""

    def conta_de_email(self, email: Email) -> str | None:
        """`conta_id` do e-mail, ou `None` se nunca visto (cadastro implícito no confirmar)."""
        ...

    def criar_conta_para_email(self, email: Email, papel: PapelConta) -> str:
        """Cria a conta do e-mail nunca visto e devolve o `conta_id` gerado (papel CONSULTA)."""
        ...


class RepositorioToken(Protocol):
    """Magic links emitidos (`login_token`). Guarda hash, uso único."""

    def salvar(self, hash_token: str, email: Email, expira_em: datetime) -> None:
        """Grava um novo magic link (hash), com sua janela de expiração."""
        ...

    def consumir(self, hash_token: str, agora: datetime) -> RegistroToken | None:
        """Valida+marca usado numa transação atômica; devolve o registro consumido ou `None`.

        Atômico de propósito (PAINEL-04): dois cliques simultâneos no mesmo link não autenticam
        duas vezes — o segundo vê o token já usado e recebe `None`.
        """
        ...

    def contar_na_janela(self, email: Email, desde: datetime) -> int:
        """Quantos magic links foram emitidos para o e-mail desde `desde` (rate limit 5/h)."""
        ...


class RepositorioSessao(Protocol):
    """Sessões ativas (`sessao`). Guarda hash do token de sessão, nunca o valor."""

    def criar(self, conta_id: str, hash_sessao: str, expira_em: datetime) -> None:
        """Grava uma sessão (hash) para a conta, com expiração de 30 dias."""
        ...

    def conta_de_sessao(self, hash_sessao: str, agora: datetime) -> str | None:
        """`conta_id` da sessão válida (não expirada), ou `None` (expirada/inexistente)."""
        ...

    def invalidar(self, hash_sessao: str) -> None:
        """Remove a sessão (logout). Idempotente: invalidar duas vezes não é erro."""
        ...


class EnviadorEmail(Protocol):
    """Envio do magic link. Levanta em falha (→ 502): nunca finge que enviou."""

    def enviar_magic_link(self, email: Email, link: str) -> None:
        """Envia o e-mail com o link de login. Exceção em falha propaga para a rota."""
        ...
