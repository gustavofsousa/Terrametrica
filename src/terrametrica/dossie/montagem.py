"""Montagem do dossiê: da coordenada clicada ao read-model montado.

Orquestra os ports e as regras de geometria numa árvore de decisão explícita.
Sem I/O: recebe `repo` e `limite` injetados (Protocols de `portas`).

Árvore (guard clauses, um caminho óbvio):
1. fora do RJ            → ForaDoRJ            (DOS-05)
2. sem polígono no ponto → SemLote            (DOS-04)
3. sobreposição          → Sobreposicao       (DOS-06)
4. lote resolvido        → Dossie             (DOS-01/07/08/10/11/12/13)
"""

from datetime import date

from terrametrica.dominio.modelos import (
    AreaM2,
    Camada,
    Coordenada,
    Dossie,
    ForaDoRJ,
    IntersecaoBruta,
    ItemRestricao,
    LoteHit,
    LoteRural,
    Proveniencia,
    SemLote,
    Sobreposicao,
    VersaoBase,
)
from terrametrica.dossie.portas import LimiteEstado, RepositorioLotes
from terrametrica.geometria.regras import classificar_intersecao

LIMIAR_DIAS_DESATUALIZADA = 90

# Camadas de restrição esperadas por natureza de lote. APP e Reserva Legal são
# do CAR (só rural); as demais aplicam a rural e urbano (docs/produto/dossie.md).
_RESTRICOES_COMUNS = (
    Camada.UNIDADE_CONSERVACAO,
    Camada.INUNDACAO,
    Camada.DESLIZAMENTO,
    Camada.CORPO_DAGUA,
)
_RESTRICOES_RURAIS = (Camada.APP, Camada.RESERVA_LEGAL, *_RESTRICOES_COMUNS)


def montar_dossie(
    coord: Coordenada,
    versao: VersaoBase,
    repo: RepositorioLotes,
    limite: LimiteEstado,
    *,
    hoje: date | None = None,
) -> Dossie | SemLote | Sobreposicao | ForaDoRJ:
    """Monta o dossiê do ponto clicado ou o estado que impede a montagem."""
    if not limite.contem(coord):
        return ForaDoRJ()

    achado = repo.lote_em(coord, versao)

    if achado is None:
        municipio = repo.municipio_em(coord, versao)
        return SemLote(municipio=municipio, cobertura=tuple(repo.cobertura_de(municipio)))

    if isinstance(achado, Sobreposicao):
        return achado

    return _montar_do_lote(achado, versao, repo, hoje or date.today())


def _montar_do_lote(
    lote: LoteHit, versao: VersaoBase, repo: RepositorioLotes, hoje: date
) -> Dossie:
    area_lote_m2 = _area_do_lote_m2(lote)
    itens = tuple(
        _avaliar_intersecao(bruta, area_lote_m2)
        for bruta in repo.intersecoes_de(lote, versao)
    )

    cobertura = {c.camada: c for c in repo.cobertura_de(_municipio_do_lote(lote))}

    proveniencia: dict[Camada, Proveniencia] = {}
    ausentes: list[Camada] = []
    sem_cobertura: list[Camada] = []
    desatualizadas: list[Camada] = []

    # A camada de identidade/geometria do próprio lote também carrega proveniência.
    camada_lote = _camada_do_lote(lote)
    for camada in (camada_lote, *_restricoes_esperadas(lote)):
        registro = cobertura.get(camada)
        if camada is not camada_lote and (registro is None or not registro.tem_dado):
            sem_cobertura.append(camada)  # DOS-11
            continue

        carimbo = repo.proveniencia_de(camada, versao)
        if carimbo is None:
            ausentes.append(camada)  # DOS-12
            continue

        proveniencia[camada] = carimbo  # DOS-10
        if (hoje - carimbo.data_extracao).days > LIMIAR_DIAS_DESATUALIZADA:
            desatualizadas.append(camada)  # DOS-13

    return Dossie(
        lote=lote,
        itens_restricao=itens,
        proveniencia=proveniencia,
        camadas_ausentes=tuple(ausentes),
        camadas_sem_cobertura=tuple(sem_cobertura),
        camadas_desatualizadas=tuple(desatualizadas),
    )


def _avaliar_intersecao(bruta: IntersecaoBruta, area_lote_m2: AreaM2) -> ItemRestricao:
    classificacao = classificar_intersecao(area_lote_m2, bruta.area_intersecao)
    return ItemRestricao(
        tipo=bruta.tipo,
        nome=bruta.nome,
        area_intersecao=bruta.area_intersecao,
        pct_do_lote=classificacao.pct_do_lote,
        marginal=classificacao.marginal,
        categoria=bruta.categoria,
        grau_suscetibilidade=bruta.grau_suscetibilidade,
    )


def _camada_do_lote(lote: LoteHit) -> Camada:
    return Camada.LOTE_RURAL if isinstance(lote, LoteRural) else Camada.LOTE_URBANO


def _restricoes_esperadas(lote: LoteHit) -> tuple[Camada, ...]:
    return _RESTRICOES_RURAIS if isinstance(lote, LoteRural) else _RESTRICOES_COMUNS


def _area_do_lote_m2(lote: LoteHit) -> AreaM2:
    return lote.area.em_metros_quadrados() if isinstance(lote, LoteRural) else lote.area


def _municipio_do_lote(lote: LoteHit) -> str:
    return lote.municipios[0] if isinstance(lote, LoteRural) else lote.municipio
