"""Contratos (ports) que a montagem do dossiê consome.

Só interfaces — nenhuma implementação, nenhum I/O importado. Mantêm a fonte
externa fora do caminho de request (AD-004): a montagem depende destes Protocols,
e a versão concreta (PostGIS) é injetada. Nos testes, um fake em memória os cumpre.
"""

from typing import Protocol

from terrametrica.dominio.modelos import (
    Camada,
    CoberturaCamada,
    Coordenada,
    IntersecaoBruta,
    LoteHit,
    Proveniencia,
    Sobreposicao,
    VersaoBase,
)


class RepositorioLotes(Protocol):
    """Leitura do read-model materializado de uma versão de base publicada."""

    def lote_em(self, coord: Coordenada, versao: VersaoBase) -> LoteHit | Sobreposicao | None:
        """Lote que contém o ponto; `Sobreposicao` se dois ou mais o reivindicam
        (DOS-06); `None` se nenhum polígono conhecido cobre o ponto (DOS-04)."""
        ...

    def intersecoes_de(self, lote: LoteHit, versao: VersaoBase) -> list[IntersecaoBruta]:
        """Cruzamentos pré-calculados do lote com as camadas de restrição (DOS-07)."""
        ...

    def proveniencia_de(self, camada: Camada, versao: VersaoBase) -> Proveniencia | None:
        """Carimbo de proveniência da camada nesta versão (DOS-10).

        `None` = camada sem stamp nesta versão → "indisponível no momento" (DOS-12),
        distinto de "sem cobertura no município", que vem de `cobertura_de`.
        """
        ...

    def municipio_em(self, coord: Coordenada, versao: VersaoBase) -> str:
        """Município que contém o ponto (malha IBGE). Usado para declarar cobertura
        quando não há lote no ponto (DOS-04). Só é chamado após `LimiteEstado.contem`
        confirmar que a coordenada está no RJ, então sempre resolve um município."""
        ...

    def cobertura_de(self, municipio: str) -> list[CoberturaCamada]:
        """Cobertura declarada por camada no município (DOS-11/13)."""
        ...


class LimiteEstado(Protocol):
    """Fronteira estadual — mantém a UF como dimensão explícita (AD-001)."""

    def contem(self, coord: Coordenada) -> bool:
        """True se a coordenada está dentro do RJ; senão a consulta é recusada (DOS-05)."""
        ...
