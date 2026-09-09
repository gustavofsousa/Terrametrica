"""Registro de observabilidade de consultas (DOS-30, AF-1).

Grava uma linha em `consulta_log` por consulta a `/dossie` — inclusive quando o resultado não é um
`Dossie` (fora do RJ, sobreposição): a consulta aconteceu e o produto precisa medir isso. Sem PII
(AD-002): só `conta_id` opaco, o lote consultado (quando houve), as camadas retornadas e a latência.

A escrita comita: o log é um efeito de borda que deve persistir mesmo que a leitura do dossiê tenha
usado a mesma conexão em modo somente-leitura. `registrar_consulta` recebe a conexão de fora (a rota
a abre por request), mantendo o I/O na borda.
"""

from dataclasses import dataclass, field

import psycopg

_INSERT_CONSULTA = """
    INSERT INTO consulta_log (conta_id, lote_id, camadas, latencia_ms)
    VALUES (%(conta_id)s, %(lote_id)s, %(camadas)s, %(latencia_ms)s)
"""


@dataclass(frozen=True, slots=True)
class EntradaConsulta:
    """Uma consulta a ser registrada (DOS-30)."""

    conta_id: str
    latencia_ms: int
    lote_id: str | None = None
    camadas: tuple[str, ...] = field(default_factory=tuple)


def registrar_consulta(conexao: psycopg.Connection, entrada: EntradaConsulta) -> None:
    """Grava e comita uma linha de `consulta_log` para a consulta descrita em `entrada`."""
    with conexao.cursor() as cursor:
        cursor.execute(
            _INSERT_CONSULTA,
            {
                "conta_id": entrada.conta_id,
                "lote_id": entrada.lote_id,
                "camadas": list(entrada.camadas),
                "latencia_ms": entrada.latencia_ms,
            },
        )
    conexao.commit()
