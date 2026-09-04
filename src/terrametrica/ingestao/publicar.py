"""Publicação de versão — guarda de 90% de feições + swap atômico do ponteiro (DOS-25/28).

Decisão desta fase: a guarda é avaliada por camada (`limite_estado`, `lote_rural`), mas a
decisão de publicar é única para a versão inteira — se QUALQUER camada reprovar a guarda
(<90% das feições da versão publicada anteriormente), a publicação inteira é rejeitada e o
`ponteiro_publicado` de TODAS as camadas permanece na versão anterior. Não há swap parcial:
misturar um `limite_estado` novo com um `lote_rural` antigo (ou vice-versa) quebraria a
consistência geográfica entre as duas camadas de uma mesma reingestão — o mesmo espírito de
atomicidade do DOS-28, aplicado também à decisão de aceitar/rejeitar, não só à escrita.

Contrato de transação: `ingerir_limite_rj`/`ingerir_sigef` não comitam (ver seus docstrings).
Esta função comita o swap — e, transitivamente, qualquer staging feito na mesma transação —
somente quando a guarda passa para todas as camadas; se a guarda reprovar, não comita nem
reverte (a decisão de descartar a tentativa de staging é de quem orquestra a chamada). Se uma
falha inesperada ocorrer durante a escrita do swap em si, a transação é revertida por completo
antes do erro ser relançado — nenhuma camada fica com o ponteiro trocado e outra não (DOS-28).
"""

import psycopg

from terrametrica.dominio.modelos import Camada, VersaoBase
from terrametrica.ingestao.limite_rj import CAMADA_LIMITE_ESTADO
from terrametrica.ingestao.tipos import RelatorioPublicacaoCamada, ResultadoPublicacao

LIMIAR_GUARDA = 0.90

_CAMADAS_PUBLICADAS = (CAMADA_LIMITE_ESTADO, Camada.LOTE_RURAL.value)

_QUERY_CONTAGEM_POR_CAMADA = {
    CAMADA_LIMITE_ESTADO: "SELECT COUNT(*) FROM limite_estado WHERE versao_base_id = %(versao)s",
    Camada.LOTE_RURAL.value: "SELECT COUNT(*) FROM lote_rural WHERE versao_base_id = %(versao)s",
}

_SELECT_VERSAO_PUBLICADA = """
    SELECT versao_base_id FROM ponteiro_publicado WHERE camada = %(camada)s
"""

_UPSERT_PONTEIRO = """
    INSERT INTO ponteiro_publicado (camada, versao_base_id)
    VALUES (%(camada)s, %(versao)s)
    ON CONFLICT (camada) DO UPDATE SET versao_base_id = EXCLUDED.versao_base_id
"""

_MARCAR_PUBLICADA = "UPDATE versao_base SET status = 'published' WHERE id = %(versao)s"


def _contar_feicoes(conexao: psycopg.Connection, camada: str, versao_id: str) -> int:
    with conexao.cursor() as cursor:
        cursor.execute(_QUERY_CONTAGEM_POR_CAMADA[camada], {"versao": versao_id})
        linha = cursor.fetchone()
    assert linha is not None  # COUNT(*) sempre devolve exatamente 1 linha
    (total,) = linha
    return int(total)


def _versao_publicada_atual(conexao: psycopg.Connection, camada: str) -> str | None:
    with conexao.cursor() as cursor:
        cursor.execute(_SELECT_VERSAO_PUBLICADA, {"camada": camada})
        linha = cursor.fetchone()
    return linha[0] if linha is not None else None


def _avaliar_camada(
    conexao: psycopg.Connection, camada: str, versao_id: str
) -> RelatorioPublicacaoCamada:
    feicoes_novas = _contar_feicoes(conexao, camada, versao_id)
    versao_anterior_id = _versao_publicada_atual(conexao, camada)

    if versao_anterior_id is None:
        # sem versão anterior publicada para esta camada — sempre passa (DOS-25/edge)
        return RelatorioPublicacaoCamada(
            camada=camada, publicada=True, feicoes_novas=feicoes_novas, feicoes_anteriores=None
        )

    feicoes_anteriores = _contar_feicoes(conexao, camada, versao_anterior_id)
    if feicoes_anteriores == 0:
        # nada para comparar de fato — trata como "sem versão anterior" para efeito da guarda
        passou = True
    else:
        passou = (feicoes_novas / feicoes_anteriores) >= LIMIAR_GUARDA

    return RelatorioPublicacaoCamada(
        camada=camada,
        publicada=passou,
        feicoes_novas=feicoes_novas,
        feicoes_anteriores=feicoes_anteriores,
    )


def _trocar_ponteiro(conexao: psycopg.Connection, camada: str, versao_id: str) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(_UPSERT_PONTEIRO, {"camada": camada, "versao": versao_id})


def publicar_versao(versao: VersaoBase, conexao: psycopg.Connection) -> ResultadoPublicacao:
    """Avalia a guarda de 90% por camada e, se todas passarem, troca o ponteiro publicado
    atomicamente. Ver docstring do módulo para o contrato de transação."""
    avaliacoes = tuple(
        _avaliar_camada(conexao, camada, versao.id) for camada in _CAMADAS_PUBLICADAS
    )

    if not all(avaliacao.publicada for avaliacao in avaliacoes):
        return ResultadoPublicacao(versao_base_id=versao.id, camadas=avaliacoes)

    try:
        for camada in _CAMADAS_PUBLICADAS:
            _trocar_ponteiro(conexao, camada, versao.id)
        with conexao.cursor() as cursor:
            cursor.execute(_MARCAR_PUBLICADA, {"versao": versao.id})
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise

    return ResultadoPublicacao(versao_base_id=versao.id, camadas=avaliacoes)
