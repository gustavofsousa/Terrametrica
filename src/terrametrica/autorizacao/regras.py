"""Regras puras de autorização do gate jurídico (P2, AD-002).

Funções puras: decidem sobre o papel da conta, sem I/O. A camada registral
nunca liga nesta versão — `CAMADA_REGISTRAL_LIGADA` é uma constante, não uma
config externa (nenhuma fatia do produto criou um mecanismo de config ainda).
"""

from terrametrica.dominio.modelos import (
    EstadoSecao,
    Indisponivel,
    Negado,
    PapelConta,
    Permitido,
    ResultadoAcesso,
)

CAMADA_REGISTRAL_LIGADA = False


def avaliar_acesso_registral(papel: PapelConta) -> ResultadoAcesso:
    """Decide o acesso a dado registral pelo papel da conta (GATE-01, GATE-03)."""
    if papel is PapelConta.HABILITADO_JURIDICAMENTE:
        return Permitido()
    return Negado()


def estado_secao_proprietario(papel: PapelConta) -> EstadoSecao:
    """Estado da seção de proprietário, para qualquer papel (GATE-02).

    Sempre "indisponível nesta versão" enquanto `CAMADA_REGISTRAL_LIGADA` for
    `False` — o papel da conta não liga a camada sozinho.
    """
    del papel  # nenhum papel muda o resultado enquanto a camada está desligada (GATE-02)
    return Indisponivel()
