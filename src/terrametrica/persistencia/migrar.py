"""Runner de migrações SQL — aplica `migracoes/*.sql` em ordem, idempotente.

A tabela de controle `schema_migrations` registra o que já foi aplicado, para que
rodar `aplicar_migracoes` duas vezes não reaplique nada.
"""

from collections.abc import Iterator
from pathlib import Path

import psycopg

DIRETORIO_MIGRACOES = Path(__file__).parent / "migracoes"

_CRIAR_TABELA_CONTROLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    nome_arquivo text PRIMARY KEY,
    aplicada_em timestamptz NOT NULL DEFAULT now()
)
"""


def aplicar_migracoes(conexao: psycopg.Connection) -> None:
    """Aplica, em ordem alfabética, os arquivos `.sql` de `migracoes/` ainda não registrados."""
    with conexao.cursor() as cursor:
        cursor.execute(_CRIAR_TABELA_CONTROLE)
        cursor.execute("SELECT nome_arquivo FROM schema_migrations")
        ja_aplicadas = {linha[0] for linha in cursor.fetchall()}

    for arquivo in sorted(DIRETORIO_MIGRACOES.glob("*.sql")):
        if arquivo.name in ja_aplicadas:
            continue
        with conexao.cursor() as cursor:
            for comando in _comandos(arquivo.read_text(encoding="utf-8")):
                cursor.execute(comando)
            cursor.execute(
                "INSERT INTO schema_migrations (nome_arquivo) VALUES (%s)", (arquivo.name,)
            )
        conexao.commit()


def _comandos(sql: str) -> Iterator[str]:
    """Divide um arquivo de migração em comandos individuais (um por `;`)."""
    for trecho in sql.split(";"):
        comando = trecho.strip()
        if comando:
            yield comando
