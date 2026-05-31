---
title: Sub-exp 04 — Decisao e welding
type: sub-experiment
status: closed
tags: [tcf, bug-fix, decision, welding]
created: 2026-05-19
updated: 2026-05-19
parent: 2026-05-18-canonical-parser-robustness
hypothesis: H-FIX-03 vence (separator heuristico)
---

# Sub-exp 04 — Decisao e welding

## Comparativo

| Metric | Canon | Opcao A (escape) | **Opcao B (separator)** |
|---|---|---|---|
| Sub-exp 01 RT | 7/10 | **10/10** | **10/10** |
| D1-D9 M9 baseline | 1615B | 1615B (==) | 1615B (==) |
| customer.c_comment bytes | 35203 (FAIL) | 35319 (+116, OK) | **35210 (+7, OK)** |
| Mudancas no canonical | encoder + decoder | **encoder only** | encoder only |
| Bytes adicionais | em cada `,` literal | so' em ref->lit ambiguo | — |

## Decisao: Opcao B (separator heuristico)

**Vencedora**: H-FIX-03 (Opcao B — separator `*` em ref→lit
quando lit comeca com `,` ou `~`).

**Razao**:
1. Mesmo poder corretivo (todos casos failavam → OK)
2. Mesma preservacao de M9 (1615B inalterado)
3. **MUITO menor overhead em datasets reais** (TPC-H customer.c_comment:
   +7B vs +116B do A)
4. Mudanca menos invasiva (so' encoder; decoder inalterado)
5. Robustez teorica equivalente (cobre `,` e `~` no contexto certo)

## Plano de welding

Aplicar em `src/tcf/composicional/syntax.py`, metodo `_emit_body`,
branch `if kind == 'lit'`:

```python
if kind == 'lit':
    if prev_type == 'lit':
        parts.append('*')
    elif prev_type == 'refs' and p[1] and p[1][0] in (',', '~'):
        # Bug fix 2026-05-19 (ADR-0007): separator pra prevenir
        # parser de consumir `,`/`~` como continuacao de ref mode
        parts.append('*')
    state['current_id'][0] += 1
    ...
```

## Validacao multi-camada (pos-welding obrigatoria)

| Camada | Esperado |
|---|---|
| EXP-007 (D1-D9 byte-canonical) | 1615B inalterado |
| EXP-010 (delta-aware 20 datasets) | RT 20/20 OK, bytes inalterados ou +N |
| EXP-011 (multi-col D17a) | RT OK, bytes ~inalterados |
| EXP-012 (Adult Census) | RT 4/4 OK, bytes ~inalterados |
| EXP-013 (TPC-H) | RT melhora — esperamos pelo menos customer.c_comment passar |
| Sub-exp 01 cases via canonical | 10/10 OK (era 7/10) |

## See also

- [ADR-0007](../../../../docs/adr/0007-comma-in-literals-bug.md)
- [Sub-exp 01](../01-reproducao-minima/)
- [Sub-exp 02](../02-opcao-A-escape-virgula/)
- [Sub-exp 03](../03-opcao-B-separator-heuristico/)
