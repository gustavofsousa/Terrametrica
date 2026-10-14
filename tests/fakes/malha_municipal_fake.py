"""Malha municipal sintética para testes (spec:mapa-do-lote-rj): quadrados lado a lado."""

import geopandas as gpd  # type: ignore[import-untyped]
from shapely.geometry import box  # type: ignore[import-untyped]

CRS = "EPSG:4674"


def malha_sintetica(
    total: int = 92, *, prefixo: str = "33", codigos: tuple[str, ...] = ()
) -> gpd.GeoDataFrame:
    """`total` municípios com código `{prefixo}{n:05d}` (7 dígitos), no formato do geobr.

    `codigos` substitui os códigos das primeiras feições, para que os municípios de uma fixture
    de lotes existam na malha.
    """
    linhas = [
        {
            "code_muni": float(codigos[n] if n < len(codigos) else f"{prefixo}{n:05d}"),
            "name_muni": f"Município {n:02d}",
            "geometry": box(-44 + n * 0.02, -23, -44 + n * 0.02 + 0.02, -22.9),
        }
        for n in range(total)
    ]
    return gpd.GeoDataFrame(linhas, geometry="geometry", crs=CRS)
