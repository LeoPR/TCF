---
title: B-homonyms-key-collision — risco de colapsar homonimos em key elimination
type: bug
status: OPEN
priority: MEDIUM
created: 2026-05-09
origin: Observacao do user durante EXP-004c
see_also:
  - docs/workbench/research-notes/2026-05-09-homonimos-key-collision.md
  - docs/workbench/tickets/open/H-compression-v04-roadmap.md (Proposta I)
---

# Risco de colapsar homonimos em key elimination

## Problema

Datasets com PKs grau 2 (auto-increment) podem ter **multiplos rows com
mesmo valor "natural"** distinguidos apenas pela PK:

```
id=1, nome=Ana, idade=25
id=5, nome=Ana, idade=42   <- outra Ana
id=12, nome=Ana, idade=30  <- ainda outra
```

Se TCF eliminar `id` agressivamente e algum modo futuro **deduplicar
linhas**, perde a distincao.

## Status atual

**Nao eh bug ativo**. TCF v0.5 emite uma linha por row e nunca
deduplica linhas inteiras. Eliminate PK = decoder regenera ids 1..N,
cada linha preserva seus dados.

**Eh risco em mode futuro** que combine:
- Key elimination (Proposta I)
- Mais alguma deduplicacao (hipotetica, ainda nao desenhada)

## Acao

1. **Documentar comportamento seguro** quando Proposta I for implementada
2. **Adicionar testes** com homonimos propositais
3. **Marcar bug** se algum modo futuro introduzir deduplicate de linhas

## Criterio de aceite

- [ ] Quando Proposta I virar codigo: testes T1, T2, T3 do research-note passam
- [ ] Documentacao da Proposta I menciona o risco
- [ ] Nenhum modo de TCF deduplica linhas sem flag explicita

## Notas

Bug ainda nao manifesto. Registro preventivo.

Detalhes em [research-notes/2026-05-09-homonimos-key-collision.md](../../research-notes/2026-05-09-homonimos-key-collision.md).
