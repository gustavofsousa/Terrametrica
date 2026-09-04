"""Conexão com o banco PostGIS via psycopg."""

import os

import psycopg

VARIAVEL_URL = "TERRAMETRICA_DB_URL"


def abrir_conexao(url: str | None = None) -> psycopg.Connection:
    """Abre uma conexão psycopg.

    Usa `url` se informada; senão lê a variável de ambiente `TERRAMETRICA_DB_URL`.
    """
    url_efetiva = url or os.environ.get(VARIAVEL_URL)
    if not url_efetiva:
        raise RuntimeError(
            f"variável de ambiente {VARIAVEL_URL} não definida e nenhuma URL foi informada"
        )
    return psycopg.connect(url_efetiva)
