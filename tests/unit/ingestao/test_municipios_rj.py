"""Validação e SHA canônico da malha municipal — spec:mapa-do-lote-rj (T2: MUN-04, MUN-05)."""

import geopandas as gpd  # type: ignore[import-untyped]
import pandas as pd
import pytest
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from terrametrica.ingestao.municipios_rj import (
    MalhaIncompleta,
    _validar_malha,
    sha256_canonico,
)
from tests.fakes.malha_municipal_fake import malha_sintetica


def test_mun04_malha_com_92_municipios_passa() -> None:
    _validar_malha(malha_sintetica(92))


@pytest.mark.parametrize("total", [91, 93])
def test_mun04_malha_com_contagem_errada_levanta_com_a_contagem_na_mensagem(total: int) -> None:
    with pytest.raises(MalhaIncompleta, match=f"{total} feições"):
        _validar_malha(malha_sintetica(total))


def test_mun04_codigo_fora_de_33_levanta() -> None:
    malha = malha_sintetica(92)
    malha.loc[0, "code_muni"] = 3500100.0

    with pytest.raises(MalhaIncompleta, match="1 fora de 33xxxxx"):
        _validar_malha(malha)


def test_mun04_geometria_vazia_levanta() -> None:
    malha = malha_sintetica(92)
    malha.loc[5, "geometry"] = Polygon()

    with pytest.raises(MalhaIncompleta, match="1 sem geometria"):
        _validar_malha(malha)


def test_mun04_codigo_duplicado_levanta() -> None:
    malha = malha_sintetica(92)
    malha.loc[1, "code_muni"] = malha.loc[0, "code_muni"]

    with pytest.raises(MalhaIncompleta, match="91 códigos distintos"):
        _validar_malha(malha)


def test_mun05_mesma_malha_em_ordem_diferente_tem_o_mesmo_sha() -> None:
    malha = malha_sintetica(10)
    embaralhada = gpd.GeoDataFrame(
        pd.concat([malha.iloc[5:], malha.iloc[:5]]), geometry="geometry", crs=malha.crs
    )

    assert sha256_canonico(malha) == sha256_canonico(embaralhada)


def test_mun05_malha_diferente_tem_sha_diferente() -> None:
    malha = malha_sintetica(10)
    alterada = malha.copy()
    alterada.loc[0, "name_muni"] = "Outro nome"

    assert sha256_canonico(malha) != sha256_canonico(alterada)
