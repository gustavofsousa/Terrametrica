# Lote Urbano de Niterói (F1.9) Specification

## Problem Statement

O dossiê só conhece lote rural (SIGEF). Clicar numa rua de Niterói devolve "sem lote". A fonte
urbana (SIGeo, AD-006) já foi verificada (Fase 0, slice 0.3): 82.375 lotes, EPSG:31983, licença
liberada com atribuição obrigatória. F1.9 ingere esses lotes e faz o clique resolver para um dossiê
urbano — a primeira coisa visual da região metropolitana do RJ.

## Goals

- [ ] Clique dentro de um lote de Niterói devolve dossiê com natureza `urbano`, área em m²,
      inscrição cadastral, logradouro e bairro.
- [ ] UC (e demais restrições comuns) cruzam o lote urbano; APP/Reserva Legal (CAR) nunca.
- [ ] Proveniência do lote urbano carrega a atribuição ao SIGeo e a página de cobertura mostra
      Niterói com a camada `lote_urbano`.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Malha municipal / "sem lote" com nome de município (F1.8, TD-001) | feature própria; o clique no vazio continua como hoje |
| Rio de Janeiro (capital) | AD-006: segundo município; fonte DATA.RIO ainda não verificada (F4.1) |
| Desenhar a geometria do lote no mapa | fora do escopo de F1.11 também; só o painel lateral |
| Resolver a sobreposição rural × urbano | já é o fluxo `Sobreposicao` (DOS-06); só passa a poder conter as duas naturezas |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Chave do lote | `niteroi:<objectid>` | `tx_insct` não é único (74.377 distintos em 82.375) nem sempre existe; o prefixo evita colisão com `lote_rural.id` (ambos entram em `intersecao_materializada`) | y — medido |
| Inscrição `"0"`/vazia | vira `NULL` | é o "sem inscrição" do SIGeo, não uma inscrição | y — medido (907 casos) |
| Feição sem polígono | não grava, conta em `feicoes_sem_geometria` | 170 de 82.375 vêm sem geometria; nunca some calado | y — medido |
| FK de `intersecao_materializada` → `lote_rural` | removida na migração 0007 | a tabela passa a servir dois tipos de lote; a integridade passa a depender do `INVARIANT` do prefixo | n — revisitar se surgir um 3º tipo (tabela de ligação por natureza) |
| Município | código IBGE `3303302` (texto) | mesma convenção de `lote_rural.municipios` (SIGEF usa código IBGE) | y |

## Requirements

| ID | Requirement |
| --- | --- |
| URB-01 | WHEN o clique cai dentro de um `lote_urbano` da versão publicada THEN `lote_em` SHALL devolver `LoteUrbano` com área em m² calculada sobre `geography`. |
| URB-02 | WHEN o clique cai em lote urbano e rural simultaneamente THEN SHALL devolver `Sobreposicao` com os dois candidatos. |
| URB-03 | WHEN a ingestão recebe `tx_insct` `"0"`/vazio ou número de porta `0` THEN SHALL gravar `NULL`/omitir, nunca o placeholder. |
| URB-04 | WHEN a ingestão recebe feição sem polígono THEN SHALL não gravar e contar no relatório. |
| URB-05 | WHEN uma UC intersecta o lote urbano THEN `intersecoes_de` SHALL devolvê-la; APP/Reserva Legal SHALL NOT ser materializadas para lote urbano. |
| URB-06 | WHEN a camada é ingerida THEN a proveniência SHALL citar "SIGeo Niterói" (atribuição da licença). |
| URB-07 | WHEN `semear_cobertura` roda THEN SHALL declarar `lote_urbano` com dado para Niterói. |
| URB-08 | WHEN `publicar_versao` roda THEN a guarda de 90% SHALL incluir `lote_urbano` (mesmo ponteiro atômico, AD-008). |

## Status

Execute concluído, **verificação independente pendente** (author ≠ verifier). Evidência do autor:
`tests/integration/ingestao/test_lote_urbano_niteroi.py` (URB-01/03/04/05/06/07) e
`tests/unit/ingestao/test_lote_urbano_niteroi.py` (URB-03). URB-02 e URB-08 sem teste dedicado ainda.
