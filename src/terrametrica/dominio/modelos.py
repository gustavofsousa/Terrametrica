"""Value objects e tipos-resultado do domínio do dossiê.

Este módulo é o hub do vocabulário ubíquo (glossário do produto). Não faz I/O:
os `portas` (contratos) e a `montagem` importam daqui, nunca o contrário.

Princípios aplicados (AGENTS.md):
- validar dado não confiável no boundary (construtores rejeitam estado ilegal);
- tornar estados ilegais irrepresentáveis (conjuntos fechados como enums, união
  fechada de resultados da montagem).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

METROS_QUADRADOS_POR_HECTARE = 10_000.0


class ErroValidacao(ValueError):
    """Falha de validação no boundary do domínio."""


# --------------------------------------------------------------------------- #
# Conjuntos fechados (make illegal states unrepresentable)
# --------------------------------------------------------------------------- #


class Camada(StrEnum):
    """Camada de dado versionada — carrega proveniência e cobertura por município."""

    LOTE_RURAL = "lote_rural"
    LOTE_URBANO = "lote_urbano"
    APP = "app"
    RESERVA_LEGAL = "reserva_legal"
    UNIDADE_CONSERVACAO = "unidade_conservacao"
    INUNDACAO = "inundacao"
    DESLIZAMENTO = "deslizamento"
    CORPO_DAGUA = "corpo_dagua"


class TipoRestricao(StrEnum):
    """Tipo de restrição cruzada com o lote na seção de alertas do dossiê."""

    APP = "app"
    RESERVA_LEGAL = "reserva_legal"
    UNIDADE_CONSERVACAO = "unidade_conservacao"
    INUNDACAO = "inundacao"
    DESLIZAMENTO = "deslizamento"
    CORPO_DAGUA = "corpo_dagua"

    @property
    def camada(self) -> Camada:
        """A camada versionada que origina esta restrição (fonte única, sem drift)."""
        return Camada(self.value)


class SituacaoCertificacao(StrEnum):
    """Situação da certificação do imóvel rural no SIGEF."""

    CERTIFICADO = "certificado"
    EM_ANALISE = "em_analise"


class PapelConta(StrEnum):
    """Papel da conta — fronteira reservada do gate jurídico (P2), sem dado pessoal."""

    CONSULTA = "consulta"
    HABILITADO_JURIDICAMENTE = "habilitado_juridicamente"


class TipoLote(StrEnum):
    """Natureza do lote resolvido no ponto clicado."""

    RURAL = "rural"
    URBANO = "urbano"


# --------------------------------------------------------------------------- #
# Value objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Coordenada:
    """Ponto clicado no mapa. Valida faixa global de lat/lon (DOS-02).

    A contenção no RJ (DOS-05) é responsabilidade do port `LimiteEstado`, não
    deste value object — o produto federa outras UFs depois sem reescrever isto.
    """

    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ErroValidacao(f"latitude fora de faixa [-90, 90]: {self.lat}")
        if not -180.0 <= self.lon <= 180.0:
            raise ErroValidacao(f"longitude fora de faixa [-180, 180]: {self.lon}")


@dataclass(frozen=True, slots=True)
class AreaM2:
    """Área em metros quadrados (unidade do lote urbano)."""

    valor: float

    def __post_init__(self) -> None:
        if self.valor < 0.0:
            raise ErroValidacao(f"área em m² não pode ser negativa: {self.valor}")

    def em_hectares(self) -> "AreaHa":
        return AreaHa(self.valor / METROS_QUADRADOS_POR_HECTARE)


@dataclass(frozen=True, slots=True)
class AreaHa:
    """Área em hectares (unidade do imóvel rural)."""

    valor: float

    def __post_init__(self) -> None:
        if self.valor < 0.0:
            raise ErroValidacao(f"área em ha não pode ser negativa: {self.valor}")

    def em_metros_quadrados(self) -> AreaM2:
        return AreaM2(self.valor * METROS_QUADRADOS_POR_HECTARE)


@dataclass(frozen=True, slots=True)
class Proveniencia:
    """Fonte, data de extração e link oficial de uma camada (DOS-10)."""

    fonte: str
    data_extracao: date
    link_oficial: str


@dataclass(frozen=True, slots=True)
class CampoComProveniencia[T]:
    """Um valor do dossiê carimbado com sua proveniência — zero dado órfão."""

    valor: T
    proveniencia: Proveniencia


@dataclass(frozen=True, slots=True)
class VersaoBase:
    """Ponteiro para uma versão publicada da base (idempotência do dossiê, DOS-26)."""

    id: str
    criada_em: date


@dataclass(frozen=True, slots=True)
class CoberturaCamada:
    """Estado de cobertura de uma camada em um município (DOS-11/13)."""

    camada: Camada
    tem_dado: bool
    data_extracao: date | None = None


@dataclass(frozen=True, slots=True)
class IntersecaoBruta:
    """Cruzamento lote × restrição com a área já calculada pelo read-model.

    A classificação de toque marginal (DOS-08) é aplicada na montagem, não aqui.
    """

    tipo: TipoRestricao
    nome: str
    area_intersecao: AreaM2
    categoria: str | None = None
    grau_suscetibilidade: str | None = None


@dataclass(frozen=True, slots=True)
class ItemRestricao:
    """Restrição já avaliada para exibição: área, percentual e flag marginal (DOS-07/08)."""

    tipo: TipoRestricao
    nome: str
    area_intersecao: AreaM2
    pct_do_lote: float
    marginal: bool
    categoria: str | None = None
    grau_suscetibilidade: str | None = None


# --------------------------------------------------------------------------- #
# Identidade do lote — união fechada rural | urbano
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class LoteRural:
    """Imóvel rural certificado (SIGEF). Área em hectares."""

    lote_id: str
    municipios: tuple[str, ...]
    codigo_sigef: str
    situacao: SituacaoCertificacao
    area: AreaHa
    perimetro_m: float
    denominacao: str | None = None


@dataclass(frozen=True, slots=True)
class LoteUrbano:
    """Lote urbano (SIGeo Niterói). Área em metros quadrados."""

    lote_id: str
    municipio: str
    inscricao_cadastral: str
    area: AreaM2
    perimetro_m: float
    logradouro: str | None = None
    bairro: str | None = None


LoteHit = LoteRural | LoteUrbano


# --------------------------------------------------------------------------- #
# Tipos-resultado da montagem — união fechada
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ForaDoRJ:
    """Coordenada fora do estado do RJ (DOS-05)."""

    MENSAGEM = "fora da área de cobertura: apenas RJ"

    @property
    def mensagem(self) -> str:
        return self.MENSAGEM


@dataclass(frozen=True, slots=True)
class SemLote:
    """Clique sem polígono conhecido: município + cobertura declarada (DOS-04)."""

    municipio: str
    cobertura: tuple[CoberturaCamada, ...]

    MENSAGEM = "sem lote mapeado neste ponto"

    @property
    def mensagem(self) -> str:
        return self.MENSAGEM


@dataclass(frozen=True, slots=True)
class Sobreposicao:
    """Ponto sobre dois ou mais polígonos: exige escolha antes de montar (DOS-06)."""

    candidatos: tuple[LoteHit, ...]

    MENSAGEM = "sobreposição de lotes: escolha um imóvel antes de montar o dossiê"

    def __post_init__(self) -> None:
        if len(self.candidatos) < 2:
            raise ErroValidacao("sobreposição exige ao menos 2 candidatos")

    @property
    def mensagem(self) -> str:
        return self.MENSAGEM


@dataclass(frozen=True, slots=True)
class Dossie:
    """Dossiê montado a partir do read-model de uma versão de base.

    `camadas_ausentes` = indisponíveis no momento (DOS-12);
    `camadas_sem_cobertura` = sem dado no município (DOS-11);
    `camadas_desatualizadas` = extração > 90 dias (DOS-13).
    """

    lote: LoteHit
    itens_restricao: tuple[ItemRestricao, ...]
    proveniencia: Mapping[Camada, Proveniencia]
    camadas_ausentes: tuple[Camada, ...] = ()
    camadas_sem_cobertura: tuple[Camada, ...] = ()
    camadas_desatualizadas: tuple[Camada, ...] = ()
    ressalva: str = field(
        default=(
            "Os cruzamentos são indicativos e não substituem levantamento técnico "
            "ou licenciamento."
        )
    )


ResultadoDossie = Dossie | SemLote | Sobreposicao | ForaDoRJ


# --------------------------------------------------------------------------- #
# Gate jurídico (P2) — fronteira arquitetada, sem dado pessoal (AD-002)
# --------------------------------------------------------------------------- #


class TipoEventoAuditoria(StrEnum):
    """Tipo de evento do log de auditoria do gate jurídico (GATE-04/05)."""

    CONSULTA_REGISTRAL = "consulta_registral"
    PROMOCAO = "promocao"


@dataclass(frozen=True, slots=True)
class Conta:
    """Conta do produto, com exatamente um papel (GATE-01).

    Não tem campo capaz de carregar nome, CPF ou CNPJ de proprietário — a
    ausência é garantia estrutural de GATE-06, não uma regra validada em runtime.
    """

    id: str
    papel: PapelConta


@dataclass(frozen=True, slots=True)
class EntradaAuditoria:
    """Uma entrada do log de auditoria: consulta registral ou promoção de papel
    (GATE-04/05). Campos não aplicáveis ao `tipo` do evento ficam `None`.
    """

    id: str
    ts: datetime
    conta_id: str
    tipo: TipoEventoAuditoria
    finalidade: str | None = None
    lote_id: str | None = None
    promovido_por: str | None = None
    credencial_verificada: str | None = None


@dataclass(frozen=True, slots=True)
class Permitido:
    """Acesso a dado registral permitido (GATE-03)."""


@dataclass(frozen=True, slots=True)
class Negado:
    """Acesso a dado registral negado (GATE-03)."""

    MENSAGEM = "acesso negado: papel da conta não habilita dado registral"

    @property
    def mensagem(self) -> str:
        return self.MENSAGEM


ResultadoAcesso = Permitido | Negado


@dataclass(frozen=True, slots=True)
class Indisponivel:
    """Seção de proprietário indisponível nesta versão (GATE-02, AD-002).

    Única variante enquanto `CAMADA_REGISTRAL_LIGADA` for `False`; o tipo-resultado
    fica pronto para uma variante `Disponivel` futura sem quebrar a assinatura.
    """

    mensagem: str = "indisponível nesta versão"


EstadoSecao = Indisponivel
