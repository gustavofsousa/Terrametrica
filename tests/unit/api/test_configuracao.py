"""Configuração de deploy (AD-013): o ambiente decide envio de e-mail, link e cookie."""

from pathlib import Path

from terrametrica.api.configuracao import (
    BASE_URL_PADRAO,
    REMETENTE_PADRAO,
    configuracao_de,
)


def test_ambiente_vazio_cai_nos_padroes_de_dev_sem_envio_de_email() -> None:
    config = configuracao_de({})

    assert config.base_url == BASE_URL_PADRAO
    assert config.resend_api_key is None
    assert config.remetente_email == REMETENTE_PADRAO
    assert config.dominio_cookie is None  # mesma origem → cookie host-only
    assert config.acesso_aberto is False  # login obrigatório por padrão
    assert (config.diretorio_app / "index.html").is_file()


def test_variavel_vazia_conta_como_ausente() -> None:
    config = configuracao_de({"RESEND_API_KEY": "  ", "TERRAMETRICA_DOMINIO_COOKIE": ""})

    assert config.resend_api_key is None
    assert config.dominio_cookie is None


def test_base_url_perde_barra_final_para_o_link_nao_ter_barra_dupla() -> None:
    config = configuracao_de({"TERRAMETRICA_BASE_URL": "https://terrametrica.up.railway.app/"})

    assert config.base_url == "https://terrametrica.up.railway.app"


def test_ambiente_de_producao_e_lido_por_inteiro() -> None:
    config = configuracao_de(
        {
            "TERRAMETRICA_BASE_URL": "https://terrametrica.xyz",
            "RESEND_API_KEY": "re_teste",
            "TERRAMETRICA_EMAIL_REMETENTE": "Terramétrica <login@terrametrica.xyz>",
            "TERRAMETRICA_DOMINIO_COOKIE": ".terrametrica.xyz",
            "TERRAMETRICA_DIR_APP": "/srv/app",
        }
    )

    assert config.resend_api_key == "re_teste"
    assert config.remetente_email == "Terramétrica <login@terrametrica.xyz>"
    assert config.dominio_cookie == ".terrametrica.xyz"
    assert config.diretorio_app == Path("/srv/app")


def test_acesso_aberto_so_liga_com_valor_explicito() -> None:
    assert configuracao_de({"TERRAMETRICA_ACESSO_ABERTO": "1"}).acesso_aberto is True
    assert configuracao_de({"TERRAMETRICA_ACESSO_ABERTO": "true"}).acesso_aberto is True
    assert configuracao_de({"TERRAMETRICA_ACESSO_ABERTO": "0"}).acesso_aberto is False
    assert configuracao_de({"TERRAMETRICA_ACESSO_ABERTO": "talvez"}).acesso_aberto is False
