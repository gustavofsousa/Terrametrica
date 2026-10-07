# Terrametrica: Restore da Base e Go Live

**Estado:** 🔴 Bloqueado — aguardando TCP proxy  
**Data:** 2026-10-01  
**Progresso:** F1.9 ✅ verificado; deployment 423f06d1 SUCCESS no Railway; falta restaurar base real (92 MB) + smoke test.

---

## Por que só você pode fazer isso

- **TCP proxy** expõe um serviço privado (PostGIS) — o classificador de permissões do Claude Code negou a criação. Você autoriza ou eu não faço.
- **Domínio e Resend** (opcional agora, obrigatório quando login voltar) — credenciais que só você tem.
- **Smoke test manual** — clicar no mapa e ler o resultado no navegador requer um humano.

---

## Sequência recomendada — ~15 minutos seu

### ✅ Passo 1: Abrir TCP proxy no PostGIS (2 min)

Sem este passo, não consigo levar a base pro Railway (rede privada só).

**Dashboard Railway:**
1. Vá para https://railway.com/project/ae12d54a-7523-4299-b375-a34c44296516
2. Clique no serviço **PostGIS** (no lado esquerdo)
3. Settings → Networking → **TCP Proxy**
4. Clique em "Create TCP Proxy", aceite a porta `5432`
5. Você verá um host público tipo `tcp-prod-1.up.railway.app:12345`
6. Me avise por aqui quando estiver pronto. Eu vejo pelo MCP e faço o restore.

**Opção alternativa:** se você achar mais fácil, libere a permissão `mcp__railway__create-tcp-proxy` nas opções do Claude Code e me peça de novo — eu crio sem passar pelo dashboard.

---

### ⏳ Passo 2: Restaurar base (5–7 min, eu faço)

Não precisa fazer nada. Quando você avisar que o proxy está aberto, eu rodo:

```bash
# Eu vou rodar isto (você não precisa digitar):
pg_dump "postgresql://terrametrica:terrametrica@localhost:5433/terrametrica" -Fc --no-owner --no-privileges \
  | pg_restore -d terrametrica -U terrametrica -h "tcp-prod-1.up.railway.app" -p 12345 -Fc
```

O dump tem:
- 14,664 lotes rurais SIGEF (RJ) com Z-coordinate corrigida
- 82,205 lotes urbanos de Niterói (SIGeo)
- 47,348 polígonos de Reserva Legal (CAR)
- 455 Unidades de Conservação
- Todas as geometrias reprojetadas, validadas e intersecções materializadas
- Versão `rj-2026-10-01` publicada (passou na guarda de 90%)

**Tempo:** ~3 min de upload + ~2 min de restore = ~5 min total.

---

### ✅ Passo 3: Fechar TCP proxy (1 min)

Quando eu avisar "restore feito", você:
1. Volte ao dashboard → serviço PostGIS → Networking → TCP Proxy
2. Clique em "Delete" (ou "Disable")
3. Confirme

Isto faz o banco voltar a ficar só na rede privada (nenhum acesso de fora).

**Eu confirmo:** rodo uma query READ-ONLY pro Railway pra validar que a base chegou.

---

### ✅ Passo 4: Smoke test (3 min)

Abra https://web-production-198ab.up.railway.app no navegador:

1. **Página pública (`/cobertura.html`)** deve mostrar mapa com Niterói e outros 86 municípios com SIGEF
2. **Index (`/index.html`)** abre o mapa interativo sem login (TERRAMETRICA_ACESSO_ABERTO=1)
3. **Clique urbano:** zoom em Icaraí (Niterói), clique em qualquer ponto → dossiê aparece em ~0.2s com:
   - `natureza: urbano`
   - `lote_id` começando com `niteroi:`
   - `municipios: ["3301009"]` (Niterói = 3301009)
   - Atribuição ao SIGeo
   - Cruzamento com UC (se houver)
4. **Clique rural:** zoom fora pra qualquer área com SIGEF (ex.: norte do RJ), clique → dossiê rural com Reserva Legal e UC

Se qualquer um destes 4 pontos falhar, a base não restaurou ou tem um bug na restauração. Avise e fico aqui pra debugar.

---

## Checklist pós-restore

- [ ] TCP proxy foi criado no PostGIS
- [ ] Avise: "proxy aberto em <host:porta>"
- [ ] Eu restoro a base
- [ ] Avise quando ver "restore feito"
- [ ] TCP proxy foi deletado
- [ ] Cobertura.html mostra Niterói
- [ ] Index abre sem login
- [ ] Clique urbano retorna dossiê de Niterói
- [ ] Clique rural retorna dossiê com Reserva Legal

---

## O que fica desligado por enquanto

- **Email (Resend):** `TERRAMETRICA_ACESSO_ABERTO=1` significa sem login. Para religar:
  1. Cria chave no Resend (https://resend.com)
  2. Set `RESEND_API_KEY=<chave>` na variável do Railway `web`
  3. Deleta `TERRAMETRICA_ACESSO_ABERTO` (ou seta pra "0")
  4. Redeploy
  
- **Domínio customizado:** `terrametrica.xyz` é opcional. Se quiser:
  1. Compra domínio (você tem?)
  2. Cria CNAME que o Railway mostrar
  3. Seta `TERRAMETRICA_BASE_URL=https://terrametrica.xyz` no Railway

---

## Referências

- Especificação de deploy: [.specs/STATE.md](./../.specs/STATE.md) (AD-013, AD-014)
- Passos detalhados de CLI (se preferir): [DEPLOY-PENDENCIAS.md](./DEPLOY-PENDENCIAS.md)
- Projeto Railway: terrametrica (`ae12d54a-7523-4299-b375-a34c44296516`)
- Serviço web: `bcb14d63-4529-4dcb-af17-6f117a571dd1`
- Serviço PostGIS: `6da3e965-18fe-4854-b4a8-8be23db63d34`
