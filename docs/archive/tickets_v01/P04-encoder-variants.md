# P04 — Variantes do Encoder (EncoderConfig)

**Status:** CLOSED (3 numeric x 4 FK x 2 sorted = 24 variantes implementadas e testadas)  
**Tipo:** Implementação — extensão de `src/tcf/encoder.py`  
**Bloqueia:** H01 (bins_16), H04, H05, H06  

## Variantes a Implementar

### Numeric encoding
| Variant | Param | Comportamento |
|---------|-------|---------------|
| `raw_float` | (default) | `_fmt_num()` atual |
| `int_scaled` | `scale=100` | `int(val * scale)` |
| `bins_16` | `n_bins=16` | quantização uniforme; emite `# BINS col min=X max=Y n=16` |

### FK representation
| Variant | Param | Comportamento |
|---------|-------|---------------|
| `id_raw` | (default) | ID numérico bruto |
| `dict_separate` | `fk_mode="dict"` | Bloco `## DICT tabela col` antes da seção |
| `hint_comment` | `fk_mode="hint"` | Linha `> col ref tabela.nome → 1=Ana 2=Bruno` |
| `inline_resolved` | `fk_mode="inline"` | JOIN no encoder, emite nomes direto |

## Interface

```python
from dataclasses import dataclass

@dataclass
class EncoderConfig:
    numeric: str = "raw_float"   # "raw_float" | "int_scaled" | "bins_16"
    n_bins: int = 16
    int_scale: int = 100
    fk_mode: str = "id_raw"      # "id_raw" | "dict" | "hint" | "inline"
    include_sorted: bool = True   # emitir colunas [sorted]

def encode(meta_path, data_dir, config: EncoderConfig | None = None) -> str:
    ...
```

## CLI

```bash
tcf encode --meta data/metadata.json --data-dir data/ \
           --numeric bins_16 --fk-mode dict --out output/bins_dict.tcf
```

## Critério de Aceitação

- `encode(config=EncoderConfig(numeric="int_scaled"))` → valores como `250` em vez de `2.5`
- `encode(config=EncoderConfig(fk_mode="dict"))` → bloco `## DICT` antes de `## vendas`
- `encode(config=EncoderConfig(numeric="bins_16"))` → linha `# BINS vl min=1.0 max=12.4 n=16`
- H01 roundtrip passa para `raw_float` e `int_scaled`; bins_16 reporta RMSE esperado
