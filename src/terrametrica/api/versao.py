"""Resolução da versão publicada no caminho de request (AD-011).

A API não recebe a versão do cliente: ela é resolvida no servidor a partir de `ponteiro_publicado`
(a versão apontada para `Camada.LOTE_RURAL`, camada-âncora do dossiê). Isso torna a idempotência do
dossiê (DOS-26) verdadeira por construção — a mesma coordenada devolve o mesmo dossiê enquanto o
ponteiro não muda — e mantém o cliente burro. É o primeiro leitor do ponteiro no caminho de leitura;
até aqui só a ingestão (`publicar.py`) o escrevia.
"""

import psycopg

from terrametrica.dominio.modelos import Camada, VersaoBase

MENSAGEM_SEM_VERSAO = (
    "nenhuma versão publicada para a camada lote_rural — o pipeline de ingestão/publicação "
    "ainda não rodou (ponteiro_publicado vazio). A API não tem base para servir."
)


class SemVersaoPublicada(RuntimeError):
    """Não há versão publicada — a API não pode montar dossiê sobre base inexistente."""


_SELECT_VERSAO_PUBLICADA = """
    SELECT vb.id, vb.criada_em
    FROM ponteiro_publicado pp
    JOIN versao_base vb ON vb.id = pp.versao_base_id
    WHERE pp.camada = %(camada)s
"""


def resolver_versao_publicada(conexao: psycopg.Connection) -> VersaoBase:
    """Devolve a `VersaoBase` publicada para `lote_rural`, ou levanta `SemVersaoPublicada`."""
    with conexao.cursor() as cursor:
        cursor.execute(_SELECT_VERSAO_PUBLICADA, {"camada": Camada.LOTE_RURAL.value})
        linha = cursor.fetchone()
    if linha is None:
        raise SemVersaoPublicada(MENSAGEM_SEM_VERSAO)
    versao_id, criada_em = linha
    return VersaoBase(id=versao_id, criada_em=criada_em)
