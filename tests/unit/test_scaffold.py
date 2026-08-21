"""Smoke test: prova que o pacote resolve no layout src/ (pythonpath correto)."""

import importlib


def test_pacote_terrametrica_importa() -> None:
    modulo = importlib.import_module("terrametrica")
    assert modulo.__doc__ is not None
