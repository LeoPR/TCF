---
title: T-CODE-RT-EDGES — 2 violações de RT em bordas (seq-RLE trailing-space + \n embutido)
status: open
priority: P1
created: 2026-07-04
updated: 2026-07-04
related:
  - src/tcf/composicional/hcc_seqrle.py
  - src/tcf/multi/core.py
  - experiments/lab/dirty/notas/diario/2026-07-04.md
  - tickets/T-CODE-EMPTY-FRAG-INDEX-RT.md
---

# T-CODE-RT-EDGES — violações do contrato lossless em bordas

**[probatório]** Achados da revisão crítica geral (2026-07-04, 6 lentes), **ambos confirmados por
repro própria** antes de registrar. O contrato nº1 do projeto (`decode(encode(x)) == x`) tem duas
violações de borda.

## Bug 1 — [P1] seq-RLE come whitespace final do template

```python
decode(encode(['a1 ', 'a2 ', 'a3 ']))   # => ['a1', 'a2', 'a3']  (espaços finais PERDIDOS)
# blob: '*3+1|a\\1 \n'  <- o espaço ESTÁ no blob; o decode o perde
```

- **Causa**: `HCCSeqRLE.decode` faz `raw.strip()` antes de expandir o marker seq-RLE
  ([hcc_seqrle.py:297](../src/tcf/composicional/hcc_seqrle.py)).
- **Histórico**: MESMA classe do bug corrigido em 2026-05-18 no decode do `syntax.py`
  ("NÃO strip", TPC-H trailing space) — o wrapper seq-RLE **reintroduziu** o strip.
- **Cobertura**: nenhum teste combina trailing-space + seq-RLE.
- **Fix proposto**: decode-only (detectar o marker sem strip, ou strip só pro teste de vazio e
  expandir sobre `raw`). **Byte-canonical-safe** (encode intocado) — mesmo padrão do fix
  T-CODE-EMPTY-FRAG-INDEX-RT. + pinar reproducer em `test_core_rt.py`.

## Bug 2 — [P1] `\n` embutido corrompe RT em silêncio

```python
decode(encode(['a\nb', 'c']))   # => ['a', 'b', 'c']  (sem erro; RT corrompido)
```

- **Causa**: a premissa "sem `\n` embutido" existe só em docstring (`_fallback_safe`,
  multi/core.py); o encoder público não valida.
- **Fix proposto**: validação barata na fronteira pública (`raise ValueError` por valor com `\n`,
  single e multi). A filosofia "dados felizes" (CLAUDE.md) diz *comprimir o que receber* — mas
  corromper silenciosamente não é comprimir; erro explícito preserva o contrato.
- **Alternativa** (se o owner preferir não-levantar): escapar/normalizar `\n` de forma reversível —
  mais caro, muda formato; a validação é o mínimo seguro.

## Critério de aceite

1. Bug 1: reproducer `['a1 ','a2 ','a3 ']` (e variantes: tab, espaço múltiplo, template só-espaço)
   com RT ok, pinado em test_core_rt.py; **D1-D9=1523B / D17a=303B / RW=89616B INALTERADOS**
   (fix decode-only).
2. Bug 2: `encode(['a\nb'])` e `encode({'c':['a\nb']})` levantam `ValueError` claro; suíte verde.
3. Fix toca `src/tcf` → **sob aprovação explícita do owner**.

## Updates

- **2026-07-04**: aberto (revisão crítica geral, lente núcleo/algoritmo; repros confirmadas).
