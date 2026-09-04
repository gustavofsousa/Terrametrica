"""Prova fim-a-fim da Fatia 2 (T14) e Fatia 3 (T20): pipeline completo → dossiê real sobre PostGIS.

Roda `ingerir_limite_rj` (rede real via geobr, AD-004 — não é mockado, mesma decisão de
`test_limite_rj.py`) → `ingerir_sigef` → `ingerir_app_car`/`ingerir_reserva_legal_car` →
`materializar_intersecoes` → `publicar_versao` (fixtures sintéticas), e então injeta os adapters
reais (`RepositorioLotesPostGIS`, `LimiteEstadoPostGIS`) em `montar_dossie` — sem tocar
`montagem.py`. A prova é que a árvore de decisão inteira (DOS-01/04/05/06/07/08/10/11/12/13)
funciona sobre dado publicado de verdade, não sobre fakes em memória (Fatia 1) nem sobre SQL
semeado à mão (T9/T13/T18).

A chamada de rede ao geobr roda uma única vez por módulo (fixture `versao_publicada`,
`scope="module"`) — repeti-la por teste seria custo de rede sem ganho de cobertura adicional.
Mesmo padrão de container efêmero + guarda de Docker de `test_limite_rj.py`/`test_sigef.py`/
`test_publicar.py`.
"""

import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from terrametrica.dominio.modelos import (
    Camada,
    Coordenada,
    Dossie,
    ForaDoRJ,
    TipoRestricao,
    VersaoBase,
)
from terrametrica.dossie.montagem import montar_dossie
from terrametrica.ingestao.cobertura import semear_cobertura
from terrametrica.ingestao.intersecoes import materializar_intersecoes
from terrametrica.ingestao.limite_rj import ingerir_limite_rj
from terrametrica.ingestao.publicar import publicar_versao
from terrametrica.ingestao.restricao_car import ingerir_app_car, ingerir_reserva_legal_car
from terrametrica.ingestao.sigef import ingerir_sigef
from terrametrica.persistencia.limite_estado_postgis import LimiteEstadoPostGIS
from terrametrica.persistencia.migrar import aplicar_migracoes
from terrametrica.persistencia.repositorio_lotes_postgis import RepositorioLotesPostGIS

IMAGEM_POSTGIS = "postgis/postgis:16-3.4"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE_SIGEF = FIXTURES / "sigef" / "sigef_rj_amostra.shp"
FIXTURE_APP = FIXTURES / "restricao_car" / "app_amostra.shp"
FIXTURE_RESERVA_LEGAL = FIXTURES / "restricao_car" / "reserva_legal_amostra.shp"

VERSAO_ID = "e2e-fatia3-v1"
DATA_EXTRACAO_SIGEF = date(2026, 8, 20)
DATA_EXTRACAO_CAR = date(2026, 9, 1)

# SIGEF-001 (fixture sintética): Rio de Janeiro, IBGE 3304557, CERTIFICADA — quadrado centrado
# exatamente neste ponto (confirmado via geopandas: centroid (-43.10, -22.90), bounds
# [-43.105, -22.905, -43.095, -22.895]) — não intersecta os demais lotes da fixture.
COORD_DENTRO_DO_LOTE_SIGEF_001 = Coordenada(lat=-22.90, lon=-43.10)

# São Paulo (capital) — claramente fora dos limites do RJ.
COORD_FORA_DO_RJ = Coordenada(lat=-23.5505, lon=-46.6333)

# SIGEF-002 (fixture sintética): centroid (-44.3, -23.0) — nenhuma das fixtures de restrição CAR
# (T16) foi posicionada perto dele, então nenhuma intersecção é materializada para este lote.
COORD_DENTRO_DO_LOTE_SIGEF_002_SEM_RESTRICAO = Coordenada(lat=-23.0, lon=-44.3)


def _garantir_docker_disponivel() -> None:
    try:
        resultado = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10, check=False
        )
    except FileNotFoundError:
        pytest.fail("Docker não encontrado — instale e rode o Docker antes desta suíte.")
    if resultado.returncode != 0:
        pytest.fail(
            "Docker não está disponível (`docker info` falhou) — os testes de integração "
            "exigem um container PostGIS efêmero via testcontainers."
        )


@pytest.fixture(scope="module")
def container() -> Iterator[PostgresContainer]:
    _garantir_docker_disponivel()
    with PostgresContainer(image=IMAGEM_POSTGIS) as postgres:
        with psycopg.connect(postgres.get_connection_url(driver=None)) as conexao_migracao:
            aplicar_migracoes(conexao_migracao)
        yield postgres


@pytest.fixture(scope="module")
def versao_publicada(container: PostgresContainer) -> VersaoBase:
    """Roda o pipeline completo (limite RJ real via geobr + SIGEF fixture + publicação) uma
    única vez por módulo e devolve a `VersaoBase` já publicada. Ordem do contrato de transação
    (ver docstrings de `limite_rj.py`/`sigef.py`/`publicar.py`): cria `versao_base` (draft) →
    persiste essa linha → ingestões (staging, sem commit) → `semear_cobertura` (Fatia 4, AD-009)
    → `publicar_versao` (comita o swap e, transitivamente, o staging, só se a guarda passar).
    """
    versao = VersaoBase(id=VERSAO_ID, criada_em=date(2026, 9, 1))
    conexao = psycopg.connect(container.get_connection_url(driver=None))
    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
                (versao.id, versao.criada_em, "draft"),
            )
        conexao.commit()

        ingerir_limite_rj(versao, conexao)
        ingerir_sigef(FIXTURE_SIGEF, versao, conexao, data_extracao=DATA_EXTRACAO_SIGEF)
        ingerir_app_car(FIXTURE_APP, versao, conexao, data_extracao=DATA_EXTRACAO_CAR)
        ingerir_reserva_legal_car(
            FIXTURE_RESERVA_LEGAL, versao, conexao, data_extracao=DATA_EXTRACAO_CAR
        )
        materializar_intersecoes(versao, conexao)
        semear_cobertura(versao, conexao)
        resultado = publicar_versao(versao, conexao)

        assert resultado.publicada is True, (
            "guarda de publicação reprovou a primeira publicação (deveria sempre passar sem "
            f"versão anterior): {resultado.camadas}"
        )
    finally:
        conexao.close()

    return versao


@pytest.fixture
def conexao(container: PostgresContainer) -> Iterator[psycopg.Connection]:
    conexao = psycopg.connect(container.get_connection_url(driver=None))
    try:
        yield conexao
    finally:
        conexao.rollback()
        conexao.close()


class TestDossieFimAFimSobrePostGISReal:
    def test_coordenada_dentro_do_lote_sigef_monta_dossie_com_proveniencia(
        self, conexao: psycopg.Connection, versao_publicada: VersaoBase
    ) -> None:
        repo = RepositorioLotesPostGIS(conexao)
        limite = LimiteEstadoPostGIS(conexao)

        resultado = montar_dossie(COORD_DENTRO_DO_LOTE_SIGEF_001, versao_publicada, repo, limite)

        assert isinstance(resultado, Dossie)
        assert resultado.lote.codigo_sigef == "SIGEF-001"

        proveniencia_lote = resultado.proveniencia[Camada.LOTE_RURAL]
        assert proveniencia_lote.fonte == "SIGEF"
        assert proveniencia_lote.data_extracao == DATA_EXTRACAO_SIGEF

    def test_restricoes_ingeridas_aparecem_com_cobertura_e_proveniencia_honesta(
        self, conexao: psycopg.Connection, versao_publicada: VersaoBase
    ) -> None:
        # DOS-11 honesto (Fatia 4, TD-002/AD-009): as camadas de restrição realmente ingeridas
        # (APP, Reserva Legal — estaduais via CAR) NÃO podem aparecer como "sem cobertura" no
        # município do lote; devem trazer proveniência. As não ingeridas (UC/inundação/
        # deslizamento/corpo-d'água) seguem honestamente marcadas sem cobertura.
        repo = RepositorioLotesPostGIS(conexao)
        limite = LimiteEstadoPostGIS(conexao)

        resultado = montar_dossie(COORD_DENTRO_DO_LOTE_SIGEF_001, versao_publicada, repo, limite)

        assert isinstance(resultado, Dossie)

        assert Camada.APP not in resultado.camadas_sem_cobertura
        assert Camada.RESERVA_LEGAL not in resultado.camadas_sem_cobertura

        assert resultado.proveniencia[Camada.APP].fonte == "CAR/SICAR"
        assert resultado.proveniencia[Camada.APP].data_extracao == DATA_EXTRACAO_CAR
        assert resultado.proveniencia[Camada.RESERVA_LEGAL].data_extracao == DATA_EXTRACAO_CAR

        # Camadas ainda não ingeridas continuam honestamente sem cobertura, não silenciadas.
        assert Camada.UNIDADE_CONSERVACAO in resultado.camadas_sem_cobertura
        assert Camada.INUNDACAO in resultado.camadas_sem_cobertura

    def test_coordenada_fora_do_rj_devolve_fora_do_rj_sobre_limite_real(
        self, conexao: psycopg.Connection, versao_publicada: VersaoBase
    ) -> None:
        repo = RepositorioLotesPostGIS(conexao)
        limite = LimiteEstadoPostGIS(conexao)

        resultado = montar_dossie(COORD_FORA_DO_RJ, versao_publicada, repo, limite)

        assert isinstance(resultado, ForaDoRJ)

    def test_lote_com_restricao_car_materializada_monta_itens_restricao(
        self, conexao: psycopg.Connection, versao_publicada: VersaoBase
    ) -> None:
        repo = RepositorioLotesPostGIS(conexao)
        limite = LimiteEstadoPostGIS(conexao)

        resultado = montar_dossie(COORD_DENTRO_DO_LOTE_SIGEF_001, versao_publicada, repo, limite)

        assert isinstance(resultado, Dossie)
        assert len(resultado.itens_restricao) >= 2  # APP plena + Reserva Legal plena, no mínimo

        item_app = next(i for i in resultado.itens_restricao if i.tipo is TipoRestricao.APP)
        assert item_app.pct_do_lote > 1.0  # sobreposição plena (~50% do lote), não marginal
        assert item_app.marginal is False

        item_rl = next(
            i for i in resultado.itens_restricao if i.tipo is TipoRestricao.RESERVA_LEGAL
        )
        assert item_rl.pct_do_lote > 1.0
        assert item_rl.marginal is False

    def test_lote_sem_sobreposicao_de_restricao_devolve_itens_restricao_vazio(
        self, conexao: psycopg.Connection, versao_publicada: VersaoBase
    ) -> None:
        repo = RepositorioLotesPostGIS(conexao)
        limite = LimiteEstadoPostGIS(conexao)

        resultado = montar_dossie(
            COORD_DENTRO_DO_LOTE_SIGEF_002_SEM_RESTRICAO, versao_publicada, repo, limite
        )

        assert isinstance(resultado, Dossie)
        assert resultado.itens_restricao == ()
