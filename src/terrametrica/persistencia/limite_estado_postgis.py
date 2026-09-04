"""Adapter PostGIS do port `LimiteEstado` (`dossie/portas.py`).

`contem` não recebe `VersaoBase` (a assinatura do Protocol não tem esse parâmetro), então
a consulta não filtra por `versao_base_id`: qualquer polígono semeado em `limite_estado`
participa do `ST_Contains`. Nesta fatia só existe uma UF (RJ) e uma versão em uso — ver
design.md — então isso não é um problema prático agora; se o produto federar outras UFs
ou versões concorrentes de `limite_estado`, revisitar esta decisão.

Borda: usa `ST_Contains` (mesma função de `repositorio_lotes_postgis.lote_em`, por
consistência) — um ponto exatamente sobre o limite do polígono não é considerado dentro
(comportamento padrão do PostGIS para `ST_Contains`, testado explicitamente).
"""

from dataclasses import dataclass

import psycopg

from terrametrica.dominio.modelos import Coordenada

_SELECT_CONTEM = """
    SELECT EXISTS (
        SELECT 1 FROM limite_estado
        WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4674))
    )
"""


@dataclass
class LimiteEstadoPostGIS:
    """Fronteira estadual contra o PostGIS real."""

    conexao: psycopg.Connection

    def contem(self, coord: Coordenada) -> bool:
        with self.conexao.cursor() as cursor:
            cursor.execute(_SELECT_CONTEM, {"lon": coord.lon, "lat": coord.lat})
            linha = cursor.fetchone()
        assert linha is not None  # EXISTS(...) sempre devolve exatamente 1 linha
        (resultado,) = linha
        return bool(resultado)
