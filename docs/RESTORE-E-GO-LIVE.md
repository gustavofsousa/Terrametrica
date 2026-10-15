# Terrametrica: Restore da Base e Go Live

**Estado:** 🔴 Bloqueado — esperando o TCP proxy
**Data:** 2026-10-01
**Progresso:** F1.9 ✅ verificado. O deployment 423f06d1 deu SUCCESS no Railway. Falta restaurar a base
real (92 MB) e fazer o smoke test.

---

## Por que só você pode fazer isso

- **TCP proxy:** ele expõe um serviço privado (PostGIS). O classificador de permissões do Claude Code
  negou a criação. Se você não autorizar, a IA não faz.
- **Domínio e Resend:** opcional agora, obrigatório quando o login voltar. São credenciais que só você
  tem.
- **Smoke test manual:** clicar no mapa e ler o resultado no navegador exige um humano.

---

## Sequência recomendada — cerca de 15 minutos seus

### ✅ Passo 1: Abrir o TCP proxy no PostGIS (2 min)

Sem este passo, a IA não leva a base para o Railway (o banco só tem rede privada).

WARNING: O TCP proxy expõe o banco à internet. Feche o proxy no Passo 3, logo depois do restore.

**Dashboard do Railway:**

1. Abra https://railway.com/project/ae12d54a-7523-4299-b375-a34c44296516.
2. Clique no serviço **PostGIS** (à esquerda).
3. Abra Settings → Networking → **TCP Proxy**.
4. Clique em "Create TCP Proxy" e aceite a porta `5432`.
5. Anote o host público, no formato `tcp-prod-1.up.railway.app:12345`.
6. Avise aqui que o proxy está pronto. A IA vê pelo MCP e faz o restore.

**Alternativa:** libere a permissão `mcp__railway__create-tcp-proxy` nas opções do Claude Code e peça de
novo. Então a IA cria o proxy sem o dashboard.

---

### ⏳ Passo 2: Restaurar a base (5–7 min, a IA faz)

Você não faz nada neste passo. Quando você avisar que o proxy está aberto, a IA roda:

```bash
# A IA roda isto (você não precisa digitar):
pg_dump "postgresql://terrametrica:terrametrica@localhost:5433/terrametrica" -Fc --no-owner --no-privileges \
  | pg_restore -d terrametrica -U terrametrica -h "tcp-prod-1.up.railway.app" -p 12345 -Fc
```

O dump contém:

- 14,664 lotes rurais SIGEF (RJ), com a Z-coordinate corrigida.
- 82,205 lotes urbanos de Niterói (SIGeo).
- 47,348 polígonos de Reserva Legal (CAR).
- 455 Unidades de Conservação.
- A versão `rj-2026-10-01` publicada (passou na guarda de 90%). Todas as geometrias estão
  reprojetadas e validadas, e as interseções estão materializadas.

**Tempo:** cerca de 3 min de upload + 2 min de restore = cerca de 5 min no total.

---

### ✅ Passo 3: Fechar o TCP proxy (1 min)

Quando a IA avisar "restore feito", faça isto:

1. Volte ao dashboard → serviço PostGIS → Networking → TCP Proxy.
2. Clique em "Delete" (ou "Disable").
3. Confirme.

Assim o banco volta a ficar só na rede privada, sem acesso de fora.

**Confirmação da IA:** ela roda uma query READ-ONLY no Railway para validar que a base chegou.

---

### ✅ Passo 4: Smoke test (3 min)

Abra https://web-production-198ab.up.railway.app no navegador:

1. **Página pública (`/cobertura.html`):** confirme que o mapa mostra Niterói e outros 86 municípios com
   SIGEF.
2. **Index (`/index.html`):** confirme que o mapa interativo abre sem login
   (`TERRAMETRICA_ACESSO_ABERTO=1`).
3. **Clique urbano:** dê zoom em Icaraí (Niterói) e clique num ponto. Confirme que o dossiê aparece em
   cerca de 0.2 s com:
   - `natureza: urbano`
   - `lote_id` que começa com `niteroi:`
   - `municipios: ["3301009"]` (Niterói = 3301009)
   - a atribuição ao SIGeo
   - o cruzamento com UC (se houver)
4. **Clique rural:** dê zoom numa área com SIGEF (por exemplo o norte do RJ) e clique. Confirme o dossiê
   rural com Reserva Legal e UC.

Se um destes 4 pontos falhar, a base não restaurou ou a restauração tem um bug. Avise, e a IA faz o
debug.

---

## Checklist pós-restore

- [ ] TCP proxy criado no PostGIS
- [ ] Aviso enviado: "proxy aberto em <host:porta>"
- [ ] Base restaurada pela IA
- [ ] Aviso "restore feito" recebido
- [ ] TCP proxy apagado
- [ ] `cobertura.html` mostra Niterói
- [ ] Index abre sem login
- [ ] Clique urbano retorna dossiê de Niterói
- [ ] Clique rural retorna dossiê com Reserva Legal

---

## O que fica desligado por enquanto

- **E-mail (Resend):** `TERRAMETRICA_ACESSO_ABERTO=1` significa sem login. Para religar o login:
  1. Crie uma chave no Resend (https://resend.com).
  2. Defina `RESEND_API_KEY=<chave>` nas variáveis do serviço `web` no Railway.
  3. Apague `TERRAMETRICA_ACESSO_ABERTO` (ou defina `0`).
  4. Faça o redeploy.

- **Domínio customizado:** `terrametrica.xyz` é opcional. Se você quiser:
  1. Compre o domínio (se ainda não tem).
  2. Crie o CNAME que o Railway mostrar.
  3. Defina `TERRAMETRICA_BASE_URL=https://terrametrica.xyz` no Railway.

---

## Referências

- Especificação de deploy: [.specs/STATE.md](./../.specs/STATE.md) (AD-013, AD-014)
- Passos detalhados por CLI: [DEPLOY-PENDENCIAS.md](./DEPLOY-PENDENCIAS.md)
- Projeto Railway: terrametrica (`ae12d54a-7523-4299-b375-a34c44296516`)
- Serviço web: `bcb14d63-4529-4dcb-af17-6f117a571dd1`
- Serviço PostGIS: `6da3e965-18fe-4854-b4a8-8be23db63d34`
