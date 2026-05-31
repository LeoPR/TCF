# Sub-exp 02 — validar IncrementalSyntax byte-canonical

## Setup

Compara bytes M8AVirtualRefsSyntax (canonical) vs
IncrementalSyntax (counter incremental) em D1-D9 + lineitem 1k/5k.

Criterio: bytes IDENTICOS (zero diferenca).

## Resultados

**Match**: 37/41

### Diffs (4)

| Source | Col | n_rows | canonical | incremental | delta |
|---|---|---:|---:|---:|---:|
| lineitem-1k | l_commitdate | 1000 | 8635 | 8634 | -1 |
| lineitem-5k | l_shipdate | 5000 | 36201 | 36233 | +32 |
| lineitem-5k | l_commitdate | 5000 | 35779 | 35787 | +8 |
| lineitem-5k | l_receiptdate | 5000 | 36139 | 36162 | +23 |
