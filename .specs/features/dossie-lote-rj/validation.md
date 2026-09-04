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

---

# Validação — Dossiê de Lote RJ (Fatia 3: CAR como camada de restrição — APP + Reserva Legal)

**Verdict:** ✅ PASS
**Escopo coberto (commits, não range genérico):** `4c0c6a5..b095437` (branch `main`) →
`a19cdd2` (docs/arquitetura) · `fe2f2f4` (design/tasks) · `fd1ebc5` (T16 `restricao_car.py`) ·
`cf11559` (T17 `intersecoes.py`) · `db94e68` (T18 `intersecoes_de` real) · `0a7ffcc` (T19 guarda
publicar) · `b095437` (T20 e2e). T15 (migração `0003`) entrou junto de `fd1ebc5`/`cf11559`.
**Gate:** `ruff check .` ✅ (All checks passed) · `mypy src` ✅ (strict, 25 arquivos, no issues) ·
`pytest tests/unit tests/integration -q` → **110 passed** ✅ (0 falhas, 59s).
**Ambiente:** Docker OK (`docker info` ✅) · rede OK (chamada real ao geobr em e2e executou) ·
venv `/home/gustavo/projects/08_Terrametrica/.venv`. Verificado a partir do checkout detached de
`b095437` no worktree isolado (o worktree nascia num commit pré-Fatia-3; Fatia 3 vive em `main`).
**Modo:** Verifier independente (author≠verifier honrado — não escrevi nenhuma linha desta fatia).

## Escopo

CAR como **camada de restrição** (papel P1): APP + Reserva Legal cruzadas contra o lote SIGEF.
Fecha a AC1 da story "Restrições ambientais" (`spec.md:105`): `RepositorioLotes.intersecoes_de`
deixa de devolver `[]` fixo. Entra: migração `0003` (`restricao` + `intersecao_materializada`),
`ingestao/restricao_car.py`, `ingestao/intersecoes.py`, `intersecoes_de` real, extensão da guarda
de publicação para `Camada.APP`/`RESERVA_LEGAL`, e prova e2e. **Fora (confirmado ausente):** CAR
"Perímetros dos imóveis" como 2ª geometria/identidade (P2, divergência SIGEF×CAR) — deferido.

**Reuso confirmado por evidência:** `dossie/montagem.py`, `geometria/regras.py` e
`dominio/modelos.py` **não aparecem** no `git diff 4c0c6a5..b095437 --stat` — zero mudança,
exatamente como `design.md` (Tech Decisions Fatia 3) afirma. `pct_do_lote`/`marginal` seguem
calculados na leitura por `montagem.py` via `geometria.classificar_intersecao` (DOS-08), não
materializados — schema `0003` grava só `area_intersecao_m2` (confirmado em
`0003_fatia3_restricoes_car.sql:19-24`).

## Cobertura por AC / "Done when" (spec-anchored, evidence-or-zero)

| Task / DOS / AC | Critério (spec/task) | Evidência (`file:line` + asserção) | ✓ |
| --- | --- | --- | --- |
| T15 schema | `restricao` + `intersecao_materializada` com tipos de design.md | `0003_fatia3_restricoes_car.sql:5-29` — ambas as tabelas criadas | ✅ |
| T15 CHECK tipo | vocabulário fechado `'app'`/`'reserva_legal'` | `0003_...sql:7` — `CHECK (tipo IN ('app', 'reserva_legal'))` | ✅ |
| T15 índice GiST | GiST em `restricao.geom` | `0003_...sql:16` — `CREATE INDEX ... USING GIST (geom)` | ✅ |
| T15 FK composta | `intersecao_materializada(lote_id, versao_base_id) → lote_rural(id, versao_base_id)` | `0003_...sql:27` — `FOREIGN KEY (lote_id, versao_base_id) REFERENCES lote_rural (id, versao_base_id)` | ✅ |
| T16 filtro `ind_status='AT'` (APP) | grava só ativas, `tipo='app'` | `test_restricao_car.py:93,95` — `len(linhas) == 4` (5 na fixture, 1 `CA` filtrada), `tipo == "app"` | ✅ |
| T16 filtro `AT` (Reserva Legal) | grava só ativas, `tipo='reserva_legal'` | `test_restricao_car.py:174-176` — `len(linhas) == 1` (2 na fixture, 1 `PE` filtrada), `== "reserva_legal"`, `feicoes_gravadas == 1` | ✅ |
| T16 correção geometria | feição inválida corrigida (não descartada), contada no relatório | `test_restricao_car.py:129,156` — `feicoes_corrigidas == 1`, geom `ST_IsValid True` | ✅ |
| T16 proveniência (DOS-10) | fonte `CAR/SICAR` + data para APP e RL | `test_restricao_car.py:146` (`fonte == "CAR/SICAR"`) + `:186-189` (RL, fonte+data) | ✅ |
| T17 intersecção plena | 1 linha com área correta (>0, plausível) | `test_intersecoes.py:106` — `area_m2 > 400_000.0` (SIGEF-001 × APP_AREA_AC) | ✅ |
| T17 intersecção marginal <1% (DOS-08) | linha materializada (classificação fica em montagem) | `test_intersecoes.py:128` — `0.0 < area_m2 < 10_000.0` (APP_ESCADINHA) | ✅ |
| T17 sem sobreposição | nenhuma linha (ausência, não área-zero) | `test_intersecoes.py:147` — `total == 0` (APP_RIO_ATE_10) | ✅ |
| T17 idempotência (DOS-26) | 2ª execução não duplica | `test_intersecoes.py:168-169` — `total_segunda_vez == total_primeira_vez`, `pares_materializados == 0` | ✅ |
| T18 `intersecoes_de` real (DOS-07) | devolve `IntersecaoBruta` reais, não `[]` | `test_repositorio_lotes_postgis.py:249-253` — `tipo is TipoRestricao.APP`, `area_intersecao.valor == 12345.0`, `grau_suscetibilidade is None` | ✅ |
| T18 isolamento entre lotes | lote sem intersecção → `[]` | `test_repositorio_lotes_postgis.py:281` — `intersecoes_de(lote_rj1, versao) == []` (intersecção só de RJ-2) | ✅ |
| T18 lista vazia preservada (T9) | nada materializado → `[]` (não erro) | `test_repositorio_lotes_postgis.py:223` — `== []` (teste T9 renomeado, não deletado) | ✅ |
| T19 guarda cobre APP/RL (DOS-25) | 1ª publicação com restrição passa a guarda | `test_publicar.py:280-281` — `publicada is True`, `_versao_apontada(APP) == "carguard-v1"` | ✅ |
| T19 <90% de APP reprova tudo (DOS-25/28) | qualquer camada reprova → publicação inteira rejeitada | `test_publicar.py:304,310` — `publicada is False`, `_versao_apontada(APP) == "carguard80-v1"` (mantém anterior) | ✅ |
| T20 e2e AC1 (DOS-07/08/10) | dossiê com `itens_restricao` (área+pct+marginal) sobre dado real | `test_dossie_e2e.py:172-181` — `len(itens_restricao) >= 2`, `item_app.pct_do_lote > 1.0`, `item_app.marginal is False`, `item_rl.pct_do_lote > 1.0` | ✅ |
| T20 e2e sem sobreposição | lote sem restrição → `itens_restricao == ()` | `test_dossie_e2e.py:195` — `resultado.itens_restricao == ()` | ✅ |
| spec AC1 (`spec.md:105`) | área + percentual em APP e Reserva Legal segundo CAR | provado fim-a-fim por T20 (`itens_restricao` com `pct_do_lote` para APP e RL); pipeline `ingerir_app_car → ingerir_reserva_legal_car → materializar_intersecoes → montar_dossie` | ✅ |
| spec AC5 (`spec.md:109`) | <1% → "toque marginal" | DOS-08 reusa `geometria.classificar_intersecao` (inalterado, `regras.py:53-63`, `LIMIAR_MARGINAL_PCT = 1.0`); T17 materializa o caso marginal (`test_intersecoes.py:128`) e T20 assere `marginal is False` no caso pleno | ✅ |

Contagens de "Done when" batidas: T16=6 (6 métodos), T17=4 (4), T18=3 (2 novos + 1 T9 renomeado),
T19=2 (2), T20=4 (2 novos + 2 T14 preservados). Baseline vs HEAD confirmado por `pytest
--collect-only`: **94 (`4c0c6a5`, checkout limpo) → 110 (`b095437`) = +16, nenhuma deleção
silenciosa** (T16 6 + T17 4 + T18 2 + T19 2 + T20 2 = 16).

## Sensor de discriminação (mutação comportamental em estado descartável)

Mutações aplicadas via script em `src/` do worktree isolado, medidas contra o teste guardião com
`PYTHONPATH` apontando pro `src/` do worktree, e revertidas com `git checkout -- <file>`. Árvore
final limpa (`git diff b095437 --stat` vazio; nenhum literal `MUTATION` remanescente).
**3/4 mutantes mortos; 1 sobrevivente (linha defensiva não coberta — ver Gaps).**

| # | Mutação | Efeito esperado | Teste guardião | Resultado |
| --- | --- | --- | --- | --- |
| M1 | `restricao_car.py`: remove filtro `ind_status=='AT'` | grava feições canceladas/pendentes | `test_restricao_car.py::test_grava_so_feicoes_ativas_*` (APP+RL) | `2 == 1`/`4` vs esperado, 2 failed ✅ morto |
| M2 | `intersecoes.py`: `WHERE area_m2 > 0` → `>= 0` | materializa toques de área zero | `test_intersecoes.py::test_sem_sobreposicao_nao_gera_linha` | **1 passed — SOBREVIVEU** ⚠️ |
| M3 | `intersecoes.py`: remove `ON CONFLICT ... DO NOTHING` | 2ª execução duplica → violação de PK | `test_intersecoes.py::test_rodar_duas_vezes_nao_duplica_linhas` | `UniqueViolation`, 1 failed ✅ morto |
| M4 | `publicar.py`: remove `Camada.APP`/`RESERVA_LEGAL` de `_CAMADAS_PUBLICADAS` | guarda deixa de cobrir CAR | `test_publicar.py::TestGuardaCobreRestricaoCar` | `publicada True` vs `is False`, 2 failed ✅ morto |

M1/M3/M4 matam os invariantes centrais da fatia: filtro de vigência do CAR, idempotência da
materialização (DOS-26) e cobertura da guarda de 90% (DOS-25). M2 sobreviveu — ver Gaps.

## Qualidade do gate

- `ruff check .` → All checks passed (0 violações).
- `mypy src` (strict) → no issues in 25 source files.
- `pytest tests/unit tests/integration -q` → **110 passed**, 0 failed (59s). Container PostGIS
  efêmero (`postgis/postgis:16-3.4`) via testcontainers, sequencial; e2e fez chamada real ao geobr
  (rede presente). Nota de ambiente: o pacote `terrametrica` é editable-install apontando pro `src/`
  do worktree `main` (mesmo commit `b095437` do checkout detached), então o código exercido é
  bit-a-bit o da Fatia 3; para o sensor, `PYTHONPATH` forçou o `src/` do worktree isolado.

## Gaps / observações (ranqueadas, não bloqueantes desta fatia)

1. **`area_m2 > 0` (defensivo) não coberto por teste — sensor M2 sobreviveu.** O guarda existe
   para descartar toques de fronteira com intersecção de área exatamente zero (`ST_Intersects`
   verdadeiro, `ST_Area(ST_Intersection)` = 0). Nenhum teste posiciona esse caso: o
   `test_sem_sobreposicao_nao_gera_linha` usa uma restrição **espacialmente disjunta** (excluída já
   pelo `ST_Intersects` do JOIN, independente do `> 0`). Impacto real: baixo — se relaxado, um toque
   de divisa geraria uma `IntersecaoBruta` com pct=0 (marginal) no dossiê, ruído, não dado errado.
   Nenhum "Done when" de T17 exige esse caso de borda (o critério é "sem sobreposição espacial não
   gera linha", que É coberto). Registrado como lacuna de cobertura defensiva, não regressão.
2. **DOS-11 "sem cobertura no município" ainda dispara mesmo com restrição real** — `cobertura`
   nunca é semeada por nenhuma ingestão (`TD-002`, pré-existente, aberto no design desta fatia). Não
   é regressão da Fatia 3; o e2e prova `itens_restricao` populado apesar disso.

Nenhum dos itens contradiz um "Done when" de T15-T20 nem a AC1/AC5 que a fatia se comprometeu a
provar.

## Sumário

**PASS ✅** — 6 tasks (T15-T20), gate verde (ruff 0, mypy 0, 110 passed / +16 vs baseline 94),
sensor 3/4 mortos (M2 sobrevivente = linha defensiva `area_m2 > 0` sem teste, impacto baixo). AC1
(área+% de APP e Reserva Legal) provada fim-a-fim; DOS-08 marginal reusa `geometria` inalterado;
`montagem.py`/`geometria`/`modelos` confirmados sem uma linha de mudança no diff.

---

## Fatia 4 — Seed de cobertura (TD-002 / AD-009) — Verificação independente

**Diff verificado:** `722835b..HEAD` (3 commits: `c36ac88` feat, `5243d54` e2e, `eb44d65` docs).
Verificador ≠ autor; cobertura re-derivada por mutação, evidência-ou-zero.

### Gate (saída observada)
- `ruff check src tests` → `All checks passed!`
- `mypy src` → `Success: no issues found in 26 source files`
- `pytest tests/integration/ingestao/test_cobertura.py tests/integration/test_dossie_e2e.py -q`
  → `10 passed in 13.53s` (5 cobertura + 5 e2e, PostGIS efêmero via testcontainers + geobr real).

### Âncoras de spec
- **DOS-11 honesto (inverso) — PASS.** `test_restricoes_ingeridas_aparecem_com_cobertura_e_proveniencia_honesta`
  (e2e, PostGIS real) prova que APP e Reserva Legal ingeridas NÃO aparecem em
  `camadas_sem_cobertura` e trazem `proveniencia` (`fonte="CAR/SICAR"`, `data_extracao=DATA_EXTRACAO_CAR`);
  e que UC/Inundação (não ingeridas) permanecem honestamente em `camadas_sem_cobertura`. Mutante A
  (`tem_dado true→false`) mata este par: sem o seed honesto o dossiê se contradiria.
- **AD-009 derivação — PARCIAL.** Municípios do produto `lote_rural.municipios` e camadas de
  `restricao.tipo` provados pelo dict exato de 4 linhas; `data_extracao` da proveniência da camada
  provado por datas distintas por camada (mutante E morto). DISTINCT-de-municípios, filtro
  INNER-JOIN (camada sem proveniência) e semântica de refresh do upsert NÃO exercitados (ver sensor).

### Sensor de discriminação (mutação em `cobertura.py`, revertida)
Alvo: `test_cobertura.py` (suíte rápida, mesma que cobre a SQL).

| # | Mutante | Resultado |
|---|---------|-----------|
| A | `true → false` em `tem_dado` | **MORTO** (test_semeia_produto) |
| E | `p.data_extracao → DATE literal fixa` | **MORTO** (test_semeia_produto + test_carimba) |
| B | `JOIN → LEFT JOIN proveniencia` (remove filtro sem-proveniência) | **SOBREVIVE** |
| C | remove `DISTINCT` do subselect de municípios | **SOBREVIVE** |
| D | `ON CONFLICT DO UPDATE → DO NOTHING` | **SOBREVIVE** |

Placar: 2 mortos / 3 sobreviventes. Análise dos sobreviventes:
- **B** — nenhum teste monta uma `restricao` SEM `proveniencia`; o INNER JOIN (razão-de-ser
  declarada na docstring: "sem data não se declara cobertura", distinção DOS-11 vs DOS-12) é
  não-provado. Severidade baixa: `restricao_car` sempre grava proveniência (INSERT incondicional),
  logo o caso não ocorre no pipeline atual — mas o filtro fica sem rede.
- **C** — dados de teste não têm dois lotes no mesmo município, então DISTINCT nunca deduplica.
  Impacto de correção baixo (o `ON CONFLICT` deduplica a tabela final de qualquer forma); só
  `linhas_semeadas` inflaria sem DISTINCT. Falta assert com lotes co-municipais.
- **D** — `test_idempotente` só verifica `len==4` e ausência de erro na 2ª rodada; NÃO prova que o
  `DO UPDATE` **atualiza** `data_extracao`/`tem_dado` quando a proveniência muda entre execuções.
  Gap real de correção (DOS-13): re-seed após nova data manteria data obsoleta com `DO NOTHING`.
  **Assert faltante:** re-rodar `semear_cobertura` após atualizar `proveniencia.data_extracao` e
  afirmar que a linha de `cobertura` passou a carregar a nova data.

### Veredito
**PASS ✅** para o objetivo central (DOS-11 honesto + derivação município×camada×data), gate verde,
mutantes A/E mortos. Ressalvas: 3 mutantes sobreviventes são gaps de precisão/borda (refresh do
upsert = maior deles), nenhum contradiz um "Done when" de T21-T22 nem regride Fatia 2/3.
Árvore limpa após reversão de todas as mutações (`git status` clean).

### Fix task T23 — mutantes D e B fechados (2026-09-04, pós-Verifier)
Loop fix→re-verify (bounded), dois testes novos em `test_cobertura.py`:
- **Mutante D (MORTO agora):** `test_reseed_atualiza_data_extracao_da_cobertura` — semeia, corrige
  `proveniencia.data_extracao`, re-semeia e afirma que a linha de `cobertura` carrega a nova data.
  Injeção de `DO NOTHING` faz o teste falhar (confirmado por observação, revertido).
- **Mutante B (MORTO agora):** `test_restricao_sem_proveniencia_nao_gera_cobertura` — `restricao`
  sem `proveniencia` ⇒ `linhas_semeadas == 0` e `cobertura` vazia. Injeção de `LEFT JOIN` faz o
  teste falhar (confirmado, revertido).
- **Mutante C — deliberadamente NÃO testado:** um assert de DISTINCT exercitaria a deduplicação do
  próprio `ON CONFLICT` do PostgreSQL, não a lógica do produto; `linhas_semeadas` é contador
  diagnóstico, não um outcome de spec. Registrado como escolha, não esquecimento.

Sensor pós-fix: 4 mortos / 1 sobrevivente-por-escolha (C). Gate: ruff 0, mypy strict 0,
`test_cobertura.py` 7 passed. Commit do fix: `a91604b`.
