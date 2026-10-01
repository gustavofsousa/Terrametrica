"""CLI de carga da base (AD-013): migra o banco e publica uma versão a partir dos arquivos brutos.

Mesmo contrato de transação do `test_dossie_e2e`: cria a `versao_base` (draft) e comita essa linha →
ingestões em staging (sem commit) → `materializar_intersecoes` → `semear_cobertura` →
`publicar_versao`, que comita tudo só se a guarda de ≥90% passar.

OPS: roda local contra o PostGIS do `docker-compose.yml` e a base vai para produção por
`pg_dump`/`pg_restore`. As ingestões gravam feição a feição; rodá-las direto contra um banco em
outro continente custaria uma ida-e-volta de rede por feição.

    python -m terrametrica.ingestao.carregar_base --versao rj-2026-09-30 \\
        --sigef data/raw/rj/Sigef-Brasil-RJ.zip \\
        --reserva-legal data/raw/rj/RESERVA-LEGAL.zip \\
        --uc data/raw/rj/uc/uc_erj.geojson
"""

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import psycopg

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.cobertura import semear_cobertura
from terrametrica.ingestao.intersecoes import materializar_intersecoes
from terrametrica.ingestao.limite_rj import ingerir_limite_rj
from terrametrica.ingestao.publicar import publicar_versao
from terrametrica.ingestao.restricao_car import ingerir_app_car, ingerir_reserva_legal_car
from terrametrica.ingestao.restricao_uc import ingerir_uc
from terrametrica.ingestao.sigef import ingerir_sigef
from terrametrica.persistencia.conexao import abrir_conexao
from terrametrica.persistencia.migrar import aplicar_migracoes


def _ler_argumentos(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migra o banco e publica uma versão da base.")
    parser.add_argument("--versao", help="id da versão, ex: rj-2026-09-30 (exigido na carga)")
    parser.add_argument("--sigef", type=Path, help="shapefile (ou .zip) SIGEF do RJ")
    parser.add_argument("--app", type=Path, help="shapefile (ou .zip) APP do CAR")
    parser.add_argument("--reserva-legal", type=Path, help="shapefile (ou .zip) RL do CAR")
    parser.add_argument("--uc", type=Path, help="GeoJSON de Unidades de Conservação")
    parser.add_argument(
        "--so-migrar", action="store_true", help="aplica as migrações e sai, sem carga"
    )
    argumentos = parser.parse_args(argv)
    if not argumentos.so_migrar and not argumentos.versao:
        parser.error("--versao é obrigatório fora de --so-migrar")
    return argumentos


def _criar_versao_draft(versao: VersaoBase, conexao: psycopg.Connection) -> None:
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO versao_base (id, criada_em, status) VALUES (%s, %s, %s)",
            (versao.id, versao.criada_em, "draft"),
        )
    conexao.commit()


def _ingerir_camadas(
    argumentos: argparse.Namespace, versao: VersaoBase, conexao: psycopg.Connection
) -> None:
    print("limite do RJ (geobr)...", flush=True)
    ingerir_limite_rj(versao, conexao)
    if argumentos.sigef:
        print(f"SIGEF: {argumentos.sigef}", flush=True)
        print(f"  {ingerir_sigef(argumentos.sigef, versao, conexao)}", flush=True)
    if argumentos.app:
        print(f"APP: {argumentos.app}", flush=True)
        print(f"  {ingerir_app_car(argumentos.app, versao, conexao)}", flush=True)
    if argumentos.reserva_legal:
        print(f"Reserva Legal: {argumentos.reserva_legal}", flush=True)
        relatorio = ingerir_reserva_legal_car(argumentos.reserva_legal, versao, conexao)
        print(f"  {relatorio}", flush=True)
    if argumentos.uc:
        print(f"UC: {argumentos.uc}", flush=True)
        print(f"  {ingerir_uc(argumentos.uc, versao, conexao)}", flush=True)
    print("materializando intersecções...", flush=True)
    materializar_intersecoes(versao, conexao)
    print("semeando cobertura...", flush=True)
    semear_cobertura(versao, conexao)


def main(argv: Sequence[str] | None = None) -> int:
    argumentos = _ler_argumentos(sys.argv[1:] if argv is None else argv)
    with abrir_conexao() as conexao:
        aplicar_migracoes(conexao)
        print("migrações aplicadas", flush=True)
        if argumentos.so_migrar:
            return 0

        versao = VersaoBase(id=argumentos.versao, criada_em=date.today())
        _criar_versao_draft(versao, conexao)
        _ingerir_camadas(argumentos, versao, conexao)
        resultado = publicar_versao(versao, conexao)

    for camada in resultado.camadas:
        print(f"  {camada}", flush=True)
    if not resultado.publicada:
        print(f"versão {versao.id} NÃO publicada: guarda de 90% reprovou", file=sys.stderr)
        return 1
    print(f"versão {versao.id} publicada", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
