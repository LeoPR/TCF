"""TCF — Tabular Compact Format (v0.6).

API publica unificada (ADR-0014):

    from tcf import encode, decode, SideOutputs

    # Single-column (lista)
    text = encode(["abc", "abcd", "abcde"])
    values = decode(text)
    assert values == ["abc", "abcd", "abcde"]

    # Multi-column (dict)
    text = encode({"id": ["1", "2"], "name": ["a", "b"]})
    table = decode(text)
    assert table == {"id": ["1", "2"], "name": ["a", "b"]}

    # Side outputs opcional (debug, stats, schema)
    side = SideOutputs()
    text = encode(data, side_outputs=side)
    print(side.hcc_trace)        # detector iterations
    print(side.column_features)  # pre-pass features
    # ... etc

Encoder dispatcha por tipo (list vs dict). Decoder dispatcha pelo
shebang (`#TCF.6 M` -> multi, senao -> single). Self-describing.

## Componentes canonicos

- `tcf.core.online`: **OBAT** (Online Bidirectional Affix Tokenizer).
  Camada 1. Tokeniza strings via LCP + LCS. Codnome origem: `alg16`.
- `tcf.composicional.syntax`: **HCC** (Hierarchical Compositional
  Coding). Camada 2. Detector unificado + emit composicional. Codnome
  origem: `M8.A`.
- `tcf.composicional.hcc_seqrle`: HCC + seq-RLE near-identical (M10).
- `tcf.encoder` / `tcf.decoder`: API publica unificada.
- `tcf.multi`: implementacao interna multi-col + aliases deprecated.
- `tcf.side_outputs`: recipiente opcional pra debug/stats.

Ver `docs/algorithms/` para documentacao tecnica detalhada.

## Validacao

Single-column (M10 canonical, ADR-0011):
- D1-D9 sint: 1523B em 2981 raw = 51.1% ratio (RT 9/9)
- Real-world Adult+TPC-H 57 cols: -11.73% weighted vs M9 puro

Multi-column (M10 + ADR-0013, T-EXP-MULTI-COL-SCALING):
- D17a sint 13x4: 322B INVARIANT (preservado vs EXP-011)
- Real-world 9 tabelas (Adult + TPC-H tier 1+2, 136k linhas):
  -33.02% weighted vs raw, -31.46% vs single-col concat, RT 9/9

## Backward compat

- `encode_table` / `decode_table` permanecem como aliases DEPRECATED
  (emitem `DeprecationWarning`). Use `encode(dict)` / `decode(text)`.

Para historia: `experiments/lab/dirty/notas/historia-dirty-lab.md`.
"""

from tcf.decoder import decode
from tcf.encoder import encode
from tcf.multi import decode_table, encode_table  # deprecated aliases
from tcf.natures import SPEC_CPF, SPEC_CNPJ, TemplatedCheckedSpec
from tcf.schema import ColumnSchema, TableSchema, build_schema
from tcf.side_outputs import SideOutputs

__all__ = [
    "encode",
    "decode",
    "SideOutputs",
    "build_schema",
    "TableSchema",
    "ColumnSchema",
    # Natures (ADR-0015):
    "TemplatedCheckedSpec",
    "SPEC_CPF",
    "SPEC_CNPJ",
    # Deprecated (mantidos pra migracao):
    "encode_table",
    "decode_table",
]
