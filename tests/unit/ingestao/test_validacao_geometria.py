"""Normalização de geometria para o tipo das colunas (`MultiPolygon` 2D)."""

from shapely.geometry import MultiPolygon, Polygon  # type: ignore[import-untyped]

from terrametrica.ingestao.validacao_geometria import para_multipolygon

QUADRADO_Z = Polygon([(0, 0, 10), (1, 0, 10), (1, 1, 10), (0, 1, 10)])


def test_poligono_com_z_vira_multipolygon_2d() -> None:
    resultado = para_multipolygon(QUADRADO_Z)

    assert isinstance(resultado, MultiPolygon)
    assert not resultado.has_z
    assert resultado.area == 1.0


def test_multipolygon_com_z_perde_o_z() -> None:
    assert not para_multipolygon(MultiPolygon([QUADRADO_Z])).has_z
