# Deploy no Railway — o que só você pode fazer

Estado e decisão: `AD-013` em `.specs/STATE.md`. Projeto Railway: **terrametrica**
(`ae12d54a-7523-4299-b375-a34c44296516`), com os serviços `web` (API + front, mesma origem) e
`PostGIS`. URL pública: https://web-production-198ab.up.railway.app

Siga a ordem abaixo. Tempo total: cerca de 20 min seus.

## 1. Autorizar o acesso temporário ao banco — ~2 min · bloqueia tudo abaixo

A base (SIGEF + Reserva Legal + UC + lotes de Niterói) vai para o PostGIS do Railway por um **TCP
proxy público** no serviço `PostGIS`. O classificador de permissões do Claude Code negou a criação
(ela expõe um serviço). A decisão é sua.

WARNING: O TCP proxy expõe o banco à internet. Remova o proxy logo depois do restore.

Opção A (a mais curta): no dashboard do Railway → projeto `terrametrica` → serviço `PostGIS` →
Settings → Networking → **TCP Proxy**, porta `5432`. Depois avise. A IA faz o restore, **remove o
proxy** e confirma que o banco voltou a ficar só na rede privada.

Opção B: libere a ferramenta `mcp__railway__create-tcp-proxy` nas permissões do Claude Code e peça de
novo.

Por que o proxy é necessário: a ingestão grava feição a feição (centenas de milhares). Por isso a base
é montada localmente e restaurada por `pg_dump | pg_restore`. Por padrão, o banco no Railway só tem
rede privada.

## 2. Chave do Resend — ~5 min · só quando o login voltar (AD-014)

**Hoje o login está desligado** (`TERRAMETRICA_ACESSO_ABERTO=1` no `web`, AD-014). Você pode pular
este passo. Para religar o login, apague essa variável e siga os passos abaixo.

O login é por magic link. Enquanto `RESEND_API_KEY` não existe, a rota `/auth/solicitar` responde
**503**. Isso é de propósito: a rota nunca finge que enviou.

1. Em https://resend.com → API Keys, crie uma chave com a permissão *Sending access*.
2. No Railway, abra o serviço `web` → Variables e defina `RESEND_API_KEY=<a chave>`.
3. Sem domínio verificado, o remetente padrão (`onboarding@resend.dev`) só entrega **para o e-mail
   dono da conta Resend**. Isso basta para você testar. Para outras pessoas entrarem, verifique um
   domínio no Resend e defina `TERRAMETRICA_EMAIL_REMETENTE="Terramétrica <login@seudominio>"`.

## 3. Domínio próprio — opcional

O design de F1.11 cita `terrametrica.xyz`. Se você tem o domínio:

1. No serviço `web` → Settings → Networking → Custom Domain, crie no seu DNS o CNAME que o Railway
   mostrar.
2. Altere `TERRAMETRICA_BASE_URL` para `https://<seu domínio>`. O link do e-mail usa essa variável.

NOTE: O front e a API estão na mesma origem. Então **não** é necessário `app.`/`api.` nem cookie de
domínio pai.

## 4. Smoke test — ~3 min

1. Abra a URL pública. Confirme que `cobertura.html` mostra Niterói e os municípios com SIGEF.
2. Confirme que `index.html` abre direto no mapa (sem login). Se o login estiver ligado: peça o link,
   abra o e-mail e clique.
3. Clique numa rua de Niterói (por exemplo Icaraí). Confirme o dossiê urbano com a atribuição ao SIGeo.
