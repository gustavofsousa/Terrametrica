# Dossiê de Lote RJ — Context

**Gathered:** 2026-08-18
**Spec:** `.specs/features/dossie-lote-rj/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Painel web que, a partir de um clique no mapa do estado do Rio de Janeiro, identifica o lote
(rural em todo o estado, urbano no município do Rio), monta um dossiê com ficha técnica e
restrições ambientais e de risco cruzadas automaticamente, com fonte e data em cada campo, e
permite exportá-lo em PDF. Sem dado de proprietário nesta versão.

---

## Implementation Decisions

### Recorte do MVP
- Rural: todo o estado do RJ, via SIGEF (limite certificado) e CAR (declaração).
- Urbano: apenas o município do Rio de Janeiro, via DATA.RIO / IPP.
- Decisão delegada pelo usuário ("sem preferência"); escolhida por encaixar uma persona em cada camada.

### Camada de proprietário
- Fora do MVP. Papéis, verificação de credencial e log de auditoria são construídos em P2, sem dado pessoal.
- Nenhum nome, CPF ou CNPJ é persistido em qualquer tabela nesta versão.

### Usuários do P1
- Produtor rural e consultoria agro → camada rural, foco em Reserva Legal, APP e conformidade CAR.
- Corretor, incorporador e investidor → camada urbana do Rio, foco em restrição de uso e risco.
- As duas personas compartilham o mesmo dossiê; o que muda é qual seção pesa mais.

### Forma de entrega
- Painel web interativo como superfície principal.
- Exportação em PDF como artefato que circula (P2), carimbado com data, versão da base e ressalva de que não tem fé pública.

### Agent's Discretion
- Recorte do MVP e escolha do município urbano piloto foram delegados ("sem preferência") e decididos como acima, registrados como premissas no spec para você contestar.

### Declined / Undiscussed Gray Areas → Assumptions
Registrados na seção Assumptions & Open Questions do spec, com default e razão:
CRS canônico, frequência de reingestão, comportamento em divergência entre fontes, política de
acesso ao MVP, licença do MapBiomas, precisão declarada e a premissa de que não existe API
pública do ONR para terceiros.

---

## Specific References

- Referência mental do usuário: "o Google Maps das terras" — mapa limpo com uma camada de
  inteligência por cima, não um portal de GIS.
- Expectativa explícita do usuário: ao tocar um lote, o polígono acende e a ficha técnica aparece.
- Diferencial nomeado pelo usuário: os alertas de restrição ("20% deste terreno está em Reserva
  Legal", "este lote está em zona de inundação").

---

## Deferred Ideas

- Federar para outros estados (arquitetura preparada, sem ingestão).
- Valuation e preço estimado do lote.
- Integração registral automática via ONR, se e quando existir caminho documentado.
- Camada de rodovias do DNIT e outros cruzamentos de infraestrutura.
- Niterói como segundo município urbano.
- App móvel nativo.
