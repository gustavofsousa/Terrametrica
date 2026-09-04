"""Testes dos value objects e tipos-resultado do domínio (T2).

Derivados das ACs: DOS-02 (coordenada valida lat/lon), DOS-05 (fora do RJ é a
fronteira de negócio), regra "validate at the boundary" e "make illegal states
unrepresentable" do AGENTS.md.
"""

from dataclasses import fields
from datetime import date, datetime

import pytest

from terrametrica.dominio.modelos import (
    AreaHa,
    AreaM2,
    Camada,
    CampoComProveniencia,
    Conta,
    Coordenada,
    EntradaAuditoria,
    ErroValidacao,
    ForaDoRJ,
    Indisponivel,
    LoteRural,
    Negado,
    PapelConta,
    Permitido,
    Proveniencia,
    SemLote,
    SituacaoCertificacao,
    Sobreposicao,
    TipoEventoAuditoria,
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


class TestGateJuridico:
    """GATE-01, 02, 04, 05, 06 — value objects do gate jurídico (P2)."""

    def test_conta_guarda_id_e_papel(self) -> None:
        conta = Conta(id="c1", papel=PapelConta.HABILITADO_JURIDICAMENTE)
        assert conta.id == "c1"
        assert conta.papel is PapelConta.HABILITADO_JURIDICAMENTE

    def test_conta_nao_representa_dado_pessoal_de_proprietario(self) -> None:
        # GATE-06: garantia estrutural — nenhum campo pode carregar nome/CPF/CNPJ
        nomes_de_campo = {f.name for f in fields(Conta)}
        assert nomes_de_campo == {"id", "papel"}
        assert not nomes_de_campo & {"nome", "cpf", "cnpj"}

    def test_tipo_evento_auditoria_e_fechado(self) -> None:
        assert {t.value for t in TipoEventoAuditoria} == {"consulta_registral", "promocao"}

    def test_entrada_auditoria_de_consulta_guarda_finalidade_e_lote(self) -> None:
        # GATE-05: identidade, finalidade declarada, lote e instante
        instante = datetime(2026, 9, 3, 12, 0)
        entrada = EntradaAuditoria(
            id="log1",
            ts=instante,
            conta_id="c1",
            tipo=TipoEventoAuditoria.CONSULTA_REGISTRAL,
            finalidade="due diligence de compra",
            lote_id="RJ-123",
        )
        assert entrada.conta_id == "c1"
        assert entrada.finalidade == "due diligence de compra"
        assert entrada.lote_id == "RJ-123"
        assert entrada.ts == instante
        assert entrada.promovido_por is None
        assert entrada.credencial_verificada is None

    def test_entrada_auditoria_de_promocao_guarda_quem_quando_credencial(self) -> None:
        # GATE-04: quem promoveu, quando e sob qual credencial verificada
        instante = datetime(2026, 9, 3, 13, 30)
        entrada = EntradaAuditoria(
            id="log2",
            ts=instante,
            conta_id="c1",
            tipo=TipoEventoAuditoria.PROMOCAO,
            promovido_por="operador-01",
            credencial_verificada="OAB/RJ 123456",
        )
        assert entrada.promovido_por == "operador-01"
        assert entrada.credencial_verificada == "OAB/RJ 123456"
        assert entrada.ts == instante

    def test_negado_traz_mensagem_de_recusa(self) -> None:
        assert Negado().mensagem == "acesso negado: papel da conta não habilita dado registral"

    def test_permitido_e_negado_sao_tipos_distintos(self) -> None:
        assert isinstance(Permitido(), Permitido)
        assert not isinstance(Permitido(), Negado)

    def test_indisponivel_traz_mensagem_padrao_da_versao(self) -> None:
        # GATE-02: "indisponível nesta versão" para todos os papéis
        assert Indisponivel().mensagem == "indisponível nesta versão"
