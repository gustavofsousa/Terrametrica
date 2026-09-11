"""Identidade da conta: por sessão (cookie) OU header `X-Conta-Id` (Fatia 6 → Fatia 7).

A Fatia 6 (AD-011) resolvia identidade só pelo header opaco. A Fatia 7 (F1.11) adiciona a **sessão
real** de login: o painel autentica por cookie httpOnly, e a API resolve `conta_id` a partir dele.
O header continua valendo para clientes de API que não usam o painel (Success Criteria 3 — F1.10
intacta). Precedência: **sessão > header**.

Divisão de responsabilidade para manter o I/O na borda:
- `credenciais_da_request` é uma dependency FastAPI **pura** (sem DB): extrai o cookie e o header.
- `resolver_conta_id` recebe a conexão já aberta pela rota + um `RepositorioSessao` e faz a
  resolução real (consulta a sessão só se houver cookie). Assim o único ponto que abre conexão
  continua sendo a rota, como na Fatia 6.

Cookie corrompido/expirado → `conta_de_sessao` devolve `None` → cai para o header; sem header → 401.
Nunca 5xx por cookie inválido (Edge Case da spec).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from terrametrica.auth.portas import RepositorioSessao
from terrametrica.auth.regras import hash_token

HEADER_CONTA = "X-Conta-Id"
COOKIE_SESSAO = "sessao"

MENSAGEM_SEM_CONTA = (
    "identidade da conta ausente: faça login no painel (cookie de sessão) "
    "ou informe o header X-Conta-Id (cliente de API)"
)


@dataclass(frozen=True, slots=True)
class CredenciaisRequest:
    """O que a request carrega para identificar a conta, antes de tocar o banco."""

    cookie_sessao: str | None
    header_conta: str | None


def credenciais_da_request(
    x_conta_id: Annotated[str | None, Header(alias=HEADER_CONTA)] = None,
    sessao: Annotated[str | None, Header(alias="cookie")] = None,
) -> CredenciaisRequest:
    """Extrai cookie de sessão + header, sem I/O. O cookie é lido do header `Cookie` bruto."""
    return CredenciaisRequest(
        cookie_sessao=_extrair_cookie(sessao, COOKIE_SESSAO),
        header_conta=x_conta_id,
    )


def _extrair_cookie(cabecalho_cookie: str | None, nome: str) -> str | None:
    """Lê o valor de um cookie do cabeçalho `Cookie` bruto (`a=1; b=2`)."""
    if not cabecalho_cookie:
        return None
    for par in cabecalho_cookie.split(";"):
        chave, _, valor = par.strip().partition("=")
        if chave == nome and valor:
            return valor
    return None


def conta_id_obrigatorio(
    x_conta_id: Annotated[str | None, Header(alias=HEADER_CONTA)] = None,
) -> str:
    """Resolução só-header (Fatia 6). Mantida para clientes de API que não usam sessão."""
    if x_conta_id is None or not x_conta_id.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAGEM_SEM_CONTA)
    return x_conta_id.strip()


def resolver_conta_id(
    credenciais: CredenciaisRequest,
    repo_sessao: RepositorioSessao,
    agora: datetime,
) -> str:
    """Resolve `conta_id`: sessão (cookie) tem precedência; senão o header; senão 401.

    `agora` é o instante da request (o mesmo relógio injetado em `criar_app`), usado para descartar
    sessão expirada. Cookie ausente/inválido/expirado → cai para o header; sem header → 401.
    """
    if credenciais.cookie_sessao:
        conta_id = repo_sessao.conta_de_sessao(hash_token(credenciais.cookie_sessao), agora)
        if conta_id is not None:
            return conta_id

    if credenciais.header_conta and credenciais.header_conta.strip():
        return credenciais.header_conta.strip()

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAGEM_SEM_CONTA)


Credenciais = Annotated[CredenciaisRequest, Depends(credenciais_da_request)]
ContaId = Annotated[str, Depends(conta_id_obrigatorio)]
