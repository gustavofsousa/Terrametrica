# Arquitetura — estado atual

Snapshot de engenharia. Descreve o que existe em `src/terrametrica/` hoje (Fatia 2 fechada,
AD-007 handoff em `.specs/STATE.md`), não o que está planejado — onde algo é planejado e ainda
não implementado, o diagrama diz isso explicitamente.

**Decisão que molda tudo abaixo (AD-007):** monolito Python modular, organizado por domínio, com
a **ingestão como entrypoint separado no mesmo repositório**. A ingestão nunca fica no caminho de
uma requisição — ela materializa um *read-model* versionado; o dossiê só lê o que já foi calculado.

---

## Visão geral de componentes

```mermaid
flowchart TB
    subgraph EXT["Fontes externas — fora do monolito"]
        GEOBR["geobr / IBGE<br/>malha estadual RJ"]
        SIGEFWEB["SIGEF · INCRA<br/>export manual via login GOV.BR"]
        CARWEB["CAR<br/>export manual, captcha — nao ingerido ainda"]
        SIGEO["SIGeo Niteroi<br/>Feature Service ArcGIS — nao ingerido ainda"]
    end

    subgraph ING["ingestao/ — entrypoint separado, nunca no caminho de request (AD-004/007)"]
        LimiteRJ["limite_rj.py<br/>ingerir_limite_rj()"]
        Sigef["sigef.py<br/>ingerir_sigef()"]
        ValidGeom["validacao_geometria.py"]
        Publicar["publicar.py<br/>publicar_versao()<br/>guarda 90% + swap atomico"]
    end

    subgraph DOM["dominio/ — vocabulario ubiquo, zero I/O"]
        Modelos["modelos.py<br/>value objects e unioes fechadas"]
    end

    subgraph DOS["dossie/ — nucleo de negocio"]
        Montagem["montagem.py<br/>montar_dossie()"]
        PortasDos["portas.py<br/>RepositorioLotes, LimiteEstado Protocol"]
    end

    subgraph GEO["geometria/"]
        RegrasGeo["regras.py<br/>classificar_intersecao, avaliar_divergencia"]
    end

    subgraph AUTH["autorizacao/ — gate juridico P2, AD-002"]
        RegrasAuth["regras.py<br/>avaliar_acesso_registral"]
        ServicoAuth["servico.py<br/>solicitar_dado_registral, promover_conta"]
        PortasAuth["portas.py<br/>RepositorioContas, LogAuditoria Protocol"]
    end

    subgraph PERS["persistencia/ — adapters reais"]
        Conexao["conexao.py"]
        Migrar["migrar.py"]
        RepoPG["repositorio_lotes_postgis.py"]
        LimitePG["limite_estado_postgis.py"]
    end

    subgraph DB["PostgreSQL + PostGIS 16-3.4 — Docker, porta 5433"]
        Tabelas["versao_base, ponteiro_publicado<br/>limite_estado, lote_rural<br/>proveniencia, cobertura"]
    end

    HTTP["HTTP / FastAPI<br/>planejado em AD-007 — ainda nao implementado"]

    GEOBR --> LimiteRJ
    SIGEFWEB -. export local shapefile .-> Sigef
    LimiteRJ --> ValidGeom
    Sigef --> ValidGeom
    LimiteRJ --> Publicar
    Sigef --> Publicar
    Publicar --> Tabelas

    Modelos -.-> PortasDos
    Modelos -.-> Montagem
    Modelos -.-> RegrasGeo
    Modelos -.-> RegrasAuth
    Modelos -.-> ServicoAuth

    Montagem --> PortasDos
    Montagem --> RegrasGeo
    PortasDos -. implementado por .-> RepoPG
    PortasDos -. implementado por .-> LimitePG
    RepoPG --> Tabelas
    LimitePG --> Tabelas
    Migrar --> Tabelas
    Conexao --> DB

    ServicoAuth --> RegrasAuth
    ServicoAuth --> PortasAuth
    PortasAuth -. sem adapter real ainda so fake em memoria .-> FakeAuth["tests/fakes/autorizacao_fake.py"]

    CARWEB -. Fatia 3 .-> ING
    SIGEO -. Fatia 3 .-> ING

    HTTP -. chamaria .-> Montagem
```

**Leitura do diagrama:**

- **Setas cheias** = dependência de execução (import ou I/O real).
- **Setas tracejadas** = dependência de tipo (`dominio/modelos.py`, sem I/O) ou relação declarada
  mas ainda não concretizada (HTTP planejado, CAR/SIGeo fora desta fatia).
- `dossie/portas.py` e `autorizacao/portas.py` são `Protocol` — a montagem e o serviço de
  autorização nunca importam `psycopg` ou `geopandas` diretamente. Isso é o que permite trocar o
  adapter fake (testes) pelo PostGIS real (produção) sem tocar a regra de negócio — provado por
  `tests/integration/test_dossie_e2e.py` (T14).
- **Não existe camada HTTP ainda.** `montar_dossie` e o serviço de autorização são chamados hoje
  só por testes. FastAPI está decidido (AD-007) mas não implementado — não há `main.py`, rota ou
  processo de servidor no repositório.
- **`autorizacao/` não tem adapter real.** Só o `Protocol` (`portas.py`) e um fake em memória
  (`tests/fakes/autorizacao_fake.py`). Não há tabela `conta` nem `entrada_auditoria` no schema
  Postgres — o gate jurídico está arquitetado (AD-002) mas a persistência dele é trabalho futuro.
- **CAR e SIGeo (camada urbana) não são ingeridos.** Só SIGEF (rural) tem pipeline real. `AreaM2`,
  `LoteUrbano` e a lógica de `LoteHit` já existem no domínio — a montagem já sabe lidar com lote
  urbano — mas não há linha em `ingestao/` nem tabela para ele ainda.

---

## Pipeline de ingestão e publicação

Os três passos rodam hoje via chamada direta de função (não há CLI nem agendador) — normalmente
disparados manualmente ou por um teste de integração/e2e.

```mermaid
sequenceDiagram
    participant Op as Operador (manual)
    participant LimiteRJ as ingerir_limite_rj
    participant Sigef as ingerir_sigef
    participant Publicar as publicar_versao
    participant DB as PostGIS

    Op->>LimiteRJ: chama com VersaoBase nova + conexao
    LimiteRJ->>LimiteRJ: geobr.read_state RJ 2025
    LimiteRJ->>LimiteRJ: corrigir_geometria, reprojetar EPSG 4674
    LimiteRJ->>DB: INSERT limite_estado (staging, sem commit)

    Op->>Sigef: chama com caminho do shapefile exportado
    Sigef->>Sigef: corrigir_geometria, garantir EPSG 4674
    Sigef->>DB: INSERT lote_rural por feicao (staging, sem commit)

    Op->>Publicar: chama com VersaoBase + conexao
    Publicar->>DB: conta feicoes novas por camada
    Publicar->>DB: le versao publicada anterior por camada
    alt guarda >= 90% em todas as camadas
        Publicar->>DB: UPSERT ponteiro_publicado por camada
        Publicar->>DB: COMMIT (swap atomico)
    else guarda reprovada em alguma camada
        Publicar-->>Op: publicacao rejeitada, ponteiro mantido
        Note over DB: nem commit nem rollback automatico -\norquestrador decide descartar staging
    end
```

Pontos que não são óbvios lendo o código isoladamente:

- `ingerir_limite_rj` e `ingerir_sigef` **nunca commitam** — quem orquestra decide o limite da
  transação. Isso é o que permite `publicar_versao` tratar limite + lote como uma unidade atômica.
- A guarda (`LIMIAR_GUARDA = 0.90`) é avaliada **por camada**, mas a decisão de publicar é única
  para a versão inteira: se qualquer camada reprovar, nenhuma é publicada — evita misturar um
  `limite_estado` novo com um `lote_rural` antigo.
- SIGEF não tem download programático (exige login GOV.BR humano) — `ingerir_sigef` lê de um
  shapefile já exportado, não da rede. CAR e SIGeo, quando entrarem (Fatia 3), seguem o mesmo
  padrão de porta de entrada por arquivo ou API, plugando em `publicar_versao` sem mudá-lo.

---

## Árvore de decisão do dossiê

```mermaid
flowchart TD
    Start(["Coordenada clicada no mapa"]) --> Q1{"LimiteEstado.contem?"}
    Q1 -- nao --> ForaRJ["ForaDoRJ<br/>fora da area de cobertura: apenas RJ"]
    Q1 -- sim --> Q2{"RepositorioLotes.lote_em"}
    Q2 -- nenhum poligono --> SemLote["SemLote<br/>municipio + cobertura declarada por camada"]
    Q2 -- dois ou mais poligonos --> Sobreposicao["Sobreposicao<br/>candidatos, exige escolha do usuario"]
    Q2 -- um lote --> Montar["monta o Dossie"]

    Montar --> Interseccoes["avalia intersecoes com restricoes esperadas<br/>rural: APP, Reserva Legal + comuns<br/>urbano: apenas comuns"]
    Interseccoes --> Classifica["classificar_intersecao<br/>marginal se menor que 1% do lote"]
    Classifica --> Cobertura["para cada camada esperada:<br/>tem_dado? tem proveniencia? esta desatualizada?"]
    Cobertura --> SemCobertura["sem_cobertura: municipio nao tem a camada"]
    Cobertura --> Ausente["ausente: camada sem carimbo nesta versao"]
    Cobertura --> Desatualizada["desatualizada: extracao ha mais de 90 dias"]
    Cobertura --> Dossie["Dossie completo<br/>lote, itens_restricao, proveniencia por campo, ressalva fixa"]
```

Esta é literalmente a árvore documentada no docstring de `dossie/montagem.py` — quatro ramos
(`ForaDoRJ`, `SemLote`, `Sobreposicao`, `Dossie`), guard clauses, um caminho óbvio, sem
`else` aninhado. `montar_dossie` não faz I/O: recebe `repo` e `limite` como `Protocol`
(injeção de dependência via `dossie/portas.py`).

---

## Gate jurídico (P2) — fronteira arquitetada, sem dado pessoal

```mermaid
flowchart TD
    Pedido(["solicitar_dado_registral chamado"]) --> Papel["RepositorioContas.papel_de(conta_id)"]
    Papel -- conta desconhecida --> Propaga["ErroValidacao propaga<br/>nenhuma entrada de log e criada"]
    Papel -- papel resolvido --> Avalia["avaliar_acesso_registral(papel)"]
    Avalia -- HABILITADO_JURIDICAMENTE --> Permitido["Permitido"]
    Avalia -- CONSULTA --> Negado["Negado"]
    Permitido --> Log["LogAuditoria.registrar<br/>CONSULTA_REGISTRAL, sempre grava"]
    Negado --> Log
    Log --> Retorna(["devolve ResultadoAcesso"])

    Promocao(["promover_conta chamado"]) --> Muda["RepositorioContas.promover<br/>papel = HABILITADO_JURIDICAMENTE"]
    Muda --> LogProm["LogAuditoria.registrar<br/>PROMOCAO: quem, quando, credencial"]
    LogProm --> RetornaConta(["devolve Conta atualizada"])

    Gate[["CAMADA_REGISTRAL_LIGADA = False<br/>constante, nao config externa"]] -.-> SecaoProp["estado_secao_proprietario<br/>sempre Indisponivel para qualquer papel"]
```

Regra de negócio central (AD-002, GATE-05): **toda decisão de acesso produz exatamente uma
entrada de auditoria antes de devolver o resultado** — permitida ou negada. O log é uma obrigação
síncrona: se `log.registrar` falhar, a exceção propaga e nenhum `ResultadoAcesso` é devolvido sem
o registro correspondente. `CAMADA_REGISTRAL_LIGADA` é hoje uma constante Python (`False`), não
uma config externa — nenhuma fatia do produto criou mecanismo de config ainda.

---

## Estratégia de testes

```mermaid
flowchart LR
    subgraph UNIT["tests/unit — regras puras, sem I/O, sem Docker"]
        FakeRepo["FakeRepositorioLotes<br/>FakeLimiteEstado"]
        FakeAuth["FakeRepositorioContas<br/>FakeLogAuditoria"]
        UnitTests["test_montagem, test_regras<br/>test_modelos, test_servico"]
        FakeRepo --> UnitTests
        FakeAuth --> UnitTests
    end

    subgraph INTEG["tests/integration — container PostGIS efemero por modulo"]
        TC["testcontainers<br/>postgis/postgis 16-3.4"]
        Migra["aplicar_migracoes roda no setup"]
        IntegTests["test_repositorio_lotes_postgis<br/>test_limite_estado_postgis<br/>test_migrar, test_sigef<br/>test_limite_rj, test_publicar"]
        TC --> Migra --> IntegTests
    end

    subgraph E2E["tests/integration/test_dossie_e2e.py"]
        Pipeline["ingerir_limite_rj real via geobr<br/>ingerir_sigef fixture sintetica<br/>publicar_versao guarda mais swap"]
        Adapters["RepositorioLotesPostGIS<br/>LimiteEstadoPostGIS reais"]
        MontagemReal["montar_dossie sem nenhuma mudanca"]
        Pipeline --> Adapters --> MontagemReal
    end

    Docker[["Docker daemon<br/>docker info precisa responder"]] -.-> TC
    Docker -.-> Pipeline
```

O e2e é a prova de que os *ports* isolam de verdade fake de real: `montar_dossie` não muda uma
linha entre `tests/unit` (fakes em memória) e `test_dossie_e2e.py` (adapters PostGIS reais) — só
o que é injetado muda.

---

## O que ainda não existe (para não ler o diagrama como se existisse)

| Item | Estado |
| --- | --- |
| Camada HTTP / FastAPI | Decidida (AD-007), zero código |
| Ingestão de CAR | Fora desta fatia — decisão explícita para provar o pipeline antes de somar fontes |
| Ingestão de SIGeo (Niterói, camada urbana) | Fase 0 confirmou acesso real (82.199 feições); sem código de ingestão ainda |
| Malha municipal IBGE | `municipio_em` levanta `NotImplementedError` — TD-001 em `.specs/TECH-DEBT.md` |
| Camadas de restrição (APP, UC, inundação, deslizamento, corpo d'água) | Modeladas no domínio; `intersecoes_de` sempre devolve `[]` — nenhuma foi ingerida |
| Adapter real de `autorizacao/portas.py` | Só fake em memória; sem tabela `conta`/`entrada_auditoria` no schema |
| CLI ou agendador de ingestão | Chamada de função direta, hoje só via teste |

Ver `.specs/STATE.md` para o log de decisões completo e o handoff atualizado.
