# framework/ — infra reutilizavel pelos experimentos clean

Helpers compartilhados pelos experimentos `clean/EXP-NNN-...`:
loaders de dataset, adapters de encoder, wrappers de compressor,
metricas, pipeline.

> **Origem**: ciclo v0.5 (LLM benchmark). Estavel desde ~2026-04-25.

## Componentes

| Modulo | Funcao |
|---|---|
| `datasets.py` | Loaders: MICRO, Adult, TPCH, sinteticos |
| `encoders.py` | Adapters: CSV, JSON, TCF (v0.5), TOON |
| `compressors.py` | Wrappers: gzip, brotli, zstd |
| `pipeline.py` | `simulate(rows, encoder, compress, transport)` |
| `metrics.py` | bytes, timing, roundtrip |

## Estado

Funcional para EXPs do ciclo v0.5. Para ciclo v0.6, ainda nao
integrado — o algoritmo do dirty (alg16 + M8.A) e' single-column
e nao foi wrappado em encoder adapter. Quando o welding pro `src/`
estiver completo, o adapter `encoders.tcf_v06` sera adicionado aqui.

## Uso

```python
from framework.pipeline import simulate
from framework.datasets import load_dataset
from framework.encoders import get_encoder

rows = load_dataset("Adult", n=1000)
encoder = get_encoder("tcf-v05", config={...})
result = simulate(rows, encoder, compress="gzip", transport="http")
```

## Dependencia

Independente do `src/tcf/` (que e' o package publico). Framework
e' uso INTERNO do lab.
