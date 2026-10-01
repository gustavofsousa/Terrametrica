"""Normalização dos campos do SIGeo Niterói (F1.9) — o que o dado real trouxe de sujeira."""

import pytest

from terrametrica.ingestao.lote_urbano_niteroi import normalizar_inscricao


@pytest.mark.parametrize("bruta", [None, "", "  ", "0", float("nan")])
def test_inscricao_vazia_ou_zero_do_sigeo_vira_none(bruta: object) -> None:
    assert normalizar_inscricao(bruta) is None


def test_inscricao_real_e_preservada_sem_espacos() -> None:
    assert normalizar_inscricao(" 1110560060 ") == "1110560060"
