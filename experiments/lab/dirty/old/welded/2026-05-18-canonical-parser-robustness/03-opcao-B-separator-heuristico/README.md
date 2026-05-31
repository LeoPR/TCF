---
title: Sub-exp 03 — Opcao B (separator `*` em ref->lit com `,`/`~`)
type: sub-experiment
status: active
tags: [tcf, bug-fix, hcc, fork, separator, comma]
created: 2026-05-19
updated: 2026-05-19
parent: 2026-05-18-canonical-parser-robustness
hypothesis: H-FIX-03 (separator heuristico encoder-only)
---

# Sub-exp 03 — Opcao B: separator heuristico

## Objetivo

Testar **Opcao B** do ADR-0007: encoder adiciona `*` separator
quando ref→lit transition AND lit comeca com `,` ou `~`. Decoder
inalterado.

## Mudanca proposta

Em `_emit_body`, branch `if kind == 'lit'`:

```python
if kind == 'lit':
    if prev_type == 'lit':
        parts.append('*')
    elif prev_type == 'refs' and p[1] and p[1][0] in (',', '~'):
        parts.append('*')
    ...
```

Sem mudanca no decoder, _escape_lit, ou em qualquer outro lugar.

## Vantagem teorica vs Opcao A

- Bytes adicionais APENAS em casos ambiguos (raros)
- Opcao A adiciona +1 byte pra CADA `,` em qualquer literal

## Trade-off

- Opcao B precisa de RAIZ DA LIT — pode introduzir bug se lit text
  for processado/transformado entre identificacao e emit
- Opcao A e' uniforme (todo `,` escapa, decoder reverte)

## Validacao

Mesmo plano sub-exp 02:
1. Sub-exp 01 cases
2. D1-D9 (M9 baseline)
3. TPC-H sample
