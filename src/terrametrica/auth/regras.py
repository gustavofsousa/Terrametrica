"""Regras puras de auth — decisões sem I/O (Fatia 7, T2).

Validação de e-mail no boundary (narrow, como `Coordenada` no domínio), geração e hash de token
opaco, e a regra de validade de um token de login. Nenhum acesso a banco/rede/e-mail vive aqui —
isso é responsabilidade das portas (T3) e adaptadores (T5).

O e-mail é a única PII que o módulo `auth` toca; `Email` a normaliza e valida, mas o value object
em si não a persiste — quem persiste é `credencial_login` via porta.
"""

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime

from terrametrica.dominio.modelos import ErroValidacao

# Validação pragmática de e-mail no boundary: uma parte local sem espaços, um @, um domínio com
# pelo menos um ponto. Não é a RFC 5322 inteira — narrow suficiente para barrar malformado óbvio
# sem falso-negativar endereços reais (o envio via Resend é a prova final de entregabilidade).
_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_BYTES_TOKEN = 32  # → ~43 chars urlsafe, alta entropia contra adivinhação de magic link/sessão.


@dataclass(frozen=True, slots=True)
class Email:
    """E-mail normalizado (lower/trim) e validado no boundary (PAINEL-02)."""

    valor: str

    def __init__(self, bruto: str) -> None:
        normalizado = bruto.strip().lower()
        if not _PADRAO_EMAIL.match(normalizado):
            raise ErroValidacao("e-mail inválido")
        object.__setattr__(self, "valor", normalizado)


@dataclass(frozen=True, slots=True)
class RegistroToken:
    """Estado de um magic link emitido, lido de `login_token` para avaliar validade."""

    hash_token: str
    email: Email
    expira_em: datetime
    usado_em: datetime | None


def gerar_token_opaco() -> str:
    """Token opaco de alta entropia para magic link ou sessão (o valor em claro)."""
    return secrets.token_urlsafe(_BYTES_TOKEN)


def hash_token(token: str) -> str:
    """Hash determinístico (sha256 hex) — é o que vai ao banco, nunca o valor em claro."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_valido(registro: RegistroToken, agora: datetime) -> bool:
    """Um magic link é válido se não expirou E ainda não foi usado (uso único, PAINEL-04)."""
    return registro.usado_em is None and agora < registro.expira_em
