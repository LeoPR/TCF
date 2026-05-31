# Sub-exp 01 — implementacao ColumnFeatures unificado

## Mudancas

### Novo modulo: `src/tcf/column_features.py`

```python
@dataclass(frozen=True)
class ColumnFeatures:
    n_rows: int
    n_unicas: int
    avg_len: float
    cardinality: float
    is_numeric: bool
    sample: tuple[str, ...]

def analyze_column(values: list[str], sample_size: int = 20) -> ColumnFeatures
```

Pre-pass O(N) unico, imutavel (`frozen=True`), shareable entre
heuristicas.

### Refator: `src/tcf/auto_min_len.py`

Duas APIs:
- **`detect_min_len_from_features(features, n_threshold=100)`** — recebe
  `ColumnFeatures` (pra callers com pipelines multi-heuristica)
- **`detect_min_len(values, n_threshold=100)`** — backward compat
  wrapper que chama `analyze_column(values)` internamente

### Modificacao: `src/tcf/encoder.py`

```python
features = analyze_column(values)
min_len = detect_min_len_from_features(features)
tokens, _ = processar(unicas, min_len=min_len)
```

Pipeline: 1 passada O(N) compartilhada para features; heuristica
detect_min_len recebe features ja' calculada. Output IDENTICO ao
pre-refactor.

## Validacao zero-risk

Reutilizando `experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/05-validacao-canonical-src-tcf/`:

| Camada | base (B) | new (B) | delta | RT |
|---|---:|---:|---:|---|
| **D1-D9 (M9 baseline 1615B)** | **1615** | **1615** | **+0** | **9/9 OK** |
| Adult + TPC-H 57 cols | **1,008,003** | **908,502** | **-99,501 (9.87%)** | **57/57 OK** |

**Outputs identicos ao pre-refactor** — confirma zero-risk.

Top wins continuam IDENTICOS:
- l_comment -29,647B (-18.18%)
- fnlwgt -22,238B (-36.78%)
- l_extendedprice -20,038B (-28.05%)
- dates -3,800/5,000B cada
- c_phone -4,149B (-12.26%)
- c_acctbal -2,668B (-15.40%)

## Beneficios futuros

1. **Reuso**: futuras heuristicas (detect_cadence canonical, T02-T07
   naturezas pre-tx) recebem mesma ColumnFeatures sem recalcular
2. **Imutabilidade**: `@dataclass(frozen=True)` evita mutacoes acidentais
3. **Testabilidade**: heuristica pura `detect_X_from_features` testavel
   sem precisar construir lista values

## Compatibilidade

- API publica `tcf.encode(values)` inalterada
- `detect_min_len(values)` backward compat preservado
- Output bytes-canonical EXATO igual ao pre-refactor
