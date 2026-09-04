"""Serviço de autorização: orquestra ports e regras do gate jurídico (P2).

Toda decisão de acesso registral produz exatamente uma entrada de log — permitida
ou negada — antes de devolver o resultado (GATE-05). O log é uma obrigação
síncrona: se `log.registrar` falhar, a exceção propaga e nenhum resultado é
devolvido sem o registro correspondente.
"""

from datetime import datetime

from terrametrica.autorizacao.portas import LogAuditoria, RepositorioContas
from terrametrica.autorizacao.regras import avaliar_acesso_registral
from terrametrica.dominio.modelos import (
    Conta,
    EntradaAuditoria,
    PapelConta,
    ResultadoAcesso,
    TipoEventoAuditoria,
)


def solicitar_dado_registral(
    conta_id: str,
    finalidade: str,
    lote_id: str,
    instante: datetime,
    repo: RepositorioContas,
    log: LogAuditoria,
) -> ResultadoAcesso:
    """Decide o acesso a dado registral e sempre registra a tentativa (GATE-03/05).

    `repo.papel_de` propaga `ErroValidacao` para conta desconhecida antes de
    qualquer entrada de log ser criada — falha visível, não um `Negado` silencioso.
    """
    papel = repo.papel_de(conta_id)
    resultado = avaliar_acesso_registral(papel)
    log.registrar(
        EntradaAuditoria(
            id=f"{conta_id}:{instante.isoformat()}",
            ts=instante,
            conta_id=conta_id,
            tipo=TipoEventoAuditoria.CONSULTA_REGISTRAL,
            finalidade=finalidade,
            lote_id=lote_id,
        )
    )
    return resultado


def promover_conta(
    conta_id: str,
    promovido_por: str,
    credencial_verificada: str,
    instante: datetime,
    repo: RepositorioContas,
    log: LogAuditoria,
) -> Conta:
    """Promove a conta a `HABILITADO_JURIDICAMENTE` e registra quem, quando e
    sob qual credencial (GATE-04)."""
    conta = repo.promover(conta_id, PapelConta.HABILITADO_JURIDICAMENTE)
    log.registrar(
        EntradaAuditoria(
            id=f"{conta_id}:{instante.isoformat()}",
            ts=instante,
            conta_id=conta_id,
            tipo=TipoEventoAuditoria.PROMOCAO,
            promovido_por=promovido_por,
            credencial_verificada=credencial_verificada,
        )
    )
    return conta
