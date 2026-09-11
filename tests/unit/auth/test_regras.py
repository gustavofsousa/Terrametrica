"""Testes das regras puras de auth (Fatia 7, T2).

Derivados das ACs da spec `painel-web-conta`:
- PAINEL-02: e-mail malformado → ErroValidacao (vira 422 no boundary da rota).
- PAINEL-04: token expirado ou já usado → inválido (vira 401 no confirmar).

Regras puras, sem I/O — nenhum fake necessário, só entrada/saída.
"""

from datetime import datetime, timedelta

import pytest

from terrametrica.auth.regras import (
    Email,
    RegistroToken,
    gerar_token_opaco,
    hash_token,
    token_valido,
)
from terrametrica.dominio.modelos import ErroValidacao

AGORA = datetime(2026, 9, 11, 12, 0)


class TestEmail:
    def test_normaliza_lower_e_trim(self) -> None:
        assert Email("  Alice@Example.COM ").valor == "alice@example.com"

    @pytest.mark.parametrize(
        "bruto",
        ["", "  ", "semarroba", "a@", "@b.com", "a@b", "a b@c.com", "a@b .com"],
    )
    def test_email_malformado_levanta_erro_validacao(self, bruto: str) -> None:
        with pytest.raises(ErroValidacao):
            Email(bruto)


class TestTokenOpaco:
    def test_gera_token_de_alta_entropia_unico(self) -> None:
        t1, t2 = gerar_token_opaco(), gerar_token_opaco()
        assert t1 != t2
        assert len(t1) >= 32  # secrets.token_urlsafe(32) → ~43 chars

    def test_hash_e_deterministico_e_nao_e_o_valor_em_claro(self) -> None:
        token = "abc123"
        assert hash_token(token) == hash_token(token)
        assert hash_token(token) != token
        assert len(hash_token(token)) == 64  # sha256 hex


class TestTokenValido:
    def _registro(self, *, expira_em: datetime, usado_em: datetime | None) -> RegistroToken:
        return RegistroToken(
            hash_token="h", email=Email("a@b.com"), expira_em=expira_em, usado_em=usado_em
        )

    def test_token_novo_dentro_da_janela_e_valido(self) -> None:
        reg = self._registro(expira_em=AGORA + timedelta(minutes=15), usado_em=None)
        assert token_valido(reg, AGORA) is True

    def test_token_expirado_e_invalido(self) -> None:
        reg = self._registro(expira_em=AGORA - timedelta(seconds=1), usado_em=None)
        assert token_valido(reg, AGORA) is False

    def test_token_ja_usado_e_invalido(self) -> None:
        reg = self._registro(
            expira_em=AGORA + timedelta(minutes=15), usado_em=AGORA - timedelta(minutes=1)
        )
        assert token_valido(reg, AGORA) is False
