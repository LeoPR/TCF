# Reference: os campos de `SideOutputs`

O contrato dos campos que o `encode(..., side_outputs=...)` e o `build_schema()`
preenchem. Para **como usar** o diagnóstico e o que cada padrão de número quer dizer,
veja a receita [`inspect-compression.md`](../how-to/inspect-compression.md).

**Pre-pass (por coluna):**

| Campo | Tipo | Significado |
|---|---|---|
| `column_features` | `ColumnFeatures \| None` | Features imutáveis extraídas em O(N): `n_rows`, `n_unicas`, `avg_len`, `cardinality`, `is_numeric`, `sample` |
| `cadence_detected` | `bool \| None` | True = heurística de cadence disparou (padrão repetido detectado) |
| `cadence_info` | `dict \| None` | Detalhe: `rule_hit`, `reason`, `lengths`, `cardinality`, etc |
| `min_len` | `int \| None` | Comprimento mínimo dos substrings (auto-detectado via heurística) |

**OBAT (por coluna):**

| Campo | Tipo | Significado |
|---|---|---|
| `obat_log` | `str \| None` | Log detalhado do shaping OBAT (prefixos/sufixos extraidos) |
| `obat_used_hint` | `bool \| None` | True = processado com hint, False = canonical |

**HCC (por coluna):**

| Campo | Tipo | Significado |
|---|---|---|
| `hcc_trace` | `str \| None` | Trace do detector de composições HCC (iterações de busca) |
| `hcc_rede` | `str \| None` | Rede final de atoms + compositions após HCC |
| `seq_rle_runs` | `list[dict]` | RLE runs detectados (vazio se nenhum) |

**Bytes e multi-col:**

| Campo | Tipo | Significado |
|---|---|---|
| `body_bytes` | `int \| None` | Bytes do corpo (single-col); calculado por coluna em multi-col |
| `multi_info` | `dict \| None` | Info agregada multi-col: `n_rows`, `n_cols`, `total_bytes`, `header_bytes`, `body_bytes` |
| `per_col` | `dict[str, SideOutputs] \| None` | Ninhada: `per_col[colname]` tem SideOutputs de cada coluna |

## Ver também

- a receita: [`../how-to/inspect-compression.md`](../how-to/inspect-compression.md)
- os knobs do encode: [`encode-knobs.md`](encode-knobs.md)
