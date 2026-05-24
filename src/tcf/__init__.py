"""TCF — Tabular Compact Format (v0.6).

API publica:

    from tcf import encode, decode                    # single-column
    from tcf import encode_table, decode_table        # multi-column

    # single-column
    tcf_text = encode(["abc", "abcd", "abcde"])
    values = decode(tcf_text)
    assert values == ["abc", "abcd", "abcde"]

    # multi-column
    table = {"id": ["1", "2", "3"], "name": ["a", "b", "c"]}
    tcf_text, info = encode_table(table)
    decoded = decode_table(tcf_text)
    assert decoded == table

## Componentes canonicos

- `tcf.core.online`: **OBAT** (Online Bidirectional Affix Tokenizer).
  Camada 1 do TCF. Tokeniza strings via LCP + LCS contra anteriores.
  Codnome de origem: `alg16` (intocado de M0/online.py do dirty lab).
- `tcf.core.syntax_base`: interface `Syntax` (encode + decode).
- `tcf.composicional.syntax`: **HCC** (Hierarchical Compositional
  Coding). Camada 2 do TCF. Detector unificado + emit composicional
  (`~` cria ref auto-nomeado, `,` concat efemero). Codnome de origem:
  `M8.A`.
- `tcf.encoder` / `tcf.decoder`: API publica single-column.
- `tcf.multi`: API publica multi-column (ADR-0013, encode_table per-col
  + header `#TCF.6 M`).

Ver `docs/algorithms/` para documentacao tecnica detalhada de cada
camada (OBAT, HCC, TCF-format).

## Validacao

Single-column (M10 canonical, ADR-0011):
- D1-D9 sint: 1523 bytes em 2981 raw = 51.1% ratio (RT 9/9)
- Real-world Adult+TPC-H 57 cols: -11.73% weighted vs M9 puro

Multi-column (M10 + ADR-0013, T-EXP-MULTI-COL-SCALING):
- D17a sint 13x4: 322B (= EXP-011 baseline)
- Real-world 9 tabelas (Adult + TPC-H tier 1+2, 136k linhas):
  -33.02% weighted vs raw, -31.46% vs single-col concat, RT 9/9

## Estado v0.6

Single-column + multi-column canonical. Para historia do desenvolvimento,
ver `experiments/lab/dirty/notas/historia-dirty-lab.md`.

Ciclo v0.5 (formato columnar com RLE/dict para LLM benchmark) em
`old/tcf/` — acessorio ao foco atual.
"""

from tcf.decoder import decode
from tcf.encoder import encode
from tcf.multi import decode_table, encode_table

__all__ = ["encode", "decode", "encode_table", "decode_table"]
