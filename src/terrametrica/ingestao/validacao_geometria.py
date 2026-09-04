"""Correção de geometria inválida na ingestão — equivalente Shapely a `ST_MakeValid`.

Regra de produto (não é decisão desta fase): geometria inválida é corrigida, nunca descartada
silenciosamente. Função pura, sem I/O — `ingerir_limite_rj`/`ingerir_sigef` decidem onde
carimbar o sinal de correção (coluna `geometria_corrigida` quando a tabela tem essa coluna;
contagem no `RelatorioCamada` quando não tem, caso de `limite_estado`). Compartilhada pelas
duas ingestões em vez de duplicada — é a mesma regra de negócio nos dois lugares.
"""

from shapely import make_valid  # type: ignore[import-untyped]
from shapely.geometry import MultiPolygon, Polygon  # type: ignore[import-untyped]
from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]


def corrigir_geometria(geom: BaseGeometry) -> tuple[BaseGeometry, bool]:
    """Devolve `(geometria válida, foi_corrigida)`. Não modifica geometria já válida."""
    if geom.is_valid:
        return geom, False
    return make_valid(geom), True


def para_multipolygon(geom: BaseGeometry) -> MultiPolygon:
    """Normaliza para `MultiPolygon` — tipo de coluna de todas as geometrias desta fatia.

    `Polygon` vira `MultiPolygon` de um membro; `MultiPolygon` passa direto. Qualquer outro
    tipo (ex.: `GeometryCollection` de uma correção degenerada) levanta erro explícito em vez
    de gravar silenciosamente um dado incorreto.
    """
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    raise ValueError(f"geometria não é Polygon/MultiPolygon após correção: {geom.geom_type}")
