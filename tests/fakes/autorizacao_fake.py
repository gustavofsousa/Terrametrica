"""Fakes em memória dos ports de autorização — usados só nos testes do serviço.

Cumprem `RepositorioContas` e `LogAuditoria` (`autorizacao/portas.py`) sem I/O.
"""

from dataclasses import dataclass, field

from terrametrica.dominio.modelos import Conta, EntradaAuditoria, ErroValidacao, PapelConta


@dataclass
class FakeRepositorioContas:
    """Contas fake, indexadas por id. Configurar via `contas` no construtor do teste."""

    contas: dict[str, Conta] = field(default_factory=dict)

    def papel_de(self, conta_id: str) -> PapelConta:
        conta = self.contas.get(conta_id)
        if conta is None:
            raise ErroValidacao(f"conta desconhecida: {conta_id}")
        return conta.papel

    def promover(self, conta_id: str, novo_papel: PapelConta) -> Conta:
        conta = self.contas.get(conta_id)
        if conta is None:
            raise ErroValidacao(f"conta desconhecida: {conta_id}")
        promovida = Conta(id=conta_id, papel=novo_papel)
        self.contas[conta_id] = promovida
        return promovida


@dataclass
class FakeLogAuditoria:
    """Log fake: só acumula (`registrar`) — mesma garantia de append-only do Protocol real."""

    entradas: list[EntradaAuditoria] = field(default_factory=list)

    def registrar(self, entrada: EntradaAuditoria) -> None:
        self.entradas.append(entrada)
