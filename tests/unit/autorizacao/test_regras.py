"""Testes das regras puras de autorização (T2).

Derivadas de GATE-01, GATE-02, GATE-03 (`.specs/features/gate-juridico-p2/spec.md`).
"""

from terrametrica.autorizacao.regras import (
    avaliar_acesso_registral,
    estado_secao_proprietario,
)
from terrametrica.dominio.modelos import Indisponivel, Negado, PapelConta, Permitido


class TestAvaliarAcessoRegistral:
    def test_papel_habilitado_juridicamente_e_permitido(self) -> None:
        # GATE-01/03: só o papel habilitado obtém acesso
        assert avaliar_acesso_registral(PapelConta.HABILITADO_JURIDICAMENTE) == Permitido()

    def test_papel_consulta_e_negado(self) -> None:
        # GATE-03: papel "consulta" nunca acessa dado registral
        assert avaliar_acesso_registral(PapelConta.CONSULTA) == Negado()


class TestEstadoSecaoProprietario:
    def test_papel_consulta_ve_secao_indisponivel(self) -> None:
        # GATE-02: "indisponível nesta versão" para todos os papéis
        assert estado_secao_proprietario(PapelConta.CONSULTA) == Indisponivel()

    def test_papel_habilitado_juridicamente_tambem_ve_secao_indisponivel(self) -> None:
        # GATE-02: o papel não liga a camada sozinho (AD-002)
        assert estado_secao_proprietario(PapelConta.HABILITADO_JURIDICAMENTE) == Indisponivel()
