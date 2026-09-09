"""Cota de consultas por conta — janela deslizante em memória de processo (DOS-27, AD-011).

MVP de um processo só: o contador é um `dict[conta_id, deque[datetime]]`. `checar` registra a
tentativa e devolve `Permitido` ou `Bloqueado(segundos_ate_renovar)` — o chamador (rota) traduz o
`Bloqueado` em `429` + `Retry-After`. Puro e injetável: nenhuma dependência de FastAPI aqui, então
o backend do contador (Redis, quando o deploy escalar para N réplicas) troca sem tocar a rota.

Débito assumido (AD-011): o contador zera no restart do processo e não é compartilhado entre
réplicas — aceitável no MVP, registrado em TECH-DEBT.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

LIMITE_POR_JANELA = 100
JANELA = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class Permitido:
    """A consulta cabe na cota."""


@dataclass(frozen=True, slots=True)
class Bloqueado:
    """Cota estourada — `retry_after_segundos` até a janela liberar a próxima vaga."""

    retry_after_segundos: int


ResultadoCota = Permitido | Bloqueado


@dataclass
class LimitadorEmMemoria:
    """Janela deslizante de `LIMITE_POR_JANELA` consultas por `JANELA`, por conta."""

    limite: int = LIMITE_POR_JANELA
    janela: timedelta = JANELA
    _consultas: dict[str, deque[datetime]] = field(
        default_factory=lambda: defaultdict(deque), init=False, repr=False
    )

    def checar(self, conta_id: str, agora: datetime) -> ResultadoCota:
        """Registra a tentativa de `conta_id` em `agora` e decide se ela passa.

        Uma tentativa bloqueada NÃO consome vaga (não é registrada) — senão uma conta em rajada
        nunca renovaria, porque cada 429 empurraria a janela para frente indefinidamente.
        """
        registros = self._consultas[conta_id]
        limite_inferior = agora - self.janela
        while registros and registros[0] <= limite_inferior:
            registros.popleft()

        if len(registros) >= self.limite:
            renova_em = registros[0] + self.janela
            segundos = max(1, _ceil_segundos(renova_em - agora))
            return Bloqueado(retry_after_segundos=segundos)

        registros.append(agora)
        return Permitido()


def _ceil_segundos(delta: timedelta) -> int:
    """Segundos arredondados para cima — Retry-After nunca subestima a espera."""
    total = delta.total_seconds()
    inteiro = int(total)
    return inteiro + 1 if total > inteiro else inteiro
