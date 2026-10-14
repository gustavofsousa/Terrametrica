"""O limite do RJ é pedido ao geobr em resolução completa — spec:mapa-do-lote-rj (T3, AD-016)."""

from datetime import date
from types import TracebackType
from typing import Any

import geopandas as gpd  # type: ignore[import-untyped]
from shapely.geometry import box  # type: ignore[import-untyped]

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.limite_rj import ingerir_limite_rj


class _CursorFake:
    def __init__(self) -> None:
        self.comandos: list[tuple[str, Any]] = []

    def __enter__(self) -> "_CursorFake":
        return self

    def __exit__(self, *_: type[BaseException] | TracebackType | None) -> None:
        return None

    def execute(self, comando: str, parametros: Any) -> None:
        self.comandos.append((comando, parametros))


class _ConexaoFake:
    def __init__(self) -> None:
        self.cursor_fake = _CursorFake()

    def cursor(self) -> _CursorFake:
        return self.cursor_fake


def test_ad016_pede_ano_2025_e_resolucao_completa_do_estado_33() -> None:
    chamadas: list[dict[str, Any]] = []

    def leitor_fake(**argumentos: Any) -> gpd.GeoDataFrame:
        chamadas.append(argumentos)
        return gpd.GeoDataFrame({"geometry": [box(-44, -23, -41, -21)]}, crs="EPSG:4674")

    conexao = _ConexaoFake()
    versao = VersaoBase(id="v", criada_em=date(2026, 10, 1))

    relatorio = ingerir_limite_rj(versao, conexao, ler=leitor_fake)  # type: ignore[arg-type]

    assert chamadas == [{"year": 2025, "code_state": 33, "simplified": False}]
    assert relatorio.feicoes_gravadas == 1
    assert len(conexao.cursor_fake.comandos) == 1
