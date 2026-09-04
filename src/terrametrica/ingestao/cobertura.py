"""Semeadura de `cobertura` (município × camada de restrição) — Fatia 4, fecha TD-002 (AD-009).

Sem este passo, `dossie/montagem.py` lê `cobertura_de(municipio)` e, achando `None`, marca TODA
camada de restrição como "sem cobertura no município" (DOS-11) mesmo com o dado ingerido no estado
inteiro — o dossiê se contradiz: mostra as intersecções de APP/Reserva Legal E declara APP/Reserva
Legal sem cobertura. Este passo torna DOS-11 honesto.

Derivação (AD-009), tudo num único upsert SQL, sem loop Python:
- **municípios** = `lote_rural.municipios` DISTINCT da versão — o único caminho de dossiê que
  consulta `cobertura_de` é o do lote achado, cujo município já vem do próprio `lote_rural`. Não
  depende da malha municipal do IBGE (TD-001 fica independente) nem de uma lista externa de códigos.
- **camadas** = `restricao.tipo` DISTINCT da versão — genérico: as camadas de restrição estaduais
  (APP/Reserva Legal hoje; UC/inundação/deslizamento/corpo-d'água do INEA/ICMBio depois) cobrem
  todo município que contenha um lote, então `tem_dado = true` para cada par (município, camada).
- **data_extracao** = `proveniencia` da própria camada/versão (fonte única da data, AD-005). Uma
  camada de restrição sem proveniência não gera linha de cobertura (o JOIN a descarta) — sem data,
  não se declara cobertura; na prática `restricao_car` sempre grava proveniência.

Chamado depois de `materializar_intersecoes` e antes de `publicar_versao`, na mesma transação: a
cobertura só persiste se a versão publicar. Idempotente (`ON CONFLICT DO UPDATE`).
"""

import psycopg

from terrametrica.dominio.modelos import VersaoBase
from terrametrica.ingestao.tipos import RelatorioCobertura

_SEMEAR_COBERTURA = """
    INSERT INTO cobertura (municipio, camada, tem_dado, data_extracao)
    SELECT lm.municipio, camadas.tipo, true, p.data_extracao
    FROM (
        SELECT DISTINCT unnest(municipios) AS municipio
        FROM lote_rural
        WHERE versao_base_id = %(versao)s
    ) lm
    CROSS JOIN (
        SELECT DISTINCT tipo FROM restricao WHERE versao_base_id = %(versao)s
    ) camadas
    JOIN proveniencia p
        ON p.camada = camadas.tipo AND p.versao_base_id = %(versao)s
    ON CONFLICT (municipio, camada) DO UPDATE
        SET tem_dado = EXCLUDED.tem_dado, data_extracao = EXCLUDED.data_extracao
"""


def semear_cobertura(versao: VersaoBase, conexao: psycopg.Connection) -> RelatorioCobertura:
    """Semeia `cobertura` marcando `tem_dado = true` para cada par (município do lote × camada
    de restrição) publicado nesta versão, com a data de extração da proveniência da camada."""
    with conexao.cursor() as cursor:
        cursor.execute(_SEMEAR_COBERTURA, {"versao": versao.id})
        linhas = cursor.rowcount

    return RelatorioCobertura(versao_base_id=versao.id, linhas_semeadas=linhas)
