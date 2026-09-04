# Pendências que exigem ação humana

> Itens da Fase 0 (e correlatos) que não dão para fechar por agente — exigem login, contato
> humano, decisão de negócio/jurídica, ou navegação manual em portal sem API. Atualizado conforme
> a Fase 0 avança; ver checklist completa em `docs/research/fontes-de-dados-rj.md`. Itens
> totalmente resolvidos (licença SIGeo, download SIGEF, download CAR) foram removidos daqui — o
> resultado deles fica registrado em `fontes-de-dados-rj.md` e `.specs/STATE.md`, não aqui.

## 1. Contatar ONR sobre API para terceiros — TRABALHO FUTURO

**Link:** [registrodeimoveis.org.br](https://www.registrodeimoveis.org.br/) (site do ONR — canal
de contato/atendimento fica lá)

**Status:** contato tentado, **sem resposta ainda**. Movido para trabalho futuro — não bloqueia
nada do MVP atual (a camada de proprietário já está fora de escopo por AD-002). Retomar quando
houver tempo/prioridade, sem prazo definido.
**O quê:** confirmar se o Operador Nacional de Registro (ONR/SREI) tem alguma via de integração
programática para consulta de certidão, ou se é 100% manual por portal.
**Por quê importa:** é o único caminho técnico-jurídico que poderia, no futuro, sustentar a camada
de proprietário. Sem isso confirmado, a camada de proprietário permanece bloqueada por design.

## 2. Validar a interpretação jurídica de AD-002 com um advogado — FAZER ANTES DA PUBLICAÇÃO PÚBLICA

**Status:** adiado de propósito — **não é bloqueio do MVP/desenvolvimento**, mas é
**pré-requisito obrigatório antes de publicar o produto publicamente** (lançamento, abrir para
usuários reais). Fica registrado aqui para não ser esquecido nessa fase.
**O quê:** AD-002 se apoia em leitura própria da Lei 6.015/73 art. 17 (publicidade registral) e da
LGPD sobre agregação de dado público. É uma leitura razoável, mas não é parecer jurídico.
**Por quê importa:** é a decisão que mais expõe o produto a risco regulatório se a camada de
proprietário for ligada um dia (ver `docs/produto/riscos.md`, risco jurídico alto).
**Ação:** revisão por advogado antes de qualquer publicação pública do produto. Sem link — é uma
consulta offline.

## 3. Push dos commits locais para o remoto

**Status:** política permanente, não pendência pontual — releio a cada rodada de trabalho.
**O quê:** eu nunca faço `git push` sem pedido explícito na sessão, mesmo que uma autorização
anterior tenha liberado um push específico (autorização não se estende automaticamente a commits
futuros).
**Ação:** avisar quando quiser publicar. Nenhum commit deste projeto até agora foi destrutivo — é
seguro autorizar a qualquer momento.

## 4. Verificação manual dos 15 municípios "Parcial"/"Ambíguo" (cobertura urbana)

**Status:** não urgente, não bloqueia o MVP (a fatia urbana atual é só Niterói). Fica registrado
para quando expandir a cobertura urbana virar prioridade.
**O quê:** o inventário dos 92 municípios está fechado (`docs/research/municipios-rj/`) — 0 com
download vetorial confirmado, 75 sem nenhuma fonte, e **6 "Parcial" + 9 "Ambíguo" (15 no total)**
que têm algum sinal de geoprocessamento mas sem export vetorial confirmado por pesquisa remota.
**Por quê importa:** são os únicos 15 com chance real de virar fonte de dado urbano além de
Niterói. **Macaé** é o mais promissor (portal GeoMacaé tem seção de shapefiles, não confirmado se
cobre lote).
**Ação sugerida:** abrir cada um dos 15 portais manualmente (ver lista e links em
`docs/research/municipios-rj/README.md`) e testar se existe export vetorial ou REST Service
ArcGIS oculto; para os que continuarem sem sinal, contato via LAI com a secretaria de
planejamento/fazenda do município.
