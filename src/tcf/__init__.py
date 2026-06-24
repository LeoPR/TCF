"""TCF — Tabular Compact Format (pré-1.0; multi-col default `#TCF.7`/0.7,
`#TCF.6` legado ainda lido — ADR-0024 versionamento pré-1.0).

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
shebang (`#TCF.6 M`/`#TCF.7 M` -> multi, senao -> single). Self-describing.

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

> Numeros abaixo sao probatorios: o TESTE mede, a prosa aponta. Guardioes
> byte-canonical: `tests/test_core_rt.py` + `tests/test_regression_v1_baseline.py`
> (baselines D1-D9/D17a), `tests/test_multi_col_rt.py` (multi-col),
> `tests/test_real_world_snapshots.py` (bytes reais; GATE de qualquer mudanca
> em pre-pass/OBAT/HCC). As % sao derivadas — ver o ADR citado em cada linha.

Single-column (M10 canonical, ADR-0011):
- D1-D9 sint: 1523B em 2981 raw = 51.1% ratio (RT 9/9)
  [1523B pinado em test_core_rt.py + test_regression_v1_baseline.py]
- Real-world Adult+TPC-H 57 cols: -11.73% weighted vs M9 puro
  [bytes em test_real_world_snapshots.py; % derivada, ADR-0011]

Multi-column (M10 + ADR-0013/0025, T-EXP-MULTI-COL-SCALING):
- D17a sint 13x4: 303B (0.7 default, V2-B); 322B = #TCF.6 legado (vs EXP-011)
  [303B/322B pinados em test_multi_col_rt.py + test_regression_v1_baseline.py]
- Real-world 9 tabelas (Adult + TPC-H tier 1+2, 136k linhas):
  -33.02% weighted vs raw, -31.46% vs single-col concat, RT 9/9
  [bytes em test_real_world_snapshots.py; % derivada, ADR-0013]

## Backward compat

Pré-1.0 (ADR-0024, git-as-compat): os aliases v0.6 `encode_table`/`decode_table`
foram APOSENTADOS (2026-06-24). Use `encode(dict)` / `decode(text)`.

Para historia: `experiments/lab/dirty/notas/historia-dirty-lab.md`.
"""

from tcf.decoder import decode
from tcf.encoder import encode
from tcf.natures import (
    SPEC_CPF, SPEC_CNPJ, SPEC_IP,
    TemplatedCheckedSpec, TemplatedPaddedSpec,
)
from tcf.pipeline import PipelineConfig
from tcf.schema import ColumnSchema, TableSchema, build_schema
from tcf.side_outputs import SideOutputs
from tcf.view import Filtered, LazyTCF, view  # camada read-only (A4, plano 0.8)

# Pré-1.0 (ADR-0024): minor acompanha o formato (#TCF.7 -> 0.7); o PATCH (.1) e'
# contador de release/correcao, DESACOPLADO do comportamento (nao muda a logica
# nem o byte-output canonical). Sem compat rigida entre minors de dev; git e' o
# mecanismo de reproducao. v1.0 = release solido futuro.
__version__ = "0.7.1"

__all__ = [
    "encode",
    "decode",
    "SideOutputs",
    "build_schema",
    "TableSchema",
    "ColumnSchema",
    # Natures (ADR-0015):
    "TemplatedCheckedSpec",
    "TemplatedPaddedSpec",
    "SPEC_CPF",
    "SPEC_CNPJ",
    "SPEC_IP",
    # Pipeline toggles (T-CODE-LAYERED-PIPELINE Fase 1):
    "PipelineConfig",
    # View lazy/consultavel read-only (A4, plano 0.8):
    "view",
    "LazyTCF",
    "Filtered",
]
