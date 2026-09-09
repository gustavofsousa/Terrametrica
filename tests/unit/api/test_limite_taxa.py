"""Testes do limitador de cota em memória (T30, DOS-27). Puro, sem I/O.

Deriva do edge do spec ("IF uma conta exceder 100 consultas por hora THEN 429 e informar quando a
cota renova"): a 100ª passa, a 101ª barra com retry positivo, a janela desliza e libera após 1h,
e contas diferentes têm cotas independentes.
"""

from datetime import datetime, timedelta

from terrametrica.api.limite_taxa import Bloqueado, LimitadorEmMemoria, Permitido

AGORA = datetime(2026, 9, 8, 12, 0, 0)


class TestLimitadorEmMemoria:
    def test_as_primeiras_100_passam(self) -> None:
        limitador = LimitadorEmMemoria()

        resultados = [limitador.checar("conta-a", AGORA + timedelta(seconds=i)) for i in range(100)]

        assert all(isinstance(r, Permitido) for r in resultados)

    def test_a_101a_barra_com_retry_positivo(self) -> None:
        limitador = LimitadorEmMemoria()
        for i in range(100):
            limitador.checar("conta-a", AGORA + timedelta(seconds=i))

        resultado = limitador.checar("conta-a", AGORA + timedelta(seconds=100))

        assert isinstance(resultado, Bloqueado)
        assert resultado.retry_after_segundos > 0

    def test_retry_after_reflete_quando_a_primeira_vaga_renova(self) -> None:
        limitador = LimitadorEmMemoria()
        # 100 consultas todas em AGORA (mesmo instante): a janela renova exatamente em AGORA + 1h.
        for _ in range(100):
            limitador.checar("conta-a", AGORA)

        # 30 min depois, ainda bloqueada — faltam ~30 min (1800s) para a primeira vaga renovar.
        resultado = limitador.checar("conta-a", AGORA + timedelta(minutes=30))

        assert isinstance(resultado, Bloqueado)
        assert resultado.retry_after_segundos == 1800

    def test_janela_desliza_libera_apos_uma_hora(self) -> None:
        limitador = LimitadorEmMemoria()
        for _ in range(100):
            limitador.checar("conta-a", AGORA)

        # 1h e 1s depois, a primeira vaga já saiu da janela → passa de novo.
        resultado = limitador.checar("conta-a", AGORA + timedelta(hours=1, seconds=1))

        assert isinstance(resultado, Permitido)

    def test_uma_conta_bloqueada_nao_consome_vaga_de_outra(self) -> None:
        limitador = LimitadorEmMemoria()
        for i in range(100):
            limitador.checar("conta-a", AGORA + timedelta(seconds=i))

        resultado = limitador.checar("conta-b", AGORA)

        assert isinstance(resultado, Permitido)

    def test_bloqueio_nao_empurra_a_janela_indefinidamente(self) -> None:
        # Uma tentativa bloqueada não deve ser registrada — senão a janela nunca renovaria.
        limitador = LimitadorEmMemoria()
        for _ in range(100):
            limitador.checar("conta-a", AGORA)

        # Rajada de bloqueios ao longo da hora não empurra o limite_inferior.
        for m in range(1, 60):
            limitador.checar("conta-a", AGORA + timedelta(minutes=m))

        # Logo após 1h da PRIMEIRA consulta, deve liberar (as 100 originais saíram da janela).
        resultado = limitador.checar("conta-a", AGORA + timedelta(hours=1, seconds=1))
        assert isinstance(resultado, Permitido)
