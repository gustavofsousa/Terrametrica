"""Identidade opaca da conta a partir do header `X-Conta-Id` (AD-011).

Esta fatia NÃO faz autenticação real (login/senha/JWT são F1.11): recebe a identidade da conta como
um identificador opaco no header e a usa para chavear observabilidade (DOS-30) e cota (DOS-27). A
ausência do header é `401` — a identidade é pré-condição desses dois requisitos, mesmo sem login.

`conta_id_obrigatorio` é uma dependency FastAPI; mantê-la aqui isola o único ponto que muda quando o
mecanismo de auth real nascer — a rota continua pedindo `conta_id: str` sem saber de onde vem.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

HEADER_CONTA = "X-Conta-Id"

MENSAGEM_SEM_CONTA = (
    "identidade da conta ausente: informe o header X-Conta-Id "
    "(conta obrigatória, sem paywall — AD-011)"
)


def conta_id_obrigatorio(
    x_conta_id: Annotated[str | None, Header(alias=HEADER_CONTA)] = None,
) -> str:
    """Extrai o `conta_id` opaco do header; ausente ou vazio → 401 (AF-4)."""
    if x_conta_id is None or not x_conta_id.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAGEM_SEM_CONTA)
    return x_conta_id.strip()


ContaId = Annotated[str, Depends(conta_id_obrigatorio)]
