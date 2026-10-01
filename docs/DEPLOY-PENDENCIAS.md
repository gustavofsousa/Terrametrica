# Deploy no Railway — o que só você pode fazer

Estado e decisão: `AD-013` em `.specs/STATE.md`. Projeto Railway: **terrametrica**
(`ae12d54a-7523-4299-b375-a34c44296516`), serviços `web` (API + front, mesma origem) e `PostGIS`.
URL pública: https://web-production-198ab.up.railway.app

Ordem recomendada. Tempo total: ~20 min seu.

## 1. Autorizar o acesso temporário ao banco — ~2 min  ·  bloqueia tudo abaixo

Para levar a base (SIGEF + Reserva Legal + UC + lotes de Niterói) ao PostGIS do Railway preciso de
um **TCP proxy público** no serviço `PostGIS`. O classificador de permissões do Claude Code negou a
criação (expõe um serviço) — decisão sua, não minha.

Opção A (a mais curta): no dashboard do Railway → projeto `terrametrica` → serviço `PostGIS` →
Settings → Networking → **TCP Proxy**, porta `5432`. Depois me avise: eu faço o restore, **removo o
proxy** em seguida e confirmo que o banco voltou a ficar só na rede privada.

Opção B: libere a ferramenta `mcp__railway__create-tcp-proxy` nas permissões do Claude Code e me
peça de novo.

Por que não dá para evitar o proxy: a ingestão grava feição a feição (centenas de milhares), então a
base é montada local e restaurada por `pg_dump | pg_restore`. O banco no Railway só tem rede
privada por padrão.

## 2. Chave do Resend — ~5 min  ·  só quando voltar a exigir login (AD-014)

**Hoje o login está desligado** (`TERRAMETRICA_ACESSO_ABERTO=1` no `web`; AD-014) — pode pular
este passo. Para religar o login: apague essa variável e faça isto.

O login é por magic link e a rota `/auth/solicitar` responde **503** enquanto `RESEND_API_KEY` não
existe (de propósito: nunca finge que enviou).

1. https://resend.com → API Keys → criar chave com permissão *Sending access*.
2. No Railway: serviço `web` → Variables → `RESEND_API_KEY=<a chave>`.
3. Sem domínio verificado, o remetente padrão (`onboarding@resend.dev`) só entrega **para o e-mail
   dono da conta Resend** — suficiente para você testar. Para outras pessoas entrarem, verifique um
   domínio no Resend e defina `TERRAMETRICA_EMAIL_REMETENTE="Terramétrica <login@seudominio>"`.

## 3. Domínio próprio — opcional

`terrametrica.xyz` (citado no design de F1.11) — se você o tem: no serviço `web` → Settings →
Networking → Custom Domain, crie o CNAME que o Railway mostrar no seu DNS, depois altere
`TERRAMETRICA_BASE_URL` para `https://<seu domínio>` (o link do e-mail usa essa variável).
Front e API estão na mesma origem, então **não** precisa de `app.`/`api.` nem de cookie de domínio pai.

## 4. Smoke test — ~3 min

1. Abra a URL pública → `cobertura.html` mostra Niterói e os municípios com SIGEF.
2. `index.html` abre direto no mapa (sem login). Se o login estiver ligado: pedir link → e-mail → clicar.
3. Clicar numa rua de Niterói (ex.: Icaraí) → dossiê urbano com a atribuição ao SIGeo.
