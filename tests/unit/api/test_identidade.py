"""Testes da resolução de identidade sessão-OU-header (Fatia 7, T6).

`resolver_conta_id` é pura (recebe as credenciais + um RepositorioSessao + o instante), então é
testada aqui com um fake em memória da sessão — sem DB. Cobre a precedência (PAINEL-07), a
retrocompat do header sozinho (Success Criteria 3 / F1.10), cookie inválido/expirado (Edge Case) e
a ausência total → 401 (PAINEL-12).
"""

from datetime import datetime

import pytest
from fastapi import HTTPException

from terrametrica.api.identidade import (
    CredenciaisRequest,
    _extrair_cookie,
    credenciais_da_request,
    resolver_conta_id,
)
from terrametrica.auth.regras import hash_token

AGORA = datetime(2026, 9, 11, 12, 0)


class FakeRepoSessao:
    """Sessões válidas: hash_sessao → conta_id. Expiração não modelada aqui (o teste passa hashes
    conhecidos como válidos; o inválido simplesmente não está no dict)."""

    def __init__(self, validas: dict[str, str]) -> None:
        self._validas = validas

    def criar(self, conta_id: str, hash_sessao: str, expira_em: datetime) -> None: ...

    def conta_de_sessao(self, hash_sessao: str, agora: datetime) -> str | None:
        return self._validas.get(hash_sessao)

    def invalidar(self, hash_sessao: str) -> None: ...


def _repo_com_sessao(token_claro: str, conta_id: str) -> FakeRepoSessao:
    return FakeRepoSessao({hash_token(token_claro): conta_id})


class TestExtrairCookie:
    def test_extrai_valor_do_cookie_nomeado(self) -> None:
        assert _extrair_cookie("outro=1; sessao=abc; mais=2", "sessao") == "abc"

    def test_cookie_ausente_devolve_none(self) -> None:
        assert _extrair_cookie("outro=1", "sessao") is None

    def test_cabecalho_vazio_devolve_none(self) -> None:
        assert _extrair_cookie(None, "sessao") is None


class TestResolverContaId:
    def test_cookie_valido_resolve_conta_da_sessao(self) -> None:
        cred = CredenciaisRequest(cookie_sessao="tok-sessao", header_conta=None)
        repo = _repo_com_sessao("tok-sessao", "conta-da-sessao")

        assert resolver_conta_id(cred, repo, AGORA) == "conta-da-sessao"

    def test_sem_cookie_cai_para_o_header(self) -> None:
        cred = CredenciaisRequest(cookie_sessao=None, header_conta="conta-header")
        repo = FakeRepoSessao({})

        assert resolver_conta_id(cred, repo, AGORA) == "conta-header"

    def test_sessao_tem_precedencia_sobre_header(self) -> None:
        cred = CredenciaisRequest(cookie_sessao="tok-sessao", header_conta="conta-header")
        repo = _repo_com_sessao("tok-sessao", "conta-da-sessao")

        assert resolver_conta_id(cred, repo, AGORA) == "conta-da-sessao"

    def test_cookie_invalido_expirado_cai_para_o_header(self) -> None:
        # cookie presente mas não corresponde a sessão válida → usa o header (nunca 5xx).
        cred = CredenciaisRequest(cookie_sessao="tok-corrompido", header_conta="conta-header")
        repo = FakeRepoSessao({})  # nenhuma sessão válida

        assert resolver_conta_id(cred, repo, AGORA) == "conta-header"

    def test_cookie_invalido_e_sem_header_resulta_401(self) -> None:
        cred = CredenciaisRequest(cookie_sessao="tok-corrompido", header_conta=None)
        repo = FakeRepoSessao({})

        with pytest.raises(HTTPException) as exc:
            resolver_conta_id(cred, repo, AGORA)
        assert exc.value.status_code == 401

    def test_sem_cookie_e_sem_header_resulta_401(self) -> None:
        cred = CredenciaisRequest(cookie_sessao=None, header_conta=None)
        repo = FakeRepoSessao({})

        with pytest.raises(HTTPException) as exc:
            resolver_conta_id(cred, repo, AGORA)
        assert exc.value.status_code == 401

    def test_header_apenas_espacos_nao_autentica(self) -> None:
        cred = CredenciaisRequest(cookie_sessao=None, header_conta="   ")
        repo = FakeRepoSessao({})

        with pytest.raises(HTTPException):
            resolver_conta_id(cred, repo, AGORA)


class TestCredenciaisDaRequest:
    def test_extrai_cookie_e_header_da_request(self) -> None:
        cred = credenciais_da_request(x_conta_id="conta-x", sessao="sessao=tok; outro=9")
        assert cred.cookie_sessao == "tok"
        assert cred.header_conta == "conta-x"

    def test_sem_nada_devolve_ambos_none(self) -> None:
        cred = credenciais_da_request(x_conta_id=None, sessao=None)
        assert cred.cookie_sessao is None
        assert cred.header_conta is None
