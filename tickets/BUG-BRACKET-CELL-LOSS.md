---
title: BUG-BRACKET-CELL-LOSS — célula string que é exatamente '[' ou ']' é PERDIDA silenciosamente
status: open
priority: P1
severity: R0
created: 2026-07-16
updated: 2026-07-16
gate: byte-canonical (toca HCC core — precisa aprovação + test_real_world_snapshots)
blocked-by: []
related:
  - src/tcf/composicional/syntax.py
  - tickets/BUG-SEQRLE-RANGE-EMPTY-B.md
  - tickets/T-REL-08-CLOSEOUT.md
---

# BUG-BRACKET-CELL-LOSS — '['/']' isolado some no round-trip

**[probatório, R0]** `decode(encode(x)) != x` — uma célula cujo valor é **exatamente** `[` ou `]`
(um único char) é **descartada silenciosamente** (corrupção SILENCIOSA, não crash). Satisfaz o
critério 1 do T-REL-08 (preempta). Pré-existente no CORE (codec PLANO single/multi-col, não só
hierarquia); descoberto pela auditoria adversarial do P2 (`wf_10194874-083`, furo #5, atribuição
correta ao L1). **Não é do P2** (number/bool nunca produzem essas strings).

## Repro MÍNIMO

```python
from tcf import decode, encode
decode(encode(["["]))          # -> []          (célula perdida!)
decode(encode(["[", "]"]))     # -> []          (as duas perdidas)
decode(encode(["a", "[", ";"])) # -> ["a", ";"]  (o '[' do meio some)
```

## Caracterização (medida)

| entrada | resultado |
|---|---|
| `["["]` / `["]"]` | **PERDE** (→ `[]`) |
| `["[", "x"]` / `["x", "["]` | **PERDE** o `[`/`]` |
| `["{"]` / `["}"]` | RT OK |
| `["[["]` / `["a["]` | RT OK (só o `[`/`]` ISOLADO some) |
| `["<", ">"]` | RT OK |

Só o char `[` ou `]` **sozinho** (célula de 1 char == `[`/`]`) some. `[`/`]` fazem parte da sintaxe
do corpo HCC (composições/refs); uma célula que é só isso é confundida com estrutura e sumida.

## Escopo / impacto

- **R0** (corrupção silenciosa no domínio aceito), **pré-existente e independente do P2**. Afeta o
  codec PLANO (`encode(list[str])`), portanto TODAS as colunas string do `.8H` (que reusa o L1).
- Os gates byte-canônicos atuais passam porque `[`/`]`-isolado não ocorre em D1-D9/retail/lineitem.
  Free-text real PODE ter uma célula `[` ou `]` isolada (raro, mas possível).
- **Fix toca o HCC core** (`syntax.py` — o parse que trata `[`/`]` como estrutura) → aprovação
  explícita + gate `test_real_world_snapshots.py` + re-pin (ADR-0024). NÃO consertar sem isso.

## Direção de fix (a validar)

Escapar/quotar a célula `[`/`]`-isolada na EMISSÃO (como o `*`/`^`-líder já são escapados no L1), ou
o parser distinguir `[`/`]` estrutural de conteúdo. Escolher por byte-custo + simplicidade. Mesma
família do `BUG-SEQRLE-RANGE-EMPTY-B` (conteúdo colide com sintaxe do corpo) — pensar juntos.

## Critério de aceite

- [ ] Repro mínimo vira teste red→green (+ a matriz de caracterização).
- [ ] `test_real_world_snapshots.py` verde (+ snapshot que exercite `[`/`]`-isolado).
- [ ] Baselines re-pinados se o wire mudar; aprovação arquivo-a-arquivo do owner (HCC core).
