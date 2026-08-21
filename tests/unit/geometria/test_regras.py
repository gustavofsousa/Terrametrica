"""Testes das regras numéricas de geometria (T3).

Derivados de: DOS-08 (toque marginal < 1%) e da regra de divergência SIGEF×CAR
(> 5%, base SIGEF por AD-003, nunca reconcilia). Limiares conferidos contra o
protótipo `prototipos/mapa-dossie/index.html:1045-1107`.
"""

import pytest

from terrametrica.dominio.modelos import AreaHa, AreaM2, ErroValidacao
from terrametrica.geometria.regras import (
    ClasseIntersecao,
    avaliar_divergencia,
    classificar_intersecao,
)


class TestClassificarIntersecao:
    def test_exatamente_1_pct_e_plena(self) -> None:
        # 100 / 10_000 = 1.00% — no limiar, NÃO é marginal
        c = classificar_intersecao(AreaM2(10_000.0), AreaM2(100.0))
        assert c.classe is ClasseIntersecao.PLENA
        assert c.marginal is False
        assert c.pct_do_lote == pytest.approx(1.0)

    def test_abaixo_de_1_pct_e_marginal(self) -> None:
        # 99 / 10_000 = 0.99%
        c = classificar_intersecao(AreaM2(10_000.0), AreaM2(99.0))
        assert c.classe is ClasseIntersecao.MARGINAL
        assert c.marginal is True
        assert c.pct_do_lote == pytest.approx(0.99)

    def test_acima_de_1_pct_e_plena(self) -> None:
        # 101 / 10_000 = 1.01%
        c = classificar_intersecao(AreaM2(10_000.0), AreaM2(101.0))
        assert c.classe is ClasseIntersecao.PLENA
        assert c.pct_do_lote == pytest.approx(1.01)

    def test_pct_calculado_corretamente(self) -> None:
        c = classificar_intersecao(AreaM2(10_000.0), AreaM2(2_500.0))
        assert c.pct_do_lote == pytest.approx(25.0)
        assert c.marginal is False

    def test_intersecao_zero_e_marginal(self) -> None:
        c = classificar_intersecao(AreaM2(10_000.0), AreaM2(0.0))
        assert c.pct_do_lote == pytest.approx(0.0)
        assert c.marginal is True

    def test_lote_com_area_zero_e_rejeitado(self) -> None:
        with pytest.raises(ErroValidacao, match="zero"):
            classificar_intersecao(AreaM2(0.0), AreaM2(10.0))


class TestAvaliarDivergencia:
    def test_exatamente_5_pct_nao_alerta(self) -> None:
        # SIGEF 100 ha, CAR 105 ha → 5.00%, no limiar, sem alerta
        d = avaliar_divergencia(AreaHa(100.0), AreaHa(105.0))
        assert d.pct == pytest.approx(5.0)
        assert d.alerta is False

    def test_abaixo_de_5_pct_nao_alerta(self) -> None:
        d = avaliar_divergencia(AreaHa(100.0), AreaHa(104.9))
        assert d.pct == pytest.approx(4.9)
        assert d.alerta is False

    def test_acima_de_5_pct_alerta(self) -> None:
        d = avaliar_divergencia(AreaHa(100.0), AreaHa(105.1))
        assert d.pct == pytest.approx(5.1)
        assert d.alerta is True

    def test_diferenca_e_sinalizada_car_menor_que_sigef(self) -> None:
        # CAR menor que SIGEF → diferença negativa; direção preservada (não reconcilia)
        d = avaliar_divergencia(AreaHa(100.0), AreaHa(90.0))
        assert d.diferenca_ha == pytest.approx(-10.0)
        assert d.pct == pytest.approx(10.0)
        assert d.alerta is True

    def test_diferenca_positiva_quando_car_maior(self) -> None:
        d = avaliar_divergencia(AreaHa(100.0), AreaHa(112.0))
        assert d.diferenca_ha == pytest.approx(12.0)

    def test_sigef_com_area_zero_e_rejeitado(self) -> None:
        with pytest.raises(ErroValidacao, match="zero"):
            avaliar_divergencia(AreaHa(0.0), AreaHa(10.0))
