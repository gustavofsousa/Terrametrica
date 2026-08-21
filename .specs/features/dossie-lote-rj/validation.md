# Validação — Dossiê de Lote RJ (Fatia 1: núcleo de domínio)

**Verdict:** ✅ PASS
**Diff coberto:** `04e5d66..7445455` (T1–T5)
**Gate:** `ruff check .` ✅ · `mypy src` (strict, 8 arquivos) ✅ · `pytest tests/unit -q` → **46 passed** ✅
**Modo:** fresh-eyes standalone (fallback do skill; sub-agente não disponível neste ambiente
não-interativo). Autor executou a validação — registrado como desvio do ideal autor≠verificador.

## Escopo

Fatia 1 é o núcleo de domínio puro (sem PostGIS, sem ingestão, sem egress `.gov.br`):
value objects, regras de geometria, ports e a árvore de decisão da montagem, testados com fake
em memória. As fatias de infra (adaptador PostGIS, ingestão versionada, camada urbana, API,
web, gate jurídico P2) permanecem bloqueadas na Fase 0 e fora deste escopo.

## Cobertura por AC (spec-anchored, evidence-or-zero)

| AC / regra | Resultado esperado (spec) | Evidência (`file:line` + asserção) | ✓ |
| --- | --- | --- | --- |
| DOS-02 lat/lon | rejeita fora de faixa com erro específico | `tests/unit/dominio/test_modelos.py:37` — `pytest.raises(ErroValidacao, match="latitude")` | ✅ |
| DOS-05 fora do RJ | "fora da área de cobertura: apenas RJ" | `test_montagem.py:90` — `resultado.mensagem == "fora da área de cobertura: apenas RJ"` | ✅ |
| DOS-04 sem lote | município + cobertura declarada | `test_montagem.py:98-101` — `municipio == "Maricá"`, `cobertura == tuple(coberturas)` | ✅ |
| DOS-06 sobreposição | lista candidatos e exige escolha | `test_montagem.py:105-106` — `isinstance(Sobreposicao)`, `candidatos == (RURAL, URBANO)` | ✅ |
| DOS-07/04-restr | intersecção como área+% (nunca sim/não) | `test_montagem.py:145-149` — `item.pct_do_lote == 50.0`, `item.area_intersecao` presente | ✅ |
| DOS-08 marginal <1% | marca "toque marginal" | `test_regras.py:22-40` (limiares 0.99/1.00/1.01) + `test_montagem.py:165-166` (`marginal is True`) | ✅ |
| DOS-10 proveniência | fonte + data por campo | `test_montagem.py:173-177` — `all(p.fonte and isinstance(p.data_extracao, date) ...)` | ✅ |
| DOS-11 sem cobertura | seção declara ausência | `test_montagem.py:189-191` — `UC in camadas_sem_cobertura`, `UC not in proveniencia` | ✅ |
| DOS-12 indisponível | dossiê parcial marcando a faltante | `test_montagem.py:199-201` — `DESLIZAMENTO in camadas_ausentes` | ✅ |
| DOS-13 >90 dias | "possivelmente desatualizada" | `test_montagem.py:210-219` — 91d marca, 90d não marca (boundary) | ✅ |
| Divergência SIGEF×CAR >5% | alerta, base SIGEF, nunca reconcilia | `test_regras.py:63-92` (limiares 4.9/5.0/5.1 + sinal ±) | ✅ |

Regra 1:1 com DOS: cada limiar tem teste dedicado nos valores exatos de borda. As camadas
esperadas por natureza de lote são fixadas no teste (não importadas da implementação), então
uma mutação da regra é detectável.

## Sensor de discriminação (mutação comportamental em estado descartável)

Cada falha injetada foi revertida após medir. **6/6 mutantes mortos, 0 sobreviventes.**

| Mutação | Efeito esperado | Resultado |
| --- | --- | --- |
| marginal `<` → `<=` (borda 1%) | quebra 1.00% plena | 1 failed ✅ morto |
| divergência `>` → `>=` (borda 5%) | quebra 5.00% sem alerta | 1 failed ✅ morto |
| divergência: inverter sinal (CAR−SIGEF) | quebra sinal da diferença | 2 failed ✅ morto |
| stale `>` → `>=` (borda 90d) | quebra 90d não-desatualizada | 3 failed ✅ morto |
| remover guard `ForaDoRJ` (DOS-05) | perde recusa fora do RJ | 3 failed ✅ morto |
| rural perde camadas do CAR (escopo DOS-11) | perde APP/RL esperadas | 2 failed ✅ morto |

> Nota operacional: o ciclo rápido mutar→`git checkout` deixou bytecode `.pyc` obsoleto uma vez
> (mtimes colidindo no mesmo segundo), produzindo 2 falhas fantasma numa árvore limpa. Resolvido
> limpando `__pycache__`; `pytest -p no:cacheprovider` confirma 46 passed com fonte intacta.

## Desvios registrados

- **Refinamento de contrato (T4→T5):** `RepositorioLotes.proveniencia_de` retorna
  `Proveniencia | None` (não `Proveniencia`), e foi acrescido `municipio_em(coord, versao) -> str`.
  Ambos exigidos para tornar DOS-12 e DOS-04 representáveis; a `tasks.md` subespecificava o port.
- **Enum extra `TipoLote`** e mapeamento `TipoRestricao.camada`: aplicam "make illegal states
  unrepresentable" do AGENTS.md, além dos 4 enums nomeados na task.
- **`hoje: date | None`** keyword em `montar_dossie`: injeta a data de referência de DOS-13 sem
  quebrar a assinatura posicional mandatada.
- **Smoke test no scaffold (T1):** um teste de import substitui "coleta 0 testes" para dar gate
  determinístico (exit 0) e provar a resolução do layout `src/`.

## Gaps / lições

Nenhum gap de cobertura. Nenhuma lição de falha a destilar (PASS limpo).
