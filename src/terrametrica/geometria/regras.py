"""Regras numéricas que definem o produto sobre áreas já calculadas.

Funções puras: operam sobre áreas vindas do read-model (PostGIS as calcula na
ingestão), nunca sobre geometria bruta. Os limiares vêm do protótipo
(`prototipos/mapa-dossie/index.html`) e são o contrato de negócio:

- toque marginal: intersecção < 1% da área do lote (DOS-08);
- divergência entre fontes: diferença > 5% relativa ao SIGEF (AD-003), reportada
  com sinal — o produto nunca reconcilia SIGEF e CAR num polígono único.
"""

from dataclasses import dataclass
from enum import StrEnum

from terrametrica.dominio.modelos import AreaHa, AreaM2, ErroValidacao

LIMIAR_MARGINAL_PCT = 1.0
LIMIAR_DIVERGENCIA_PCT = 5.0


class ClasseIntersecao(StrEnum):
    """Classe de uma intersecção lote × restrição."""

    PLENA = "plena"
    MARGINAL = "marginal"


@dataclass(frozen=True, slots=True)
class ClassificacaoIntersecao:
    """Resultado da classificação: percentual do lote e classe (DOS-08)."""

    pct_do_lote: float
    classe: ClasseIntersecao

    @property
    def marginal(self) -> bool:
        return self.classe is ClasseIntersecao.MARGINAL


@dataclass(frozen=True, slots=True)
class Divergencia:
    """Comparação SIGEF × CAR. `diferenca_ha` é sinalizada (CAR − SIGEF).

    Não há campo de área reconciliada por construção: o produto expõe a diferença,
    nunca funde as duas geometrias (AD-003).
    """

    diferenca_ha: float
    pct: float
    alerta: bool


def classificar_intersecao(
    area_lote: AreaM2, area_intersecao: AreaM2
) -> ClassificacaoIntersecao:
    """Classifica a intersecção como marginal (< 1% do lote) ou plena (DOS-08)."""
    if area_lote.valor == 0.0:
        raise ErroValidacao("área do lote não pode ser zero para classificar intersecção")
    pct = area_intersecao.valor / area_lote.valor * 100.0
    classe = (
        ClasseIntersecao.MARGINAL if pct < LIMIAR_MARGINAL_PCT else ClasseIntersecao.PLENA
    )
    return ClassificacaoIntersecao(pct_do_lote=pct, classe=classe)


def avaliar_divergencia(area_sigef: AreaHa, area_car: AreaHa) -> Divergencia:
    """Mede a divergência entre o limite certificado (SIGEF) e a declaração (CAR).

    Percentual relativo ao SIGEF (limite autoritativo). Alerta acima de 5%. A
    diferença mantém o sinal (CAR − SIGEF) para não esconder a direção do desvio.
    """
    if area_sigef.valor == 0.0:
        raise ErroValidacao("área SIGEF não pode ser zero para avaliar divergência")
    diferenca = area_car.valor - area_sigef.valor
    pct = abs(diferenca) / area_sigef.valor * 100.0
    return Divergencia(diferenca_ha=diferenca, pct=pct, alerta=pct > LIMIAR_DIVERGENCIA_PCT)
