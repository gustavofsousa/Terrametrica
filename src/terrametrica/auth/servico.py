"""Serviço de auth: orquestra regras + ports nos 3 casos de uso (Fatia 7, T4).

`solicitar` → emite magic link. `confirmar` → autentica/cria conta e abre sessão. `encerrar` →
logout. Nenhum I/O direto aqui: banco e e-mail entram por ports (mesmo padrão de
`autorizacao/servico.py`). O tempo (`agora`) é injetado para o teste controlar expiração/janela.

Anti-enumeração: `solicitar_magic_link` nunca revela se o e-mail já tem conta — o fluxo é idêntico
para e-mail conhecido e desconhecido (a conta só nasce no `confirmar`).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from terrametrica.auth.portas import (
    EnviadorEmail,
    RepositorioCredencial,
    RepositorioSessao,
    RepositorioToken,
)
from terrametrica.auth.regras import Email, gerar_token_opaco, hash_token
from terrametrica.dominio.modelos import PapelConta

EXPIRACAO_TOKEN = timedelta(minutes=15)  # magic link (PAINEL-01)
EXPIRACAO_SESSAO = timedelta(days=30)  # cookie de sessão (spec: duração da sessão)
LIMITE_LINKS_POR_JANELA = 5  # rate limit por e-mail (PAINEL-05)
JANELA_RATE_LIMIT = timedelta(hours=1)


class LimiteDeLinksExcedido(Exception):
    """5 magic links já foram emitidos para o e-mail na última hora (PAINEL-05 → 429)."""


@dataclass(frozen=True, slots=True)
class ResultadoLogin:
    """Resultado do `confirmar_login`. `token_sessao` em claro para a rota setar o cookie.

    `valido=False` cobre token inexistente/expirado/já usado — sem distinguir qual (anti-oracle,
    PAINEL-04). Quando inválido, `token_sessao`/`conta_id` são `None`.
    """

    valido: bool
    token_sessao: str | None = None
    conta_id: str | None = None
    conta_nova: bool = False


def solicitar_magic_link(
    email_bruto: str,
    agora: datetime,
    repo_token: RepositorioToken,
    repo_cred: RepositorioCredencial,
    enviador: EnviadorEmail,
    base_url: str,
) -> None:
    """Valida o e-mail (ErroValidacao→422), aplica rate limit (LimiteDeLinksExcedido→429), gera e
    salva um magic link (hash) e o envia. Não revela se o e-mail já tem conta (anti-enumeração)."""
    email = Email(email_bruto)  # ErroValidacao se malformado (PAINEL-02)

    emitidos = repo_token.contar_na_janela(email, agora - JANELA_RATE_LIMIT)
    if emitidos >= LIMITE_LINKS_POR_JANELA:
        raise LimiteDeLinksExcedido()

    token = gerar_token_opaco()
    repo_token.salvar(hash_token(token), email, agora + EXPIRACAO_TOKEN)

    enviador.enviar_magic_link(email, f"{base_url}/auth/confirmar?token={token}")


def confirmar_login(
    token: str,
    agora: datetime,
    repo_token: RepositorioToken,
    repo_cred: RepositorioCredencial,
    repo_sessao: RepositorioSessao,
) -> ResultadoLogin:
    """Consome o magic link (atômico); se válido, autentica/cria a conta e abre sessão de 30 dias.

    Token inexistente/expirado/usado → `ResultadoLogin(valido=False)` (PAINEL-04). Conta nova nasce
    com papel `CONSULTA` (PAINEL-03); e-mail já conhecido reautentica sem duplicar conta.
    """
    registro = repo_token.consumir(hash_token(token), agora)
    if registro is None:
        return ResultadoLogin(valido=False)

    email = registro.email
    conta_id = repo_cred.conta_de_email(email)
    conta_nova = conta_id is None
    if conta_id is None:
        conta_id = repo_cred.criar_conta_para_email(email, PapelConta.CONSULTA)

    token_sessao = gerar_token_opaco()
    repo_sessao.criar(conta_id, hash_token(token_sessao), agora + EXPIRACAO_SESSAO)

    return ResultadoLogin(
        valido=True, token_sessao=token_sessao, conta_id=conta_id, conta_nova=conta_nova
    )


def encerrar_sessao(token_sessao: str, repo_sessao: RepositorioSessao) -> None:
    """Invalida a sessão corrente (logout, PAINEL-13). Idempotente: sessão ausente não é erro."""
    repo_sessao.invalidar(hash_token(token_sessao))
