"""Materialização de intersecções lote × restrição (AD-007) — Fatia 3.

O cálculo caro (`ST_Intersection`/`ST_Area`) roda em SQL, num único spatial join usando o índice
GiST de `restricao.geom` (migração 0003) — nunca em loop Python (design.md "Fatia 3", Risks &
Concerns: ~430k feições de restrição inviabilizam iteração em Python no caminho de ingestão).

`pct_do_lote`/`marginal` (DOS-08) não são calculados nem gravados aqui — são cálculo puro em
`geometria.classificar_intersecao`, já rodado por `dossie/montagem.py` na leitura (T4/T5, contrato
inalterado). Esta função só grava a área bruta da intersecção.

Idempotente: rodar duas vezes sobre a mesma versão não duplica linha (chave primária composta
`(lote_id, restricao_id, versao_base_id)` + `ON CONFLICT DO NOTHING`).
"""

import psycopg

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.tipos import RelatorioIntersecoes

_MATERIALIZAR_INTERSECOES = """
    INSERT INTO intersecao_materializada (lote_id, restricao_id, area_intersecao_m2, versao_base_id)
    SELECT id_lote, id_restricao, area_m2, %(versao)s
    FROM (
        SELECT
            l.id AS id_lote,
            r.id AS id_restricao,
            ST_Area(ST_Intersection(l.geom_sigef, r.geom)::geography) AS area_m2
        FROM lote_rural l
        JOIN restricao r
            ON r.versao_base_id = l.versao_base_id
            AND ST_Intersects(l.geom_sigef, r.geom)
        WHERE l.versao_base_id = %(versao)s
    ) calculado
    WHERE area_m2 > 0
    ON CONFLICT (lote_id, restricao_id, versao_base_id) DO NOTHING
"""

_MATERIALIZAR_INTERSECOES_URBANAS = """
    INSERT INTO intersecao_materializada (lote_id, restricao_id, area_intersecao_m2, versao_base_id)
    SELECT id_lote, id_restricao, area_m2, %(versao)s
    FROM (
        SELECT
            l.id AS id_lote,
            r.id AS id_restricao,
            ST_Area(ST_Intersection(l.geom, r.geom)::geography) AS area_m2
        FROM lote_urbano l
        JOIN restricao r
            ON r.versao_base_id = l.versao_base_id
            AND r.tipo NOT IN ('app', 'reserva_legal')
            AND ST_Intersects(l.geom, r.geom)
        WHERE l.versao_base_id = %(versao)s
    ) calculado
    WHERE area_m2 > 0
    ON CONFLICT (lote_id, restricao_id, versao_base_id) DO NOTHING
"""


def materializar_intersecoes(
    versao: VersaoBase, conexao: psycopg.Connection
) -> RelatorioIntersecoes:
    """Cruza cada `lote_rural` com toda `restricao` da mesma versão e grava os pares com
    intersecção real (área > 0) em `intersecao_materializada`."""
    with conexao.cursor() as cursor:
        cursor.execute(_MATERIALIZAR_INTERSECOES, {"versao": versao.id})
        pares = cursor.rowcount
        # INVARIANT: APP e Reserva Legal são do CAR e só valem para lote rural (dossie.md).
        cursor.execute(_MATERIALIZAR_INTERSECOES_URBANAS, {"versao": versao.id})
        pares += cursor.rowcount

    return RelatorioIntersecoes(versao_base_id=versao.id, pares_materializados=pares)
