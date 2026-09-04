"""Adapter PostGIS do port `RepositorioLotes` (`dossie/portas.py`).

Implementa contra o schema real da Fatia 2 (`migracoes/0001_fatia2_sigef.sql`), que só
tem a camada `lote_rural` (SIGEF) — não há tabela de lote urbano nesta fatia, então este
adapter só produz `LoteRural`. `area`/`perimetro_m` do value object não existem como
colunas: são derivados de `geom_sigef` via `ST_Area`/`ST_Perimeter` sobre `geography`
(cálculo correto no elipsoide, não em graus).

`intersecoes_de` lê `intersecao_materializada JOIN restricao` (Fatia 3) — só `app`/`reserva_legal`
estão populados nesta fatia; as demais camadas de restrição (UC, inundação, deslizamento, corpo
d'água — INEA/ICMBio) ficam para fatias futuras, mesma tabela.

`municipio_em` levanta `NotImplementedError` — TD-001 (`.specs/TECH-DEBT.md`): resolver
uma coordenada em município exige a malha municipal do IBGE, fora do escopo desta fatia.
"""

from dataclasses import dataclass

import psycopg

from terrametrica.dominio.modelos import (
    AreaM2,
    Camada,
    CoberturaCamada,
    Coordenada,
    IntersecaoBruta,
    LoteHit,
    LoteRural,
    Proveniencia,
    SituacaoCertificacao,
    Sobreposicao,
    TipoRestricao,
    VersaoBase,
)

MENSAGEM_TD_001 = (
    "municipio_em não implementado nesta fatia — TD-001 (.specs/TECH-DEBT.md): "
    "resolver coordenada em município exige a malha municipal do IBGE, fora do "
    "escopo da Fatia 2 (só SIGEF)."
)

_SELECT_LOTE_NO_PONTO = """
    SELECT id, municipios, codigo_sigef, denominacao, situacao_certificacao,
           ST_Area(geom_sigef::geography) AS area_m2,
           ST_Perimeter(geom_sigef::geography) AS perimetro_m
    FROM lote_rural
    WHERE versao_base_id = %(versao)s
      AND ST_Contains(geom_sigef, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4674))
    ORDER BY id
"""

_SELECT_INTERSECOES_DO_LOTE = """
    SELECT r.tipo, r.nome, im.area_intersecao_m2, r.categoria, r.grau_suscetibilidade
    FROM intersecao_materializada im
    JOIN restricao r ON r.id = im.restricao_id AND r.versao_base_id = im.versao_base_id
    WHERE im.lote_id = %(lote_id)s AND im.versao_base_id = %(versao)s
    ORDER BY r.id
"""

_SELECT_PROVENIENCIA = """
    SELECT fonte, data_extracao, link_oficial
    FROM proveniencia
    WHERE camada = %(camada)s AND versao_base_id = %(versao)s
"""

_SELECT_COBERTURA = """
    SELECT camada, tem_dado, data_extracao
    FROM cobertura
    WHERE municipio = %(municipio)s
"""


@dataclass
class RepositorioLotesPostGIS:
    """Read-model do lote rural (SIGEF) contra o PostGIS real."""

    conexao: psycopg.Connection

    def lote_em(self, coord: Coordenada, versao: VersaoBase) -> LoteHit | Sobreposicao | None:
        with self.conexao.cursor() as cursor:
            cursor.execute(
                _SELECT_LOTE_NO_PONTO,
                {"versao": versao.id, "lon": coord.lon, "lat": coord.lat},
            )
            linhas = cursor.fetchall()

        candidatos = tuple(_lote_rural_de(linha) for linha in linhas)
        if not candidatos:
            return None
        if len(candidatos) == 1:
            return candidatos[0]
        return Sobreposicao(candidatos=candidatos)

    def intersecoes_de(self, lote: LoteHit, versao: VersaoBase) -> list[IntersecaoBruta]:
        with self.conexao.cursor() as cursor:
            cursor.execute(
                _SELECT_INTERSECOES_DO_LOTE,
                {"lote_id": lote.lote_id, "versao": versao.id},
            )
            linhas = cursor.fetchall()

        return [
            IntersecaoBruta(
                tipo=TipoRestricao(tipo),
                nome=nome,
                area_intersecao=AreaM2(area_m2),
                categoria=categoria,
                grau_suscetibilidade=grau_suscetibilidade,
            )
            for tipo, nome, area_m2, categoria, grau_suscetibilidade in linhas
        ]

    def proveniencia_de(self, camada: Camada, versao: VersaoBase) -> Proveniencia | None:
        with self.conexao.cursor() as cursor:
            cursor.execute(_SELECT_PROVENIENCIA, {"camada": camada.value, "versao": versao.id})
            linha = cursor.fetchone()
        if linha is None:
            return None
        fonte, data_extracao, link_oficial = linha
        return Proveniencia(fonte=fonte, data_extracao=data_extracao, link_oficial=link_oficial)

    def municipio_em(self, coord: Coordenada, versao: VersaoBase) -> str:
        raise NotImplementedError(MENSAGEM_TD_001)

    def cobertura_de(self, municipio: str) -> list[CoberturaCamada]:
        with self.conexao.cursor() as cursor:
            cursor.execute(_SELECT_COBERTURA, {"municipio": municipio})
            linhas = cursor.fetchall()
        return [
            CoberturaCamada(camada=Camada(camada), tem_dado=tem_dado, data_extracao=data_extracao)
            for camada, tem_dado, data_extracao in linhas
        ]


def _lote_rural_de(linha: tuple[str, list[str], str, str | None, str, float, float]) -> LoteRural:
    lote_id, municipios, codigo_sigef, denominacao, situacao, area_m2, perimetro_m = linha
    return LoteRural(
        lote_id=lote_id,
        municipios=tuple(municipios),
        codigo_sigef=codigo_sigef,
        situacao=SituacaoCertificacao(situacao),
        area=AreaM2(area_m2).em_hectares(),
        perimetro_m=perimetro_m,
        denominacao=denominacao,
    )
