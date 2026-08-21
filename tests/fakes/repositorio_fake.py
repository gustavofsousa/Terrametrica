"""Fakes em memória dos ports do dossiê — usados só nos testes de montagem.

Cumprem os Protocols `RepositorioLotes` e `LimiteEstado` sem I/O. Cada teste
instancia o seu, configurando exatamente o cenário que exercita um ramo da árvore.
"""

from dataclasses import dataclass, field

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


@dataclass
class FakeLimiteEstado:
    """Fronteira estadual fake: responde `contem` com um booleano fixo."""

    dentro: bool = True

    def contem(self, coord: Coordenada) -> bool:
        return self.dentro


@dataclass
class FakeRepositorioLotes:
    """Read-model fake configurável por teste."""

    lote: LoteHit | Sobreposicao | None = None
    municipio: str = "Niterói"
    intersecoes: list[IntersecaoBruta] = field(default_factory=list)
    proveniencias: dict[Camada, Proveniencia | None] = field(default_factory=dict)
    coberturas: list[CoberturaCamada] = field(default_factory=list)

    def lote_em(self, coord: Coordenada, versao: VersaoBase) -> LoteHit | Sobreposicao | None:
        return self.lote

    def intersecoes_de(self, lote: LoteHit, versao: VersaoBase) -> list[IntersecaoBruta]:
        return self.intersecoes

    def proveniencia_de(self, camada: Camada, versao: VersaoBase) -> Proveniencia | None:
        return self.proveniencias.get(camada)

    def municipio_em(self, coord: Coordenada, versao: VersaoBase) -> str:
        return self.municipio

    def cobertura_de(self, municipio: str) -> list[CoberturaCamada]:
        return self.coberturas
