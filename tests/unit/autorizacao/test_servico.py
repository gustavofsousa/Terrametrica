"""Testes do serviço de autorização (T4).

Derivados de GATE-03, GATE-04, GATE-05 (`.specs/features/gate-juridico-p2/spec.md`).
"""

from datetime import datetime

import pytest

from terrametrica.autorizacao.servico import promover_conta, solicitar_dado_registral
from terrametrica.dominio.modelos import (
    Conta,
    ErroValidacao,
    Negado,
    PapelConta,
    Permitido,
    TipoEventoAuditoria,
)
from tests.fakes.autorizacao_fake import FakeLogAuditoria, FakeRepositorioContas

INSTANTE = datetime(2026, 9, 3, 12, 0)


class TestSolicitarDadoRegistral:
    def test_conta_consulta_e_negada_e_gera_uma_entrada_de_log(self) -> None:
        # GATE-03/05: papel "consulta" nunca acessa, e a tentativa é registrada
        repo = FakeRepositorioContas(contas={"c1": Conta(id="c1", papel=PapelConta.CONSULTA)})
        log = FakeLogAuditoria()

        resultado = solicitar_dado_registral(
            conta_id="c1",
            finalidade="due diligence",
            lote_id="RJ-1",
            instante=INSTANTE,
            repo=repo,
            log=log,
        )

        assert resultado == Negado()
        assert len(log.entradas) == 1
        entrada = log.entradas[0]
        assert entrada.tipo is TipoEventoAuditoria.CONSULTA_REGISTRAL
        assert entrada.conta_id == "c1"
        assert entrada.finalidade == "due diligence"
        assert entrada.lote_id == "RJ-1"
        assert entrada.ts == INSTANTE

    def test_conta_habilitada_e_permitida_e_gera_uma_entrada_de_log(self) -> None:
        # GATE-03/05: papel habilitado acessa, e a consulta também é registrada
        repo = FakeRepositorioContas(
            contas={"c2": Conta(id="c2", papel=PapelConta.HABILITADO_JURIDICAMENTE)}
        )
        log = FakeLogAuditoria()

        resultado = solicitar_dado_registral(
            conta_id="c2",
            finalidade="análise de crédito",
            lote_id="RJ-2",
            instante=INSTANTE,
            repo=repo,
            log=log,
        )

        assert resultado == Permitido()
        assert len(log.entradas) == 1
        assert log.entradas[0].tipo is TipoEventoAuditoria.CONSULTA_REGISTRAL

    def test_duas_consultas_no_mesmo_instante_geram_duas_entradas_distintas(self) -> None:
        # Edge case do spec.md: auditoria nunca deduplica, mesmo com timestamp igual
        repo = FakeRepositorioContas(
            contas={"c1": Conta(id="c1", papel=PapelConta.HABILITADO_JURIDICAMENTE)}
        )
        log = FakeLogAuditoria()

        for _ in range(2):
            solicitar_dado_registral(
                conta_id="c1",
                finalidade="due diligence",
                lote_id="RJ-1",
                instante=INSTANTE,
                repo=repo,
                log=log,
            )

        assert len(log.entradas) == 2
        assert log.entradas[0].id != log.entradas[1].id

    def test_conta_desconhecida_propaga_erro_sem_gerar_log(self) -> None:
        repo = FakeRepositorioContas(contas={})
        log = FakeLogAuditoria()

        with pytest.raises(ErroValidacao, match="desconhecida"):
            solicitar_dado_registral(
                conta_id="fantasma",
                finalidade="x",
                lote_id="RJ-3",
                instante=INSTANTE,
                repo=repo,
                log=log,
            )

        assert log.entradas == []


class TestPromoverConta:
    def test_promocao_registra_quem_quando_e_credencial(self) -> None:
        # GATE-04: quem promoveu, quando e sob qual credencial verificada
        repo = FakeRepositorioContas(contas={"c1": Conta(id="c1", papel=PapelConta.CONSULTA)})
        log = FakeLogAuditoria()

        conta = promover_conta(
            conta_id="c1",
            promovido_por="operador-01",
            credencial_verificada="OAB/RJ 123456",
            instante=INSTANTE,
            repo=repo,
            log=log,
        )

        assert conta.papel is PapelConta.HABILITADO_JURIDICAMENTE
        assert len(log.entradas) == 1
        entrada = log.entradas[0]
        assert entrada.tipo is TipoEventoAuditoria.PROMOCAO
        assert entrada.promovido_por == "operador-01"
        assert entrada.credencial_verificada == "OAB/RJ 123456"
        assert entrada.ts == INSTANTE

    def test_conta_promovida_passa_a_ser_permitida_em_solicitacao_seguinte(self) -> None:
        # Confirma que a promoção realmente muda a decisão de acesso subsequente
        repo = FakeRepositorioContas(contas={"c1": Conta(id="c1", papel=PapelConta.CONSULTA)})
        log = FakeLogAuditoria()

        promover_conta(
            conta_id="c1",
            promovido_por="operador-01",
            credencial_verificada="OAB/RJ 123456",
            instante=INSTANTE,
            repo=repo,
            log=log,
        )
        resultado = solicitar_dado_registral(
            conta_id="c1",
            finalidade="due diligence",
            lote_id="RJ-1",
            instante=INSTANTE,
            repo=repo,
            log=log,
        )

        assert resultado == Permitido()
        assert len(log.entradas) == 2
