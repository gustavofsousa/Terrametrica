"""Testes do serviço de auth (Fatia 7, T4) com fakes em memória das ports.

Derivados das ACs P1/P2 da spec `painel-web-conta`:
- PAINEL-01: e-mail válido → token salvo (15min) + link enviado.
- PAINEL-02: e-mail malformado → ErroValidacao (sem enviar).
- PAINEL-03: confirmar cria conta CONSULTA (nova) ou autentica (conhecida, sem duplicar).
- PAINEL-04: token expirado/usado → ResultadoLogin inválido; consumido não reautentica.
- PAINEL-05: 6ª solicitação/hora → LimiteDeLinksExcedido, nada enviado.
- PAINEL-13/14: logout invalida; sessão invalidada some.
- Edge cases da spec: reenvio (2 tokens válidos), falha do enviador propaga (→502).
"""

from datetime import datetime, timedelta

import pytest

from terrametrica.auth.regras import hash_token
from terrametrica.auth.servico import (
    EXPIRACAO_SESSAO,
    EXPIRACAO_TOKEN,
    LimiteDeLinksExcedido,
    confirmar_login,
    encerrar_sessao,
    solicitar_magic_link,
)
from terrametrica.dominio.modelos import ErroValidacao
from tests.fakes.auth_fake import (
    FakeEnviadorEmail,
    FakeRepositorioCredencial,
    FakeRepositorioSessao,
    FakeRepositorioToken,
)

AGORA = datetime(2026, 9, 11, 12, 0)
BASE_URL = "https://app.terrametrica.xyz"


def _tokens_emitidos(enviador: FakeEnviadorEmail) -> list[str]:
    """Extrai os tokens em claro dos links que o enviador recebeu."""
    return [link.split("token=")[1] for _, link in enviador.enviados]


class TestSolicitarMagicLink:
    def test_email_valido_salva_token_15min_e_envia_link(self) -> None:
        repo_token, repo_cred, enviador = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeEnviadorEmail(),
        )

        solicitar_magic_link("alice@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)

        assert len(enviador.enviados) == 1
        email_dest, link = enviador.enviados[0]
        assert email_dest == "alice@example.com"
        assert link.startswith(f"{BASE_URL}/auth/confirmar?token=")
        (registro,) = repo_token.registros.values()
        assert registro.expira_em == AGORA + EXPIRACAO_TOKEN
        assert registro.usado_em is None

    def test_email_malformado_levanta_e_nao_envia(self) -> None:
        repo_token, repo_cred, enviador = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeEnviadorEmail(),
        )

        with pytest.raises(ErroValidacao):
            solicitar_magic_link("sem-arroba", AGORA, repo_token, repo_cred, enviador, BASE_URL)

        assert enviador.enviados == []
        assert repo_token.registros == {}

    def test_sexta_solicitacao_na_janela_excede_limite_e_nao_envia(self) -> None:
        repo_token, repo_cred, enviador = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeEnviadorEmail(),
        )
        for i in range(5):
            solicitar_magic_link(
                "bob@example.com",
                AGORA + timedelta(minutes=i),
                repo_token,
                repo_cred,
                enviador,
                BASE_URL,
            )

        with pytest.raises(LimiteDeLinksExcedido):
            solicitar_magic_link(
                "bob@example.com",
                AGORA + timedelta(minutes=5),
                repo_token,
                repo_cred,
                enviador,
                BASE_URL,
            )

        assert len(enviador.enviados) == 5  # a 6ª não enviou

    def test_janela_desliza_permite_novo_link_apos_uma_hora(self) -> None:
        repo_token, repo_cred, enviador = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeEnviadorEmail(),
        )
        for i in range(5):
            solicitar_magic_link(
                "bob@example.com", AGORA + timedelta(minutes=i), repo_token, repo_cred, enviador,
                BASE_URL,
            )

        # 61 min depois do 1º: só 4 caem na janela de 1h → 6º link permitido.
        solicitar_magic_link(
            "bob@example.com", AGORA + timedelta(minutes=61), repo_token, repo_cred, enviador,
            BASE_URL,
        )
        assert len(enviador.enviados) == 6

    def test_falha_do_enviador_propaga(self) -> None:
        repo_token, repo_cred = FakeRepositorioToken(), FakeRepositorioCredencial()
        enviador = FakeEnviadorEmail(falhar=True)

        with pytest.raises(RuntimeError):
            solicitar_magic_link(
                "alice@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL
            )

    def test_nao_revela_se_email_tem_conta(self) -> None:
        # E-mail conhecido e desconhecido produzem o mesmo efeito observável (1 envio, 1 token).
        repo_token, enviador = FakeRepositorioToken(), FakeEnviadorEmail()
        repo_cred = FakeRepositorioCredencial(contas={"conhecido@example.com": "conta-99"})

        for email in ("conhecido@example.com", "novo@example.com"):
            solicitar_magic_link(email, AGORA, repo_token, repo_cred, enviador, BASE_URL)

        assert len(enviador.enviados) == 2
        assert len(repo_token.registros) == 2


class TestConfirmarLogin:
    def test_email_novo_cria_conta_consulta_e_abre_sessao(self) -> None:
        repo_token, repo_cred, repo_sessao = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeRepositorioSessao(),
        )
        enviador = FakeEnviadorEmail()
        solicitar_magic_link("nova@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)
        token = _tokens_emitidos(enviador)[0]

        resultado = confirmar_login(token, AGORA, repo_token, repo_cred, repo_sessao)

        assert resultado.valido is True
        assert resultado.conta_nova is True
        assert resultado.conta_id == "conta-1"
        assert repo_cred.contas["nova@example.com"] == "conta-1"  # conta persistida na credencial
        assert resultado.token_sessao is not None
        # sessão gravada como hash, 30 dias.
        conta = repo_sessao.conta_de_sessao(hash_token(resultado.token_sessao), AGORA)
        assert conta == "conta-1"
        conta_apos = repo_sessao.sessoes[hash_token(resultado.token_sessao)]
        assert conta_apos[1] == AGORA + EXPIRACAO_SESSAO

    def test_email_conhecido_autentica_sem_duplicar_conta(self) -> None:
        repo_token, repo_sessao = FakeRepositorioToken(), FakeRepositorioSessao()
        repo_cred = FakeRepositorioCredencial(contas={"joao@example.com": "conta-existente"})
        enviador = FakeEnviadorEmail()
        solicitar_magic_link("joao@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)
        token = _tokens_emitidos(enviador)[0]

        resultado = confirmar_login(token, AGORA, repo_token, repo_cred, repo_sessao)

        assert resultado.valido is True
        assert resultado.conta_nova is False
        assert resultado.conta_id == "conta-existente"
        assert len(repo_cred.contas) == 1  # não duplicou

    def test_token_invalido_inexistente_retorna_invalido(self) -> None:
        repo_token, repo_cred, repo_sessao = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeRepositorioSessao(),
        )
        resultado = confirmar_login("nao-existe", AGORA, repo_token, repo_cred, repo_sessao)

        assert resultado.valido is False
        assert resultado.token_sessao is None
        assert resultado.conta_id is None

    def test_token_expirado_retorna_invalido(self) -> None:
        repo_token, repo_cred, repo_sessao = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeRepositorioSessao(),
        )
        enviador = FakeEnviadorEmail()
        solicitar_magic_link("a@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)
        token = _tokens_emitidos(enviador)[0]

        depois = AGORA + EXPIRACAO_TOKEN + timedelta(seconds=1)
        resultado = confirmar_login(token, depois, repo_token, repo_cred, repo_sessao)

        assert resultado.valido is False

    def test_token_usado_nao_reautentica(self) -> None:
        repo_token, repo_cred, repo_sessao = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeRepositorioSessao(),
        )
        enviador = FakeEnviadorEmail()
        solicitar_magic_link("a@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)
        token = _tokens_emitidos(enviador)[0]

        primeiro = confirmar_login(token, AGORA, repo_token, repo_cred, repo_sessao)
        segundo = confirmar_login(token, AGORA, repo_token, repo_cred, repo_sessao)

        assert primeiro.valido is True
        assert segundo.valido is False  # uso único

    def test_reenvio_dois_tokens_validos_qualquer_um_autentica(self) -> None:
        # Edge case da spec: reenviar não invalida o token anterior.
        repo_token, repo_cred, repo_sessao = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeRepositorioSessao(),
        )
        enviador = FakeEnviadorEmail()
        solicitar_magic_link("a@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)
        solicitar_magic_link("a@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)
        t1, t2 = _tokens_emitidos(enviador)

        assert confirmar_login(t1, AGORA, repo_token, repo_cred, repo_sessao).valido is True
        assert confirmar_login(t2, AGORA, repo_token, repo_cred, repo_sessao).valido is True


class TestEncerrarSessao:
    def test_logout_invalida_sessao(self) -> None:
        repo_token, repo_cred, repo_sessao = (
            FakeRepositorioToken(),
            FakeRepositorioCredencial(),
            FakeRepositorioSessao(),
        )
        enviador = FakeEnviadorEmail()
        solicitar_magic_link("a@example.com", AGORA, repo_token, repo_cred, enviador, BASE_URL)
        token = _tokens_emitidos(enviador)[0]
        resultado = confirmar_login(token, AGORA, repo_token, repo_cred, repo_sessao)
        assert resultado.token_sessao is not None

        encerrar_sessao(resultado.token_sessao, repo_sessao)

        assert repo_sessao.conta_de_sessao(hash_token(resultado.token_sessao), AGORA) is None

    def test_logout_de_sessao_ja_invalidada_e_idempotente(self) -> None:
        repo_sessao = FakeRepositorioSessao()
        # invalidar uma sessão que nunca existiu não deve levantar.
        encerrar_sessao("token-fantasma", repo_sessao)
