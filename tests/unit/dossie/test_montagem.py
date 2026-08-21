"""Testes da árvore de decisão da montagem do dossiê (T5).

Um teste por ramo, derivado das ACs: DOS-02/05 (fora do RJ), DOS-04 (sem lote),
DOS-06 (sobreposição), DOS-01/07/08 (dossiê + intersecções), DOS-10 (proveniência),
DOS-11 (sem cobertura), DOS-12 (indisponível), DOS-13 (desatualizada).

As camadas esperadas por natureza de lote são fixadas aqui (não importadas da
implementação) para que uma mutação na regra seja detectada pelo teste.
"""

from datetime import date, timedelta

from terrametrica.dominio.modelos import (
    AreaHa,
    AreaM2,
    Camada,
    CoberturaCamada,
    Coordenada,
    Dossie,
    ForaDoRJ,
    IntersecaoBruta,
    LoteRural,
    LoteUrbano,
    Proveniencia,
    SemLote,
    SituacaoCertificacao,
    Sobreposicao,
    TipoRestricao,
    VersaoBase,
)
from terrametrica.dossie.montagem import montar_dossie
from tests.fakes.repositorio_fake import FakeLimiteEstado, FakeRepositorioLotes

HOJE = date(2026, 8, 20)
FRESCO = date(2026, 8, 1)  # 19 dias — dentro dos 90
VERSAO = VersaoBase(id="2026-08", criada_em=date(2026, 8, 1))
COORD = Coordenada(lat=-22.9, lon=-43.1)

RESTR_RURAIS = (
    Camada.APP,
    Camada.RESERVA_LEGAL,
    Camada.UNIDADE_CONSERVACAO,
    Camada.INUNDACAO,
    Camada.DESLIZAMENTO,
    Camada.CORPO_DAGUA,
)
RESTR_URBANAS = (
    Camada.UNIDADE_CONSERVACAO,
    Camada.INUNDACAO,
    Camada.DESLIZAMENTO,
    Camada.CORPO_DAGUA,
)

RURAL = LoteRural(
    lote_id="RJ-1",
    municipios=("Cachoeiras de Macacu",),
    codigo_sigef="SIGEF-1",
    situacao=SituacaoCertificacao.CERTIFICADO,
    area=AreaHa(100.0),  # 1_000_000 m²
    perimetro_m=4000.0,
    denominacao="Fazenda X",
)
URBANO = LoteUrbano(
    lote_id="U-1",
    municipio="Niterói",
    inscricao_cadastral="12.34.56",
    area=AreaM2(360.0),
    perimetro_m=80.0,
    logradouro="Rua Icaraí",
    bairro="Icaraí",
)


def _prov(camada: Camada, data: date = FRESCO) -> Proveniencia:
    return Proveniencia(
        fonte=f"fonte-{camada.value}",
        data_extracao=data,
        link_oficial=f"https://exemplo/{camada.value}",
    )


def _repo_rural_completo() -> FakeRepositorioLotes:
    """Rural com todas as camadas cobertas e frescas."""
    camadas = (Camada.LOTE_RURAL, *RESTR_RURAIS)
    return FakeRepositorioLotes(
        lote=RURAL,
        municipio="Cachoeiras de Macacu",
        coberturas=[CoberturaCamada(c, tem_dado=True, data_extracao=FRESCO) for c in RESTR_RURAIS],
        proveniencias={c: _prov(c) for c in camadas},
    )


def _montar(repo: FakeRepositorioLotes, limite: FakeLimiteEstado | None = None) -> object:
    return montar_dossie(COORD, VERSAO, repo, limite or FakeLimiteEstado(dentro=True), hoje=HOJE)


class TestRamosSemDossie:
    def test_fora_do_rj_recusa_com_mensagem_do_spec(self) -> None:
        resultado = _montar(FakeRepositorioLotes(), FakeLimiteEstado(dentro=False))
        assert isinstance(resultado, ForaDoRJ)
        assert resultado.mensagem == "fora da área de cobertura: apenas RJ"

    def test_sem_lote_devolve_municipio_e_cobertura_declarada(self) -> None:
        coberturas = [
            CoberturaCamada(Camada.UNIDADE_CONSERVACAO, tem_dado=False),
            CoberturaCamada(Camada.INUNDACAO, tem_dado=True, data_extracao=FRESCO),
        ]
        repo = FakeRepositorioLotes(lote=None, municipio="Maricá", coberturas=coberturas)
        resultado = _montar(repo)
        assert isinstance(resultado, SemLote)
        assert resultado.municipio == "Maricá"
        assert resultado.cobertura == tuple(coberturas)

    def test_sobreposicao_devolve_candidatos_para_escolha(self) -> None:
        sobre = Sobreposicao(candidatos=(RURAL, URBANO))
        resultado = _montar(FakeRepositorioLotes(lote=sobre))
        assert isinstance(resultado, Sobreposicao)
        assert resultado.candidatos == (RURAL, URBANO)


class TestDossieRuralUrbano:
    def test_rural_monta_dossie_com_identidade_e_proveniencia(self) -> None:
        resultado = _montar(_repo_rural_completo())
        assert isinstance(resultado, Dossie)
        assert resultado.lote is RURAL
        assert resultado.proveniencia[Camada.LOTE_RURAL].fonte == "fonte-lote_rural"
        assert resultado.camadas_ausentes == ()
        assert resultado.camadas_sem_cobertura == ()
        assert resultado.camadas_desatualizadas == ()

    def test_urbano_nao_espera_camadas_do_car(self) -> None:
        camadas = (Camada.LOTE_URBANO, *RESTR_URBANAS)
        repo = FakeRepositorioLotes(
            lote=URBANO,
            municipio="Niterói",
            coberturas=[
                CoberturaCamada(c, tem_dado=True, data_extracao=FRESCO) for c in RESTR_URBANAS
            ],
            proveniencias={c: _prov(c) for c in camadas},
        )
        resultado = _montar(repo)
        assert isinstance(resultado, Dossie)
        assert resultado.lote is URBANO
        # APP e Reserva Legal são do CAR — não se aplicam a urbano, nem faltam
        assert Camada.APP not in resultado.camadas_sem_cobertura
        assert Camada.APP not in resultado.proveniencia
        assert resultado.camadas_sem_cobertura == ()


class TestIntersecoes:
    def test_intersecao_plena_preserva_pct_e_nao_marca_marginal(self) -> None:
        repo = _repo_rural_completo()
        # 500_000 m² de 1_000_000 m² (100 ha) = 50%
        repo.intersecoes = [
            IntersecaoBruta(
                tipo=TipoRestricao.UNIDADE_CONSERVACAO,
                nome="PARNA da Serra",
                area_intersecao=AreaM2(500_000.0),
                categoria="Proteção Integral",
            )
        ]
        resultado = _montar(repo)
        assert isinstance(resultado, Dossie)
        (item,) = resultado.itens_restricao
        assert item.tipo is TipoRestricao.UNIDADE_CONSERVACAO
        assert item.pct_do_lote == 50.0
        assert item.marginal is False
        assert item.categoria == "Proteção Integral"

    def test_intersecao_abaixo_de_1pct_marcada_marginal(self) -> None:
        repo = _repo_rural_completo()
        # 5_000 m² de 1_000_000 m² = 0.5%
        repo.intersecoes = [
            IntersecaoBruta(
                tipo=TipoRestricao.APP,
                nome="APP de curso d'água",
                area_intersecao=AreaM2(5_000.0),
            )
        ]
        resultado = _montar(repo)
        assert isinstance(resultado, Dossie)
        (item,) = resultado.itens_restricao
        assert item.pct_do_lote == 0.5
        assert item.marginal is True


class TestProvenienciaECobertura:
    def test_cada_camada_do_dossie_tem_fonte_e_data(self) -> None:
        resultado = _montar(_repo_rural_completo())
        assert isinstance(resultado, Dossie)
        assert Camada.LOTE_RURAL in resultado.proveniencia
        assert all(
            p.fonte and isinstance(p.data_extracao, date)
            for p in resultado.proveniencia.values()
        )

    def test_camada_sem_cobertura_no_municipio_declara_ausencia(self) -> None:
        repo = _repo_rural_completo()
        # UC sem dado no município
        repo.coberturas = [
            CoberturaCamada(
                c,
                tem_dado=(c is not Camada.UNIDADE_CONSERVACAO),
                data_extracao=FRESCO,
            )
            for c in RESTR_RURAIS
        ]
        resultado = _montar(repo)
        assert isinstance(resultado, Dossie)
        assert Camada.UNIDADE_CONSERVACAO in resultado.camadas_sem_cobertura
        assert Camada.UNIDADE_CONSERVACAO not in resultado.proveniencia
        assert Camada.UNIDADE_CONSERVACAO not in resultado.camadas_ausentes

    def test_camada_coberta_sem_carimbo_fica_indisponivel(self) -> None:
        repo = _repo_rural_completo()
        # coberta, mas sem stamp de proveniência nesta versão → DOS-12
        repo.proveniencias[Camada.DESLIZAMENTO] = None
        resultado = _montar(repo)
        assert isinstance(resultado, Dossie)
        assert Camada.DESLIZAMENTO in resultado.camadas_ausentes
        assert Camada.DESLIZAMENTO not in resultado.proveniencia
        assert Camada.DESLIZAMENTO not in resultado.camadas_sem_cobertura

    def test_camada_extraida_ha_mais_de_90_dias_e_desatualizada(self) -> None:
        repo = _repo_rural_completo()
        repo.proveniencias[Camada.INUNDACAO] = _prov(
            Camada.INUNDACAO, HOJE - timedelta(days=91)
        )
        resultado = _montar(repo)
        assert isinstance(resultado, Dossie)
        assert Camada.INUNDACAO in resultado.camadas_desatualizadas
        assert Camada.CORPO_DAGUA not in resultado.camadas_desatualizadas

    def test_extracao_de_exatamente_90_dias_nao_e_desatualizada(self) -> None:
        repo = _repo_rural_completo()
        repo.proveniencias[Camada.INUNDACAO] = _prov(
            Camada.INUNDACAO, HOJE - timedelta(days=90)
        )
        resultado = _montar(repo)
        assert isinstance(resultado, Dossie)
        assert Camada.INUNDACAO not in resultado.camadas_desatualizadas
