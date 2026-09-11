"""App FastAPI — entrypoint fino do dossiê (AD-007/AD-011).

Cada rota é fina: resolve a versão publicada (servidor, não cliente — DOS-26), injeta a identidade
opaca da conta (DOS-30/DOS-27), aplica a cota, chama `montar_dossie` e traduz o tipo-resultado da
montagem em HTTP + DTO. Nenhuma regra de negócio vive aqui — ela está em `dossie`/`geometria`/
`dominio`, reusados intactos (os mesmos adapters do `test_dossie_e2e`).

`criar_app` recebe a URL do banco, o limitador e um relógio por injeção, para o teste controlar o
tempo (cota 100/1h) e apontar para o container efêmero. Cada request abre e fecha sua própria
conexão psycopg (sem pool nesta fatia, MVP de um processo).
"""

from collections.abc import Callable
from datetime import datetime

import psycopg
from fastapi import FastAPI, Query, Response, status
from fastapi.responses import JSONResponse

from terrametrica.api.dto import (
    cobertura_para_dict,
    dossie_para_dict,
    sem_lote_para_dict,
    sobreposicao_para_dict,
)
from terrametrica.api.identidade import Credenciais, resolver_conta_id
from terrametrica.api.limite_taxa import Bloqueado, LimitadorEmMemoria
from terrametrica.api.observabilidade import EntradaConsulta, registrar_consulta
from terrametrica.api.versao import resolver_versao_publicada
from terrametrica.auth.adaptadores import RepositorioSessaoPostgres
from terrametrica.auth.portas import RepositorioSessao
from terrametrica.dominio.modelos import (
    Coordenada,
    Dossie,
    ErroValidacao,
    ForaDoRJ,
    SemLote,
    Sobreposicao,
)
from terrametrica.dossie.montagem import montar_dossie
from terrametrica.persistencia.conexao import abrir_conexao
from terrametrica.persistencia.limite_estado_postgis import LimiteEstadoPostGIS
from terrametrica.persistencia.repositorio_lotes_postgis import RepositorioLotesPostGIS


def criar_app(
    url_banco: str | None = None,
    *,
    limitador: LimitadorEmMemoria | None = None,
    relogio: Callable[[], datetime] | None = None,
    repo_sessao: Callable[[psycopg.Connection], RepositorioSessao] | None = None,
) -> FastAPI:
    """Monta a app FastAPI com as rotas do dossiê. Dependências injetáveis para teste."""
    app = FastAPI(title="Terramétrica — API do dossiê", version="0.1.0")
    limitador_efetivo = limitador if limitador is not None else LimitadorEmMemoria()
    agora = relogio if relogio is not None else datetime.now
    repo_sessao_de = repo_sessao if repo_sessao is not None else RepositorioSessaoPostgres

    @app.get("/saude")
    def saude() -> dict[str, str]:
        """Liveness — não toca o banco."""
        return {"status": "ok"}

    @app.get("/dossie")
    def dossie(
        credenciais: Credenciais,
        lat: float = Query(...),
        lon: float = Query(...),
    ) -> Response:
        with abrir_conexao(url_banco) as conexao:
            # Identidade por sessão (cookie) OU header, resolvida com a conexão já aberta.
            conta_id = resolver_conta_id(credenciais, repo_sessao_de(conexao), agora())

            cota = limitador_efetivo.checar(conta_id, agora())
            if isinstance(cota, Bloqueado):
                return _resposta_cota_estourada(cota)

            inicio = agora()
            resposta, lote_id, camadas = _montar_e_traduzir(conexao, lat, lon)
            latencia_ms = int((agora() - inicio).total_seconds() * 1000)
            registrar_consulta(
                conexao,
                EntradaConsulta(
                    conta_id=conta_id,
                    latencia_ms=latencia_ms,
                    lote_id=lote_id,
                    camadas=camadas,
                ),
            )
        return resposta

    @app.get("/cobertura")
    def cobertura(municipio: str = Query(...)) -> Response:
        with abrir_conexao(url_banco) as conexao:
            repo = RepositorioLotesPostGIS(conexao)
            corpo = cobertura_para_dict(repo.cobertura_de(municipio))
        return JSONResponse(status_code=status.HTTP_200_OK, content=corpo)

    return app


def _montar_e_traduzir(
    conexao: psycopg.Connection, lat: float, lon: float
) -> tuple[Response, str | None, tuple[str, ...]]:
    """Chama o motor e traduz o tipo-resultado em (Response, lote_id, camadas) para o log."""
    try:
        coord = Coordenada(lat=lat, lon=lon)
    except ErroValidacao as erro:
        return _json(status.HTTP_422_UNPROCESSABLE_ENTITY, {"erro": str(erro)}), None, ()

    versao = resolver_versao_publicada(conexao)
    repo = RepositorioLotesPostGIS(conexao)
    limite = LimiteEstadoPostGIS(conexao)
    resultado = montar_dossie(coord, versao, repo, limite)

    if isinstance(resultado, ForaDoRJ):
        corpo: dict[str, object] = {"tipo": "fora_do_rj", "mensagem": resultado.mensagem}
        return _json(status.HTTP_422_UNPROCESSABLE_ENTITY, corpo), None, ()

    if isinstance(resultado, Sobreposicao):
        corpo = sobreposicao_para_dict(resultado)
        return _json(status.HTTP_409_CONFLICT, corpo), None, ()

    if isinstance(resultado, SemLote):
        corpo = sem_lote_para_dict(resultado)
        return _json(status.HTTP_404_NOT_FOUND, corpo), None, ()

    assert isinstance(resultado, Dossie)
    corpo = dossie_para_dict(resultado)
    camadas = tuple(_camadas_do_dossie(resultado))
    return _json(status.HTTP_200_OK, corpo), resultado.lote.lote_id, camadas


def _camadas_do_dossie(dossie: Dossie) -> list[str]:
    """Camadas com proveniência no dossiê — o que a consulta de fato entregou (DOS-30)."""
    return [camada.value for camada in dossie.proveniencia]


def _resposta_cota_estourada(cota: Bloqueado) -> JSONResponse:
    """429 + Retry-After quando a conta estoura a cota (DOS-27/AF-2)."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "erro": "cota de consultas excedida (100/hora)",
            "retry_after_segundos": cota.retry_after_segundos,
        },
        headers={"Retry-After": str(cota.retry_after_segundos)},
    )


def _json(status_code: int, corpo: dict[str, object]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=corpo)


# Factory p/ deploy: `uvicorn terrametrica.api.app:app_padrao --factory` (lê TERRAMETRICA_DB_URL).
# Os testes usam `criar_app(url)` com o container efêmero, não esta factory.
def app_padrao() -> FastAPI:  # pragma: no cover - conveniência de deploy, exercido só via uvicorn
    return criar_app()
