"""Testes das projeções de DTO da API (T29). Puro, sem I/O.

Deriva das ACs de saída: um Dossie serializa lote + restrições (área/pct/marginal, DOS-07/08) +
proveniência por camada (DOS-10) + os três estados de camada distintos (ausente/sem-cobertura/
desatualizada, DOS-11/12/13); a sobreposição lista candidatos (DOS-06); o SemLote leva município +
cobertura (DOS-04). Os valores esperados são fixados aqui, não lidos da implementação.
"""

from datetime import date

from terrametrica.api.dto import (
    cobertura_para_dict,
    dossie_para_dict,
    sem_lote_para_dict,
    sobreposicao_para_dict,
)
from terrametrica.dominio.modelos import (
    AreaHa,
    AreaM2,
    Camada,
    CoberturaCamada,
    Dossie,
    ItemRestricao,
    LoteRural,
    Proveniencia,
    SemLote,
    SituacaoCertificacao,
    Sobreposicao,
    TipoRestricao,
)

RURAL = LoteRural(
    lote_id="RJ-1",
    municipios=("3300100",),
    codigo_sigef="SIGEF-1",
    situacao=SituacaoCertificacao.CERTIFICADO,
    area=AreaHa(100.0),
    perimetro_m=4000.0,
    denominacao="Fazenda Teste",
)

PROV_SIGEF = Proveniencia(
    fonte="SIGEF", data_extracao=date(2026, 9, 1), link_oficial="https://sigef.example/1"
)
PROV_APP = Proveniencia(
    fonte="CAR", data_extracao=date(2026, 6, 1), link_oficial="https://car.example/1"
)


class TestDossieParaDict:
    def _dossie(self) -> Dossie:
        item = ItemRestricao(
            tipo=TipoRestricao.APP,
            nome="APP de rio",
            area_intersecao=AreaM2(50_000.0),
            pct_do_lote=5.0,
            marginal=False,
            categoria="APP_RIO",
        )
        return Dossie(
            lote=RURAL,
            itens_restricao=(item,),
            proveniencia={Camada.LOTE_RURAL: PROV_SIGEF, Camada.APP: PROV_APP},
            camadas_ausentes=(Camada.INUNDACAO,),
            camadas_sem_cobertura=(Camada.CORPO_DAGUA,),
            camadas_desatualizadas=(Camada.APP,),
        )

    def test_serializa_ficha_do_lote_rural(self) -> None:
        d = dossie_para_dict(self._dossie())

        assert d["tipo"] == "dossie"
        assert d["lote"] == {
            "natureza": "rural",
            "lote_id": "RJ-1",
            "codigo_sigef": "SIGEF-1",
            "situacao": "certificado",
            "municipios": ["3300100"],
            "area_ha": 100.0,
            "perimetro_m": 4000.0,
            "denominacao": "Fazenda Teste",
        }

    def test_serializa_restricao_com_area_pct_e_marginal(self) -> None:
        d = dossie_para_dict(self._dossie())

        (restricao,) = d["restricoes"]  # type: ignore[misc]
        assert restricao["tipo"] == "app"
        assert restricao["nome"] == "APP de rio"
        assert restricao["area_intersecao_m2"] == 50_000.0
        assert restricao["pct_do_lote"] == 5.0
        assert restricao["marginal"] is False
        assert restricao["categoria"] == "APP_RIO"

    def test_carimba_proveniencia_por_camada(self) -> None:
        d = dossie_para_dict(self._dossie())

        prov = d["proveniencia"]
        assert prov["lote_rural"] == {  # type: ignore[index]
            "fonte": "SIGEF",
            "data_extracao": "2026-09-01",
            "link_oficial": "https://sigef.example/1",
        }
        assert prov["app"]["fonte"] == "CAR"  # type: ignore[index]

    def test_distingue_os_tres_estados_de_camada(self) -> None:
        d = dossie_para_dict(self._dossie())

        assert d["camadas_ausentes"] == ["inundacao"]
        assert d["camadas_sem_cobertura"] == ["corpo_dagua"]
        assert d["camadas_desatualizadas"] == ["app"]


class TestSobreposicaoParaDict:
    def test_lista_todos_os_candidatos(self) -> None:
        outro = LoteRural(
            lote_id="RJ-2",
            municipios=("3300100",),
            codigo_sigef="SIGEF-2",
            situacao=SituacaoCertificacao.CERTIFICADO,
            area=AreaHa(10.0),
            perimetro_m=1000.0,
        )
        d = sobreposicao_para_dict(Sobreposicao(candidatos=(RURAL, outro)))

        assert d["tipo"] == "sobreposicao"
        ids = [c["lote_id"] for c in d["candidatos"]]  # type: ignore[union-attr]
        assert ids == ["RJ-1", "RJ-2"]


class TestSemLoteParaDict:
    def test_leva_municipio_e_cobertura(self) -> None:
        cobertura = (
            CoberturaCamada(camada=Camada.APP, tem_dado=True, data_extracao=date(2026, 6, 1)),
        )
        d = sem_lote_para_dict(SemLote(municipio="3300100", cobertura=cobertura))

        assert d["tipo"] == "sem_lote"
        assert d["municipio"] == "3300100"
        (cob,) = d["cobertura"]  # type: ignore[misc]
        assert cob == {"camada": "app", "tem_dado": True, "data_extracao": "2026-06-01"}


class TestCoberturaParaDict:
    def test_data_nula_vira_none(self) -> None:
        cobertura = [CoberturaCamada(camada=Camada.INUNDACAO, tem_dado=False, data_extracao=None)]
        d = cobertura_para_dict(cobertura)

        (cob,) = d["cobertura"]  # type: ignore[misc]
        assert cob["tem_dado"] is False
        assert cob["data_extracao"] is None
