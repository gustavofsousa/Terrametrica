"""Tipos-resultado dos passos de ingestão.

`RelatorioCamada` e `ResultadoPublicacao` são citados em design.md (seção `ingestao`) mas nunca
foram definidos como tipo concreto antes desta fase. Não são modelos de domínio de negócio —
não vivem em `dominio/modelos.py` — são metadados de execução do pipeline (o que foi gravado,
o que a guarda de publicação decidiu por camada). Mantidos deliberadamente mínimos: só os campos
que `ingerir_limite_rj`/`ingerir_sigef`/`publicar_versao` (T11-T13) realmente produzem/consomem.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RelatorioCamada:
    """Retorno de `ingerir_limite_rj`/`ingerir_sigef`: o que foi gravado nesta chamada.

    `camada` é o identificador de texto usado em `proveniencia`/`ponteiro_publicado`
    (ex.: `"limite_estado"`, ou `Camada.LOTE_RURAL.value`) — não é necessariamente um membro
    do enum `Camada` do domínio, já que `limite_estado` não é uma camada de restrição.
    """

    camada: str
    versao_base_id: str
    feicoes_gravadas: int
    feicoes_corrigidas: int = 0
    feicoes_sem_geometria: int = 0  # lote sem polígono: não grava, mas conta (nunca some calado)


@dataclass(frozen=True, slots=True)
class RelatorioPublicacaoCamada:
    """Decisão da guarda de publicação (DOS-25) para uma camada.

    `feicoes_anteriores` é `None` quando não havia versão publicada antes desta camada
    (primeira publicação, sempre passa a guarda por definição).
    """

    camada: str
    publicada: bool
    feicoes_novas: int
    feicoes_anteriores: int | None


@dataclass(frozen=True, slots=True)
class ResultadoPublicacao:
    """Retorno de `publicar_versao`: decisão por camada da tentativa de publicação."""

    versao_base_id: str
    camadas: tuple[RelatorioPublicacaoCamada, ...]

    @property
    def publicada(self) -> bool:
        """True somente se a guarda passou para todas as camadas e o swap ocorreu."""
        return all(c.publicada for c in self.camadas)


@dataclass(frozen=True, slots=True)
class RelatorioIntersecoes:
    """Retorno de `materializar_intersecoes` (Fatia 3): quantos pares lote×restrição
    tiveram intersecção real (área > 0) gravados em `intersecao_materializada`."""

    versao_base_id: str
    pares_materializados: int


@dataclass(frozen=True, slots=True)
class RelatorioCobertura:
    """Retorno de `semear_cobertura` (Fatia 4): quantas linhas (município × camada de restrição)
    foram semeadas em `cobertura` a partir do que a versão publicou (AD-009)."""

    versao_base_id: str
    linhas_semeadas: int
