"""Serialização dos value objects do domínio para JSON (DTO de saída da API).

Funções puras, sem I/O: recebem um resultado do motor (`Dossie`/`SemLote`/`Sobreposicao`) ou uma
lista de cobertura e devolvem um `dict` serializável direto. Não há Pydantic model de domínio — o
domínio já valida no boundary (`dominio/modelos.py`); a resposta é a projeção desses objetos.

Cada camada com dado no dossiê carrega sua proveniência (fonte + data + link oficial), expondo o
DOS-10 que `montar_dossie` já montou; nenhum número aparece órfão (AD-005). As listas de camadas
ausentes / sem-cobertura / desatualizadas viram arrays de string para o cliente distinguir os três
estados (DOS-11/12/13).
"""

from terrametrica.dominio.modelos import (
    Camada,
    CoberturaCamada,
    CoberturaMunicipio,
    Dossie,
    ItemRestricao,
    LoteHit,
    LoteRural,
    Proveniencia,
    SemLote,
    Sobreposicao,
)


def dossie_para_dict(dossie: Dossie) -> dict[str, object]:
    """Projeta um `Dossie` montado no corpo JSON de `200 /dossie`."""
    return {
        "tipo": "dossie",
        "lote": _lote_para_dict(dossie.lote),
        "restricoes": [_item_restricao_para_dict(item) for item in dossie.itens_restricao],
        "proveniencia": {
            camada.value: _proveniencia_para_dict(carimbo)
            for camada, carimbo in dossie.proveniencia.items()
        },
        "camadas_ausentes": [c.value for c in dossie.camadas_ausentes],
        "camadas_sem_cobertura": [c.value for c in dossie.camadas_sem_cobertura],
        "camadas_desatualizadas": [c.value for c in dossie.camadas_desatualizadas],
        "ressalva": dossie.ressalva,
    }


def sem_lote_para_dict(sem_lote: SemLote) -> dict[str, object]:
    """Projeta o estado `SemLote` (clique sem polígono conhecido, DOS-04)."""
    return {
        "tipo": "sem_lote",
        "mensagem": sem_lote.mensagem,
        "municipio": sem_lote.municipio,
        "cobertura": [_cobertura_para_dict(c) for c in sem_lote.cobertura],
    }


def sobreposicao_para_dict(sobreposicao: Sobreposicao) -> dict[str, object]:
    """Projeta a `Sobreposicao` — lista os candidatos, exige escolha (DOS-06)."""
    return {
        "tipo": "sobreposicao",
        "mensagem": sobreposicao.mensagem,
        "candidatos": [_lote_para_dict(lote) for lote in sobreposicao.candidatos],
    }


def cobertura_para_dict(cobertura: list[CoberturaCamada]) -> dict[str, object]:
    """Projeta a cobertura de um município para `200 /cobertura` (DOS-11/13)."""
    return {"cobertura": [_cobertura_para_dict(c) for c in cobertura]}


def cobertura_estado_para_dict(municipios: list[CoberturaMunicipio]) -> dict[str, object]:
    """Projeta a cobertura de todos os municípios para `200 /cobertura/estado` (COBPUB-01..03/06).

    Preenche toda `Camada` do domínio para cada município, mesmo quando a camada nunca apareceu em
    `cobertura` — a mesma honestidade de DOS-11: uma camada nunca fica omitida, vira `tem_dado`
    falso explícito (COBPUB-03, edge case "coluna nunca omitida").
    """
    return {
        "municipios": [
            {
                "municipio": item.municipio,
                "cobertura": [
                    _cobertura_para_dict(_camada_ou_ausente(item, camada)) for camada in Camada
                ],
            }
            for item in municipios
        ]
    }


def _camada_ou_ausente(item: CoberturaMunicipio, camada: Camada) -> CoberturaCamada:
    for registro in item.camadas:
        if registro.camada is camada:
            return registro
    return CoberturaCamada(camada=camada, tem_dado=False, data_extracao=None)


# --------------------------------------------------------------------------- #
# Projeções internas dos value objects
# --------------------------------------------------------------------------- #


def _lote_para_dict(lote: LoteHit) -> dict[str, object]:
    if isinstance(lote, LoteRural):
        return {
            "natureza": "rural",
            "lote_id": lote.lote_id,
            "codigo_sigef": lote.codigo_sigef,
            "situacao": lote.situacao.value,
            "municipios": list(lote.municipios),
            "area_ha": lote.area.valor,
            "perimetro_m": lote.perimetro_m,
            "denominacao": lote.denominacao,
        }
    return {
        "natureza": "urbano",
        "lote_id": lote.lote_id,
        "inscricao_cadastral": lote.inscricao_cadastral,
        "municipio": lote.municipio,
        "area_m2": lote.area.valor,
        "perimetro_m": lote.perimetro_m,
        "logradouro": lote.logradouro,
        "bairro": lote.bairro,
    }


def _item_restricao_para_dict(item: ItemRestricao) -> dict[str, object]:
    return {
        "tipo": item.tipo.value,
        "nome": item.nome,
        "area_intersecao_m2": item.area_intersecao.valor,
        "pct_do_lote": item.pct_do_lote,
        "marginal": item.marginal,
        "categoria": item.categoria,
        "grau_suscetibilidade": item.grau_suscetibilidade,
    }


def _proveniencia_para_dict(carimbo: Proveniencia) -> dict[str, object]:
    return {
        "fonte": carimbo.fonte,
        "data_extracao": carimbo.data_extracao.isoformat(),
        "link_oficial": carimbo.link_oficial,
    }


def _cobertura_para_dict(cobertura: CoberturaCamada) -> dict[str, object]:
    data = cobertura.data_extracao
    return {
        "camada": cobertura.camada.value,
        "tem_dado": cobertura.tem_dado,
        "data_extracao": data.isoformat() if data is not None else None,
    }
