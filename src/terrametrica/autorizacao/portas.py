"""Contratos (ports) que o serviço de autorização consome.

Só interfaces — nenhuma implementação, nenhum I/O importado. A persistência
real (Postgres) fica para a Slice 2 desta feature; nos testes, fakes em
memória cumprem estes contratos.
"""

from typing import Protocol

from terrametrica.dominio.modelos import Conta, EntradaAuditoria, PapelConta


class RepositorioContas(Protocol):
    """Leitura e transição de papel de uma conta."""

    def papel_de(self, conta_id: str) -> PapelConta:
        """Papel atual da conta. Levanta `ErroValidacao` se `conta_id` for desconhecido."""
        ...

    def promover(self, conta_id: str, novo_papel: PapelConta) -> Conta:
        """Muda o papel da conta e devolve a conta atualizada (GATE-04)."""
        ...


class LogAuditoria(Protocol):
    """Log de auditoria — só permite adicionar, nunca remover ou editar (GATE-05)."""

    def registrar(self, entrada: EntradaAuditoria) -> None:
        """Grava uma entrada de auditoria."""
        ...
