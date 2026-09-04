"""Ingestão das camadas de restrição do CAR (APP e Reserva Legal) — sem download programático,
mesma decisão herdada da Fase 0 para SIGEF/CAR (SICAR não automatiza download).

`ingerir_app_car` e `ingerir_reserva_legal_car` compartilham a mesma lógica (`cod_tema`/`nom_tema`/
`cod_imovel`/`ind_status` — mesmo schema real nas duas camadas, ver Fase 0/design.md "Fatia 3") via
`_ingerir_camada_restricao_car`, só o `tipo`/`Camada`/caminho de arquivo mudam.

Filtra `ind_status == 'AT'` (ativo) — `PE`/`CA`/`SU` não são declaração vigente (mesmo raciocínio
de `status='CERTIFICADA'` em `sigef.py`). Grava em `restricao`, nunca em `lote_rural` — estas são
camadas de restrição cruzadas com o lote (DOS-07), não uma segunda identidade do imóvel (essa é
P2, fora desta fatia — ver design.md).
"""

from datetime import date, datetime
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import psycopg

from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.tipos import RelatorioCamada
from terrametrica.ingestao.validacao_geometria import corrigir_geometria, para_multipolygon

CRS_CANONICO = "EPSG:4674"
LINK_OFICIAL_SICAR = "https://consultapublica.car.gov.br/publico/estados/downloads"

STATUS_BRUTO_ATIVO = "AT"

_INSERIR_RESTRICAO = """
    INSERT INTO restricao (id, tipo, nome, categoria, geom, versao_base_id)
    VALUES (%(id)s, %(tipo)s, %(nome)s, %(categoria)s, ST_GeomFromText(%(wkt)s, 4674), %(versao)s)
"""

_INSERIR_PROVENIENCIA = """
    INSERT INTO proveniencia (camada, versao_base_id, fonte, data_extracao, link_oficial)
    VALUES (%(camada)s, %(versao)s, %(fonte)s, %(data_extracao)s, %(link)s)
"""


def _data_extracao_de(caminho: Path) -> date:
    """Mesma heurística de `sigef.py`: mtime do arquivo exportado aproxima a data real do
    export do SICAR melhor do que a data em que a ingestão rodou."""
    return datetime.fromtimestamp(caminho.stat().st_mtime).date()


def _ingerir_camada_restricao_car(
    caminho: Path,
    tipo: str,
    camada: Camada,
    versao: VersaoBase,
    conexao: psycopg.Connection,
    *,
    data_extracao: date | None = None,
) -> RelatorioCamada:
    feicoes = gpd.read_file(caminho, engine="pyogrio")
    if feicoes.crs is None:
        raise ValueError(f"shapefile de restrição CAR sem CRS definido: {caminho}")
    feicoes = feicoes.to_crs(CRS_CANONICO)
    feicoes = feicoes[feicoes["ind_status"].str.strip().str.upper() == STATUS_BRUTO_ATIVO]

    total_corrigidas = 0
    with conexao.cursor() as cursor:
        for indice, (_, linha) in enumerate(feicoes.iterrows()):
            geom_corrigida, foi_corrigida = corrigir_geometria(linha.geometry)
            geom_final = para_multipolygon(geom_corrigida)
            if foi_corrigida:
                total_corrigidas += 1

            cursor.execute(
                _INSERIR_RESTRICAO,
                {
                    "id": f"{tipo}-{linha['cod_imovel']}-{indice}",
                    "tipo": tipo,
                    "nome": str(linha["nom_tema"]),
                    "categoria": str(linha["cod_tema"]),
                    "wkt": geom_final.wkt,
                    "versao": versao.id,
                },
            )

        cursor.execute(
            _INSERIR_PROVENIENCIA,
            {
                "camada": camada.value,
                "versao": versao.id,
                "fonte": "CAR/SICAR",
                "data_extracao": data_extracao or _data_extracao_de(caminho),
                "link": LINK_OFICIAL_SICAR,
            },
        )

    return RelatorioCamada(
        camada=camada.value,
        versao_base_id=versao.id,
        feicoes_gravadas=len(feicoes),
        feicoes_corrigidas=total_corrigidas,
    )


def ingerir_app_car(
    caminho: Path,
    versao: VersaoBase,
    conexao: psycopg.Connection,
    *,
    data_extracao: date | None = None,
) -> RelatorioCamada:
    """Lê o shapefile de APP do CAR (camada "Área de Preservação Permanente"), filtra
    `ind_status='AT'` e grava cada feição em `restricao` com `tipo='app'`."""
    return _ingerir_camada_restricao_car(
        caminho, "app", Camada.APP, versao, conexao, data_extracao=data_extracao
    )


def ingerir_reserva_legal_car(
    caminho: Path,
    versao: VersaoBase,
    conexao: psycopg.Connection,
    *,
    data_extracao: date | None = None,
) -> RelatorioCamada:
    """Lê o shapefile de Reserva Legal do CAR, filtra `ind_status='AT'` e grava cada feição
    em `restricao` com `tipo='reserva_legal'`."""
    return _ingerir_camada_restricao_car(
        caminho, "reserva_legal", Camada.RESERVA_LEGAL, versao, conexao, data_extracao=data_extracao
    )
