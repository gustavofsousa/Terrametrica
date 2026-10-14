"""Semeadura de `cobertura` (município × camada) — Fatia 4 (AD-009), conjunto de municípios pela
malha municipal (AD-016, MUN-07).

Sem este passo, `dossie/montagem.py` lê `cobertura_de(municipio)` e, achando `None`, marca TODA
camada de restrição como "sem cobertura no município" (DOS-11) mesmo com o dado ingerido no estado
inteiro — o dossiê se contradiz. Este passo torna DOS-11 honesto.

Derivação, tudo em upserts SQL, sem loop Python:
- **municípios** = a tabela `municipio` da versão (os 92 do RJ). Todo município ganha uma linha por
  camada ingerida; `tem_dado = false` onde a camada não tem feição nele. Um código de lote que não
  está na malha não gera linha.
- **camadas** = as que a versão ingeriu: `restricao.tipo` DISTINCT, mais `lote_rural` e
  `lote_urbano` quando têm feição. Camada sem `proveniencia` não gera linha (sem data, não se
  declara cobertura).
- **tem_dado** de uma restrição = o município tem algum lote (rural ou urbano): as restrições
  estaduais cobrem todo município que contém um lote (AD-009). Das camadas de lote = o município
  tem feição dela.
- **data_extracao** = `proveniencia` da própria camada/versão (fonte única da data, AD-005).

Chamado depois de `materializar_intersecoes` e antes de `publicar_versao`, na mesma transação: a
cobertura só persiste se a versão publicar. Idempotente (`ON CONFLICT DO UPDATE`).
"""

import psycopg

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.tipos import RelatorioCobertura

_MUNICIPIOS_COM_LOTE = """
    SELECT DISTINCT unnest(municipios) AS codigo
    FROM lote_rural
    WHERE versao_base_id = %(versao)s
    UNION
    SELECT DISTINCT municipio FROM lote_urbano WHERE versao_base_id = %(versao)s
"""

_SEMEAR_COBERTURA = f"""
    INSERT INTO cobertura (municipio, camada, tem_dado, data_extracao)
    SELECT m.codigo, camadas.tipo,
           m.codigo IN ({_MUNICIPIOS_COM_LOTE}),
           p.data_extracao
    FROM municipio m
    CROSS JOIN (
        SELECT DISTINCT tipo FROM restricao WHERE versao_base_id = %(versao)s
    ) camadas
    JOIN proveniencia p
        ON p.camada = camadas.tipo AND p.versao_base_id = %(versao)s
    WHERE m.versao_base_id = %(versao)s
    ON CONFLICT (municipio, camada) DO UPDATE
        SET tem_dado = EXCLUDED.tem_dado, data_extracao = EXCLUDED.data_extracao
"""

# A própria camada de lote rural também é cobertura por município: sem esta linha a página pública
# diz "sem dado" de SIGEF em municípios que têm milhares de lotes (achado na carga real, F1.9).
_SEMEAR_COBERTURA_LOTE_RURAL = """
    INSERT INTO cobertura (municipio, camada, tem_dado, data_extracao)
    SELECT m.codigo, p.camada,
           m.codigo IN (
               SELECT DISTINCT unnest(municipios) FROM lote_rural WHERE versao_base_id = %(versao)s
           ),
           p.data_extracao
    FROM municipio m
    JOIN proveniencia p ON p.camada = 'lote_rural' AND p.versao_base_id = m.versao_base_id
    WHERE m.versao_base_id = %(versao)s
      AND EXISTS (SELECT 1 FROM lote_rural WHERE versao_base_id = %(versao)s)
    ON CONFLICT (municipio, camada) DO UPDATE
        SET tem_dado = EXCLUDED.tem_dado, data_extracao = EXCLUDED.data_extracao
"""

# F1.9: a própria camada urbana é cobertura por município — só Niterói tem (AD-006), e a página
# pública de cobertura precisa dizer isso, não esconder.
_SEMEAR_COBERTURA_LOTE_URBANO = """
    INSERT INTO cobertura (municipio, camada, tem_dado, data_extracao)
    SELECT m.codigo, p.camada,
           m.codigo IN (
               SELECT DISTINCT municipio FROM lote_urbano WHERE versao_base_id = %(versao)s
           ),
           p.data_extracao
    FROM municipio m
    JOIN proveniencia p ON p.camada = 'lote_urbano' AND p.versao_base_id = m.versao_base_id
    WHERE m.versao_base_id = %(versao)s
      AND EXISTS (SELECT 1 FROM lote_urbano WHERE versao_base_id = %(versao)s)
    ON CONFLICT (municipio, camada) DO UPDATE
        SET tem_dado = EXCLUDED.tem_dado, data_extracao = EXCLUDED.data_extracao
"""


def semear_cobertura(versao: VersaoBase, conexao: psycopg.Connection) -> RelatorioCobertura:
    """Semeia `cobertura` com uma linha por município da malha × camada ingerida na versão."""
    with conexao.cursor() as cursor:
        cursor.execute(_SEMEAR_COBERTURA, {"versao": versao.id})
        linhas = cursor.rowcount
        cursor.execute(_SEMEAR_COBERTURA_LOTE_RURAL, {"versao": versao.id})
        linhas += cursor.rowcount
        cursor.execute(_SEMEAR_COBERTURA_LOTE_URBANO, {"versao": versao.id})
        linhas += cursor.rowcount

    return RelatorioCobertura(versao_base_id=versao.id, linhas_semeadas=linhas)
