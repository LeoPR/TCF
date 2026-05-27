"""Pipeline toggle infrastructure (T-CODE-LAYERED-PIPELINE Fase 1).

Cada camada do funil TCF pode ser ligada/desligada declarativamente:

```python
from tcf import encode, PipelineConfig

# Default (current canonical M10)
text = encode(values)

# Ablation: disable seq-RLE (reverte M10 -> M9 comportamento)
text = encode(values, layers=PipelineConfig(hcc_seq_rle=False))

# Debug: skip pre-pass (sem cadence detection, min_len=3)
text = encode(values, layers=PipelineConfig(pre_pass=False))

# Performance: skip OBAT shape-preserve hint
text = encode(values, layers=PipelineConfig(obat_shape_preserve=False))
```

Filosofia:
- Default config = M10 canonical byte-canonical (zero mudanca)
- Cada toggle eh boolean simple (Fase 1)
- Online adaptive + per-layer marker no body = Fase 2 futura

Cf. nota arquitetural
`experiments/lab/dirty/notas/arquitetura-funil-camadas-2026-05-24.md`
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    """Toggle declarativo das camadas do pipeline TCF.

    Atributos (todos default = M10 canonical):
        pre_pass: aplicar analyze_column + detect_cadence + detect_min_len.
            False = pular pre-pass, usar defaults (cadence=False, min_len=3).
        obat_shape_preserve: usar `processar_with_hint` quando cadence ativa.
            False = sempre `processar` canonical, mesmo se cadence detected.
        hcc_seq_rle: aplicar post-process HCCSeqRLE (M10).
            False = usar so' M8AVirtualRefsSyntax (M9 puro, sem seq-RLE).

    NAO toggleable (sempre on, foundationals):
    - OBAT (tokenizer): camada 2 obrigatoria
    - HCC base (M8A): camada 3a obrigatoria

    Camada 0 (nature filter) tem param proprio `nature=`/`nature_per_col=`
    em encode(); nao precisa de PipelineConfig.
    """
    pre_pass: bool = True
    obat_shape_preserve: bool = True
    hcc_seq_rle: bool = True


# Default singleton — equivalente a config nao passada (M10 canonical)
DEFAULT_PIPELINE = PipelineConfig()
