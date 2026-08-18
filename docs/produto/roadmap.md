# Roadmap

Quatro fases. Cada uma entrega valor sozinha e destrava a seguinte. As datas são deliberadamente
ausentes: as dependências externas (confirmar fontes, contatar o ONR, inventariar municípios)
têm prazo que não controlamos.

---

## Fase 0 — Verificar as fontes (pré-requisito, sem entrega de produto)

Nada de ingestão antes disso. Hoje as fontes estão documentadas com nível de confiança, não
confirmadas por acesso real — o ambiente de desenvolvimento bloqueia HTTPS para hosts `.gov.br`.

- Baixar SIGEF do RJ e medir: número de feições, CRS, validade dos polígonos
- Baixar CAR de um município piloto e medir a sobreposição SIGEF × CAR
- Confirmar se DATA.RIO expõe camada de **lote** (não só quadra ou bairro), e em qual endpoint
- Confirmar licença do MapBiomas para uso comercial
- Contatar o ONR sobre existência e condições de API para terceiros

**Destrava:** todo o resto. Um "não" aqui muda o produto, não o cronograma.

Checklist completa em [`../research/fontes-de-dados-rj.md`](../research/fontes-de-dados-rj.md).

---

## Fase 1 — MVP: o dossiê

**Entrega:** clicar no mapa e receber o dossiê, com restrições cruzadas e proveniência.

- Camada rural em todo o RJ (SIGEF + CAR)
- Camada urbana no município do Rio
- Cruzamento com APP, Reserva Legal, unidades de conservação, inundação e deslizamento
- Fonte e data em cada campo, página de cobertura pública
- Painel web, conta autenticada, sem paywall

**Corresponde a:** as três histórias P1 do spec (DOS-01 a DOS-13, mais DOS-25, 26, 28, 29, 30).

**Prova ou refuta:** a tese de que o cruzamento vale mais que o dado. Se ninguém voltar uma
segunda vez, o problema não era esse.

---

## Fase 2 — O que faz o dossiê circular

**Entrega:** o dossiê sai do painel e vira artefato; a divergência entre fontes vira produto;
a estrutura de autorização nasce vazia.

- **Exportação em PDF** — carimbado com data, versão da base e ressalva de fé pública
- **Divergência SIGEF × CAR** — dois polígonos, diferença em hectares e percentual, alerta acima de 5%
- **Gate jurídico arquitetado** — papéis, verificação de credencial, log imutável de auditoria, **sem nenhum dado pessoal**

**Corresponde a:** as três histórias P2 do spec (DOS-14 a DOS-22, mais DOS-27).

**Por que o gate vem antes do dado:** construir autorização e auditoria depois significa
reescrever o sistema. Construir antes custa pouco e transforma a Fase 3 em ligar uma chave.

---

## Fase 3 — A camada registral (condicional)

**Só existe se a Fase 0 confirmar um caminho jurídico defensável com o ONR.**

Três desenhos possíveis, em ordem decrescente de valor e de risco:

| Desenho | Como funciona | Depende de |
| --- | --- | --- |
| Consulta viva | O app consulta o registro no ato, sob identidade do usuário habilitado, exibe e registra em log. Sem cache do conteúdo pessoal. | Existir integração do ONR para terceiros |
| Deep link | O app leva o usuário ao pedido de certidão no portal oficial, já preenchido com o imóvel identificado | Nada além do portal existir |
| Upload de certidão | O usuário anexa a certidão que ele mesmo obteve; o app extrai e cruza com o dossiê | Nada externo |

**O que nunca acontece, em nenhum desenho:** ingerir e servir uma base agregada de
"proprietário → imóveis". Ver [riscos.md](riscos.md).

---

## Fase 4 — Ampliação

Em ordem de custo crescente por unidade de valor:

1. **Niterói** como segundo município urbano — SIG municipal maduro, mercado relevante
2. **Inventário dos 92 municípios** — planilha de quem publica lote cadastral aberto; define se a camada urbana escala ou estaciona
3. **Camadas de infraestrutura** — rodovias do DNIT e afins, cruzamentos que hoje ninguém faz
4. **API para terceiros** — vender o motor para quem já tem sistema (banco, ERP agro, escritório)
5. **Federação para outros estados** — a arquitetura já trata a UF como dimensão explícita; o custo é ingestão e verificação, não redesenho

---

## Fora do roadmap, por decisão

| Item | Razão |
| --- | --- |
| Valuation e preço estimado | Exige base de transações que não temos e responsabilidade de laudo que não queremos |
| Emissão de documento com fé pública | Não somos cartório |
| Edição de dado público pelo usuário | Retificação cadastral é com o órgão que produziu o dado |
| App móvel nativo | Painel web responsivo cobre o uso previsto |
