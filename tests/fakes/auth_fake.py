"""Fakes em memória dos ports de auth — usados nos testes do serviço (Fatia 7, T4).

Cumprem `RepositorioCredencial`, `RepositorioToken`, `RepositorioSessao`, `EnviadorEmail`
(`auth/portas.py`) sem I/O. `consumir` replica a atomicidade do adaptador real (marca usado e não
reautentica no segundo consumo).
"""

from dataclasses import dataclass, field
from datetime import datetime

from terrametrica.auth.regras import Email, RegistroToken, token_valido
from terrametrica.auth.servico import EXPIRACAO_TOKEN
from terrametrica.dominio.modelos import PapelConta


@dataclass
class FakeRepositorioCredencial:
    """e-mail → conta_id em memória. Conta nova recebe um id sequencial determinístico."""

    contas: dict[str, str] = field(default_factory=dict)  # email.valor → conta_id
    _proximo: int = 1

    def conta_de_email(self, email: Email) -> str | None:
        return self.contas.get(email.valor)

    def criar_conta_para_email(self, email: Email, papel: PapelConta) -> str:
        assert papel is PapelConta.CONSULTA  # a fatia só cria conta CONSULTA (GATE)
        conta_id = f"conta-{self._proximo}"
        self._proximo += 1
        self.contas[email.valor] = conta_id
        return conta_id


@dataclass
class FakeRepositorioToken:
    """login_token em memória, indexado por hash. `consumir` é atômico (uso único).

    `criado_em` de cada token é derivado de `expira_em - EXPIRACAO_TOKEN` — o serviço sempre salva
    com `expira_em = agora + EXPIRACAO_TOKEN`, então esse cálculo recupera o `agora` da emissão sem
    precisar estender a porta (a query real usa a coluna `criado_em DEFAULT now()`).
    """

    registros: dict[str, RegistroToken] = field(default_factory=dict)
    _criado_em: dict[str, datetime] = field(default_factory=dict)

    def salvar(self, hash_token: str, email: Email, expira_em: datetime) -> None:
        self.registros[hash_token] = RegistroToken(
            hash_token=hash_token, email=email, expira_em=expira_em, usado_em=None
        )
        self._criado_em[hash_token] = expira_em - EXPIRACAO_TOKEN

    def consumir(self, hash_token: str, agora: datetime) -> RegistroToken | None:
        registro = self.registros.get(hash_token)
        if registro is None or not token_valido(registro, agora):
            return None
        self.registros[hash_token] = RegistroToken(
            hash_token=registro.hash_token,
            email=registro.email,
            expira_em=registro.expira_em,
            usado_em=agora,
        )
        return registro

    def contar_na_janela(self, email: Email, desde: datetime) -> int:
        return sum(
            1
            for h, r in self.registros.items()
            if r.email.valor == email.valor and self._criado_em[h] >= desde
        )


@dataclass
class FakeRepositorioSessao:
    """sessao em memória: hash_sessao → (conta_id, expira_em)."""

    sessoes: dict[str, tuple[str, datetime]] = field(default_factory=dict)

    def criar(self, conta_id: str, hash_sessao: str, expira_em: datetime) -> None:
        self.sessoes[hash_sessao] = (conta_id, expira_em)

    def conta_de_sessao(self, hash_sessao: str, agora: datetime) -> str | None:
        entrada = self.sessoes.get(hash_sessao)
        if entrada is None:
            return None
        conta_id, expira_em = entrada
        return conta_id if agora < expira_em else None

    def invalidar(self, hash_sessao: str) -> None:
        self.sessoes.pop(hash_sessao, None)


@dataclass
class FakeEnviadorEmail:
    """Enviador fake: acumula os links enviados. `falhar=True` simula falha do provedor (→502)."""

    falhar: bool = False
    enviados: list[tuple[str, str]] = field(default_factory=list)  # (email, link)

    def enviar_magic_link(self, email: Email, link: str) -> None:
        if self.falhar:
            raise RuntimeError("falha simulada do provedor de e-mail")
        self.enviados.append((email.valor, link))
