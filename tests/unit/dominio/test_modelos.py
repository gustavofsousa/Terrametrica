"""Testes dos value objects e tipos-resultado do domínio (T2).

Derivados das ACs: DOS-02 (coordenada valida lat/lon), DOS-05 (fora do RJ é a
fronteira de negócio), regra "validate at the boundary" e "make illegal states
unrepresentable" do AGENTS.md.
"""

from datetime import date

import pytest

from terrametrica.dominio.modelos import (
    AreaHa,
    AreaM2,
    Camada,
    CampoComProveniencia,
    Coordenada,
    ErroValidacao,
    ForaDoRJ,
    LoteRural,
    PapelConta,
    Proveniencia,
    SemLote,
    SituacaoCertificacao,
    Sobreposicao,
    TipoRestricao,
    VersaoBase,
)


class TestCoordenada:
    def test_coordenada_valida_guarda_lat_lon(self) -> None:
        coord = Coordenada(lat=-22.9, lon=-43.1)
        assert (coord.lat, coord.lon) == (-22.9, -43.1)

    @pytest.mark.parametrize("lat", [-90.0, 90.0])
    def test_latitude_no_limite_e_valida(self, lat: float) -> None:
        assert Coordenada(lat=lat, lon=0.0).lat == lat

    @pytest.mark.parametrize("lat", [-90.0001, 90.0001, 120.0])
    def test_latitude_fora_de_faixa_rejeitada(self, lat: float) -> None:
        with pytest.raises(ErroValidacao, match="latitude"):
            Coordenada(lat=lat, lon=0.0)

    @pytest.mark.parametrize("lon", [-180.0001, 180.0001, 200.0])
    def test_longitude_fora_de_faixa_rejeitada(self, lon: float) -> None:
        with pytest.raises(ErroValidacao, match="longitude"):
            Coordenada(lat=0.0, lon=lon)


class TestArea:
    def test_area_m2_negativa_rejeitada(self) -> None:
        with pytest.raises(ErroValidacao, match="área"):
            AreaM2(-1.0)

    def test_area_ha_negativa_rejeitada(self) -> None:
        with pytest.raises(ErroValidacao, match="área"):
            AreaHa(-0.001)

    def test_area_zero_e_valida_no_limite(self) -> None:
        assert AreaM2(0.0).valor == 0.0
        assert AreaHa(0.0).valor == 0.0

    def test_conversao_m2_para_hectare(self) -> None:
        assert AreaM2(10_000.0).em_hectares() == AreaHa(1.0)


class TestEnumsFechados:
    def test_tipo_restricao_mapeia_para_camada_correspondente(self) -> None:
        # cada restrição conhece sua camada versionada — sem string solta
        assert TipoRestricao.APP.camada is Camada.APP
        assert TipoRestricao.RESERVA_LEGAL.camada is Camada.RESERVA_LEGAL
        assert TipoRestricao.UNIDADE_CONSERVACAO.camada is Camada.UNIDADE_CONSERVACAO
        assert TipoRestricao.INUNDACAO.camada is Camada.INUNDACAO
        assert TipoRestricao.DESLIZAMENTO.camada is Camada.DESLIZAMENTO
        assert TipoRestricao.CORPO_DAGUA.camada is Camada.CORPO_DAGUA

    def test_papel_conta_tem_exatamente_os_dois_papeis(self) -> None:
        assert {p.value for p in PapelConta} == {"consulta", "habilitado_juridicamente"}

    def test_situacao_certificacao_e_fechada(self) -> None:
        assert {s.value for s in SituacaoCertificacao} == {"certificado", "em_analise"}


class TestProveniencia:
    def test_campo_com_proveniencia_guarda_valor_e_carimbo(self) -> None:
        prov = Proveniencia(
            fonte="SIGEF / INCRA",
            data_extracao=date(2026, 7, 28),
            link_oficial="https://sigef.incra.gov.br",
        )
        campo = CampoComProveniencia(valor="RJ-123", proveniencia=prov)
        assert campo.valor == "RJ-123"
        assert campo.proveniencia.fonte == "SIGEF / INCRA"
        assert campo.proveniencia.data_extracao == date(2026, 7, 28)

    def test_versao_base_guarda_id_e_data(self) -> None:
        versao = VersaoBase(id="2026-08", criada_em=date(2026, 8, 1))
        assert versao.id == "2026-08"
        assert versao.criada_em == date(2026, 8, 1)


class TestTiposResultado:
    def test_fora_do_rj_traz_mensagem_do_spec(self) -> None:
        # DOS-05: texto literal exigido pelo spec
        assert ForaDoRJ().mensagem == "fora da área de cobertura: apenas RJ"

    def test_sem_lote_traz_mensagem_do_spec(self) -> None:
        # DOS-04: texto literal exigido pelo spec
        assert SemLote(municipio="Niterói", cobertura=()).mensagem == (
            "sem lote mapeado neste ponto"
        )

    def test_sobreposicao_exige_ao_menos_dois_candidatos(self) -> None:
        lote = LoteRural(
            lote_id="RJ-1",
            municipios=("Cachoeiras de Macacu",),
            codigo_sigef="ABC",
            situacao=SituacaoCertificacao.CERTIFICADO,
            area=AreaHa(10.0),
            perimetro_m=1000.0,
        )
        with pytest.raises(ErroValidacao, match="sobreposição"):
            Sobreposicao(candidatos=(lote,))
