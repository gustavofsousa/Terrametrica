"""Configuração de deploy lida do ambiente (AD-013) — pura, sem I/O além do `Mapping` recebido.

O deploy serve front e API na **mesma origem** (um serviço só): o cookie de sessão fica host-only
e `config.js` mantém `API_BASE = ""`. `TERRAMETRICA_DOMINIO_COOKIE` só existe para o desenho de
subdomínios (`app.`/`api.`) do design de F1.11, se um dia ele voltar.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

BASE_URL_PADRAO = "http://localhost:8000"
REMETENTE_PADRAO = "Terramétrica <onboarding@resend.dev>"
DIRETORIO_APP_PADRAO = Path(__file__).resolve().parents[3] / "app"
_VERDADEIROS = {"1", "true", "sim", "yes"}


@dataclass(frozen=True)
class ConfiguracaoDeploy:
    base_url: str
    resend_api_key: str | None
    remetente_email: str
    dominio_cookie: str | None
    diretorio_app: Path
    acesso_aberto: bool


def configuracao_de(ambiente: Mapping[str, str]) -> ConfiguracaoDeploy:
    """Monta a configuração a partir das variáveis de ambiente; vazio conta como ausente."""
    return ConfiguracaoDeploy(
        base_url=(_valor(ambiente, "TERRAMETRICA_BASE_URL") or BASE_URL_PADRAO).rstrip("/"),
        resend_api_key=_valor(ambiente, "RESEND_API_KEY"),
        remetente_email=_valor(ambiente, "TERRAMETRICA_EMAIL_REMETENTE") or REMETENTE_PADRAO,
        dominio_cookie=_valor(ambiente, "TERRAMETRICA_DOMINIO_COOKIE"),
        diretorio_app=Path(_valor(ambiente, "TERRAMETRICA_DIR_APP") or DIRETORIO_APP_PADRAO),
        acesso_aberto=_ligado(ambiente, "TERRAMETRICA_ACESSO_ABERTO"),
    )


def _valor(ambiente: Mapping[str, str], nome: str) -> str | None:
    valor = ambiente.get(nome, "").strip()
    return valor or None


def _ligado(ambiente: Mapping[str, str], nome: str) -> bool:
    return (_valor(ambiente, nome) or "").lower() in _VERDADEIROS
