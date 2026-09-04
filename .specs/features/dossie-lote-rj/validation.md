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

---

# Validação — Dossiê de Lote RJ (Fatia 2: adaptador PostGIS + ingestão SIGEF)

**Verdict:** ✅ PASS
**Escopo coberto (commits, não range genérico):** `7409f9f` (design/tasks) · `6bbc532` (T6) ·
`e7848b5` (T7) · `745f0a0` (T8) · `d62ef3d` + `195321a` (T9) · `1de5056` (T10) · `6f26078` (T11) ·
`1209f09` (T12) · `4fed269` (T13) · `fb27b20` (T14) · `a8e2037`/`2687fba` (docs). A sessão
concorrente (`autorizacao`/gate-jurídico-P2) foi explicitamente excluída — não avaliada.
**Gate:** `ruff check .` ✅ (All checks passed) · `mypy src` ✅ (strict, 23 arquivos, no issues) ·
`pytest tests/unit tests/integration -q` → **94 passed** ✅ (30 são de integração, exit 0).
**Ambiente:** Docker OK (`docker info` ✅) · rede OK (chamada real ao geobr em T11/T14 executou —
`ingerir_limite_rj` gravou 1 MULTIPOLYGON válido EPSG:4674).
**Modo:** Verifier independente (author≠verifier honrado — não escrevi nenhuma linha desta fatia).

## Escopo

Walking skeleton: schema PostGIS mínimo (6 tabelas), adapters reais dos *ports* `RepositorioLotes`/
`LimiteEstado` (T4, inalterados), ingestão de duas fontes (limite RJ via geobr; SIGEF via arquivo
local), publicação com guarda de 90% + swap atômico, e prova fim-a-fim que `montar_dossie` (T5, zero
mudança) roda sobre Postgres real. CAR, camada urbana, restrições e `intersecao_materializada`
ficam fora — confirmado ausentes.

**Desvio de escopo documentado (não penalizado):** `RepositorioLotesPostGIS.municipio_em` levanta
`NotImplementedError` citando TD-001, e `lote_rural.municipios` grava o código IBGE bruto do SIGEF
(ex. `3304557`) em vez do nome. Ambos registrados em `.specs/TECH-DEBT.md` (TD-001, status `open`,
com nota de 2026-09-03 sobre o `municipio_`). O ramo `SemLote` (DOS-04) não é testável contra o
adapter real nesta fatia — consequência esperada e documentada, não uma lacuna.

## Cobertura por AC / "Done when" (spec-anchored, evidence-or-zero)

| Task / DOS | Critério (spec/task) | Evidência (`file:line` + asserção) | ✓ |
| --- | --- | --- | --- |
| T6 infra | compose sobe PostGIS sem conflito de porta; 4 deps runtime + testcontainers; DEV-SETUP | `docker-compose.yml` (`image: postgis/postgis:16-3.4`, `5433:5432`) · `pyproject.toml:8-16` · `docs/DEV-SETUP.md` presente | ✅ |
| T7 schema | `CREATE EXTENSION postgis`; 6 tabelas EPSG:4674; `geom_car` nullable | `migracoes/0001_fatia2_sigef.sql:4` (extensão), `:29-41` (`lote_rural`, `geom_car` sem NOT NULL), 6 tabelas | ✅ |
| T8 migrar | 6 tabelas em banco vazio; idempotente; guarda de Docker | `test_migrar.py:53-62` (`TABELAS_ESPERADAS <= tabelas`), `:64-69` (extensão), `:71-81` (`quantidade == 1`) | ✅ |
| T9 `lote_em` (DOS-01) | encontra lote via `ST_Contains`; área/perímetro>0 | `test_repositorio_lotes_postgis.py:129-143` — `isinstance(LoteRural)`, `lote_id=="RJ-1"`, `area.valor>0`, `perimetro_m>0` | ✅ |
| T9 `Sobreposicao` (DOS-06) | dois lotes no ponto → `Sobreposicao` | `test_repositorio_lotes_postgis.py:145-157` — `isinstance(Sobreposicao)`, `{RJ-1,RJ-2}` | ✅ |
| T9 `intersecoes_de` | `[]` explícito (sem restrição ingerida) | `test_repositorio_lotes_postgis.py:172-183` — `== []` | ✅ |
| T9 `proveniencia_de` (DOS-10) | fonte+data carimbadas / `None` sem stamp | `test_repositorio_lotes_postgis.py:186-223` — `fonte=="SIGEF/INCRA"`, data; e `is None` | ✅ |
| T9 `cobertura_de` (DOS-11) | reflete `cobertura` semeada | `test_repositorio_lotes_postgis.py:226-255` — `INUNDACAO.tem_dado True`, `UC.tem_dado False` | ✅ |
| T9 `municipio_em` (TD-001) | `NotImplementedError` citando TD-001 | `test_repositorio_lotes_postgis.py:258-267` — `pytest.raises(NotImplementedError, match="TD-001")` | ✅ |
| T10 `contem` (DOS-05) | dentro True / fora False / borda False / vazio False | `test_limite_estado_postgis.py:88-125` — 4 asserções `is True/is False` | ✅ |
| T11 limite RJ (geobr) | 1 polígono válido EPSG:4674 via rede real | `test_limite_rj.py:74-100` — `feicoes_gravadas==1`, `ST_SRID==4674`, `ST_IsValid True`, `MULTIPOLYGON` | ✅ |
| T11 correção geometria (edge) | inválida corrigida, não descartada | `test_limite_rj.py:103-111` — bowtie inválido → `foi_corrigida True`, `is_valid` | ✅ |
| T12 SIGEF (DOS-10, AD-003) | 4 feições gravadas, `geom_car` null, EPSG:4674, proveniência | `test_sigef.py:73-97` (`geom_car is None`, `srid==4674`), `:118-135` (`fonte=="SIGEF"`) | ✅ |
| T12 feição inválida (edge) | corrigida e marcada, não descartada | `test_sigef.py:103-116` — `SIGEF-004` → `geometria_corrigida is True` (4 gravadas, 1 corrigida) | ✅ |
| T13 primeira publicação (DOS-25) | sem versão anterior sempre publica | `test_publicar.py:143-157` — `publicada is True`, ponteiros == v1, status `published` | ✅ |
| T13 guarda ≥90% | swap atômico, ponteiro→nova | `test_publicar.py:160-180` — 9/10 → `publicada True`, ponteiros==v2 | ✅ |
| T13 guarda <90% (DOS-25) | rejeita, mantém anterior | `test_publicar.py:183-205` — 8/10 → `publicada is False`, ponteiros==v1, status `draft` | ✅ |
| T13 atomicidade (DOS-28) | falha no meio do swap não deixa estado parcial | `test_publicar.py:208-241` — raise na 2ª camada → ambos ponteiros == atomic-v1 | ✅ |
| T14 e2e (DOS-01/10) | pipeline → dossiê real com proveniência | `test_dossie_e2e.py:114-128` — `isinstance(Dossie)`, `codigo_sigef=="SIGEF-001"`, `proveniencia[LOTE_RURAL].fonte=="SIGEF"`, `data_extracao` | ✅ |
| T14 e2e (DOS-05) | fora do RJ → `ForaDoRJ` sobre dado real | `test_dossie_e2e.py:130-138` — `isinstance(ForaDoRJ)` | ✅ |

Contagens de "Done when" batidas: T8~3 (3), T9~6 (7 métodos de teste), T10~4 (4), T11~3 (3),
T12~5 (6), T13~4 (4), T14~2 (2). Nenhuma deleção silenciosa; totais ≥ estimativas das tasks.

## Sensor de discriminação (mutação comportamental em estado descartável)

Cada mutação aplicada via script em arquivo committado, medida, e revertida com
`git checkout -- <file>`. Árvore real intacta ao final (só as modificações da sessão concorrente
em `spec.md`/`design.md`/`pendencias-humano.md` permanecem — não são desta validação).
**3/3 mutantes mortos, 0 sobreviventes.**

| Mutação | Efeito esperado | Teste guardião | Resultado |
| --- | --- | --- | --- |
| `_mapear_situacao`: `if False` (CERTIFICADA nunca → certificado) | perde mapeamento de situação | `test_sigef.py::TestMapearSituacao::test_certificada...` | `certificado`→`em_analise`, 1 failed ✅ morto |
| `publicar.py`: `LIMIAR_GUARDA 0.90→0.0` (guarda neutralizada) | aceita versão <90% | `test_publicar.py::TestReingestaoForaDaGuarda` | `publicada True` vs `is False`, 1 failed ✅ morto |
| `publicar.py`: except `rollback()`→`commit()` (comita swap parcial) | deixa ponteiro em estado parcial | `test_publicar.py::TestAtomicidadeDoSwap` | ponteiro `atomic-v2` vs `atomic-v1`, 1 failed ✅ morto |

Os testes MATAM mutações que atingem exatamente os invariantes centrais da fatia: mapeamento de
situação SIGEF, guarda de 90% (DOS-25) e atomicidade do swap (DOS-28).

## Qualidade do gate

- `ruff check .` → All checks passed (0 violações).
- `mypy src` (strict) → no issues in 23 source files.
- `pytest tests/unit tests/integration -q -p no:cacheprovider` → 94 passed, 0 failed (41s).
  Integração isolada: 30 passed, exit 0. Container PostGIS efêmero (`postgis/postgis:16-3.4`) via
  testcontainers, sequencial; T11/T14 fizeram chamada real ao geobr (rede presente neste ambiente).

## Gaps / observações (ranqueadas, não bloqueantes desta fatia)

1. **DOS-04 (`SemLote`) sem cobertura de adapter real** — depende de `municipio_em`, que cai em
   TD-001 (`NotImplementedError`). Documentado e esperado nesta fatia; vira teste quando a malha
   municipal do IBGE for ingerida (Fatia 3+). Não é falha.
2. **`lote_rural.municipios` guarda código IBGE bruto**, não o nome do município (DOS-01 pede
   "município"). Documentado na nota de TD-001. O dossiê fim-a-fim exibe o código até a malha
   município→nome existir. Impacto de apresentação, dentro do escopo declarado do walking skeleton.
3. **DOS-26 (idempotência: mesmo lote 2× sob a mesma versão → mesmo dossiê)** não é asserido por um
   teste que chame `montar_dossie` duas vezes. O mecanismo (read-model versionado, AD-007) suporta
   a propriedade, mas ela não está provada por execução nesta fatia. Não consta de nenhum "Done
   when" de T6-T14 — fora dos critérios binários de fechamento desta rodada, registrado para a
   fatia que expuser a API (DOS-03/26/30).

Nenhum dos itens acima contradiz um "Done when" de T6-T14 nem um DOS que esta fatia se comprometeu
a provar. Fatia 2 fecha em PASS.

## Sumário

**PASS ✅** — 9 tasks (T6-T14), gate verde (ruff 0, mypy 0, 94 passed / 30 integração), sensor
3/3 mortos. Desvios de escopo (municipio_em / nome de município) documentados em TD-001; DOS-04 e
DOS-26 fora dos critérios binários desta fatia.
