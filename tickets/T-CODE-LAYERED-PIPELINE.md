---
title: T-CODE-LAYERED-PIPELINE — Toggle infrastructure + online adaptive + fallback
status: open-fase-1-welded
priority: P3
created: 2026-05-24
updated: 2026-05-24
blocked-by: []
related:
  - experiments/lab/dirty/notas/arquitetura-funil-camadas-2026-05-24.md
  - docs/algorithms/TCF-format.md
  - src/tcf/pipeline.py
---

# T-CODE-LAYERED-PIPELINE — Toggle + online adaptive

## Contexto

Owner pediu (2026-05-24) arquitetura de camadas toggleaveis com
fallback online. Cada etapa do funil (filtro / pre-pass / OBAT /
HCC) deve poder ser:
- **Habilitada/desabilitada** explicitamente (debug, ablation)
- **Detectada online** durante streaming — se nao esta ajudando,
  fallback pra identity sem comprimir restante

Sintese arquitetural em
[`arquitetura-funil-camadas-2026-05-24.md`](../experiments/lab/dirty/notas/arquitetura-funil-camadas-2026-05-24.md).

## Hipotese / Objetivo

H1: Pipeline com toggle declarativo simplifica:
- Debug (skip camada X pra ver impacto isolado)
- Ablation studies cientificos
- Fallback automatico em datasets onde camada hurts

H2: Heuristica online (eval window de N values) detecta camada
ineficiente em streaming + reverte pra identity sem custo perda
significativa.

## Plano

### Fase 1 — Toggle infrastructure

```python
@dataclass
class LayerConfig:
    name: str
    enabled: bool = True
    options: dict = field(default_factory=dict)

class TCFPipeline:
    def __init__(self, layers: list[LayerConfig]):
        self.layers = layers

    def encode(self, data, side_outputs=None):
        for layer in self.layers:
            if not layer.enabled:
                continue
            data = self._apply(layer, data, side_outputs)
        return data
```

Camadas registraveis:
- `nature_filter` (camada 0)
- `pre_pass` (camada 1)
- `obat` (camada 2)
- `hcc` (camada 3a)
- `hcc_seq_rle` (camada 3b — sub-component)

### Fase 2 — Online adaptive

```python
class AdaptiveLayer:
    def __init__(self, base_strategy, eval_window=100, threshold=1.0):
        self.strategy = base_strategy
        self.eval_window = eval_window
        self.threshold = threshold
        self.bytes_in = 0
        self.bytes_out = 0
        self.fallback_active = False

    def process(self, value):
        if self.fallback_active:
            return value  # identity
        result = self.strategy.process(value)
        self.bytes_in += len(value)
        self.bytes_out += len(result)
        if self.bytes_in >= self.eval_window:
            ratio = self.bytes_out / self.bytes_in
            if ratio > self.threshold:
                self.fallback_active = True
        return result
```

### Fase 3 — Marker pra transicao on→off

Output indica transicao no body:
```
<dados-com-camada-X-ON>
*FALLBACK_X         ← marker mudando estado
<dados-sem-camada-X>
```

Decoder espelha — re-aplica/desaplica conforme marker.

### Fase 4 — Composicao com Encoder Manager (T-CODE-ENCODER-MANAGER)

Quando encoder manager paraleliza per-coluna, cada coluna pode ter
configuracao de camadas propria (schema_builder Fase 3 decide).

## Criterio de aceite

- [ ] LayerConfig dataclass + TCFPipeline implementados
- [ ] Toggle por camada funcional (test_layer_toggle.py)
- [ ] D17a INVARIANT 322B preservado com all-layers default
- [ ] Adaptive fallback funcional (test_adaptive_fallback.py)
- [ ] Marker syntax pra transicao on/off definido + ADR
- [ ] Integration com encoder manager (T-CODE-ENCODER-MANAGER P2)
- [ ] Schema builder consumer (T-CODE-SCHEMA-BUILDER Fase 3)

## Riscos

1. **Format change**: marker `*FALLBACK_X` muda body syntax — quebra
   M10 backward compat. Version bump TCF v0.7?
2. **Performance overhead**: per-value tracking (bytes_in/out) custa
   tempo. Pode ser desligado em production.
3. **Adaptive threshold tuning**: 1.0 conservador; mais agressivo
   (0.9) detecta cedo mas pode reverter prematuro.
4. **Toggle granularity**: per-camada (4 toggles) ou per-sub-strategy
   (hcc.seq_rle on/off independente)? Decisao pendente.

## Conexao

- [Arquitetura funil de camadas](../experiments/lab/dirty/notas/arquitetura-funil-camadas-2026-05-24.md)
- [T-CODE-ENCODER-MANAGER](T-CODE-ENCODER-MANAGER.md) — pre-requisito P2
- [T-CODE-SCHEMA-BUILDER](T-CODE-SCHEMA-BUILDER.md) — alimenta config camada 0

## Updates datados

### 2026-05-24 — abertura

Ticket aberto pos discussao arquitetural. Pre-requisitos
T-CODE-ENCODER-MANAGER (P2 Fases 2+) e T-CODE-SCHEMA-BUILDER (Fase 3)
ainda nao implementados. Implementacao adiada ate' base estiver pronta.

### 2026-05-24 — Fase 1 WELDED (minimal viable toggle)

Owner aprovou Fase 1 minimal apos pausa formal. Implementado:

**Novo modulo** `src/tcf/pipeline.py`:
```python
@dataclass(frozen=True)
class PipelineConfig:
    pre_pass: bool = True
    obat_shape_preserve: bool = True
    hcc_seq_rle: bool = True
```

3 toggles toggleaveis. Outras camadas (OBAT base, HCC M8A) sao
obrigatorias.

**API publica estendida**:
```python
from tcf import encode, PipelineConfig

# Default (M10 canonical inalterado)
text = encode(values)

# Ablacao: revert M10 -> M9 (sem seq-RLE)
text = encode(values, layers=PipelineConfig(hcc_seq_rle=False))

# Debug: skip pre-pass (sem cadence detection)
text = encode(values, layers=PipelineConfig(pre_pass=False))

# Ablacao: sempre processar canonical (sem shape-preserve hint)
text = encode(values, layers=PipelineConfig(obat_shape_preserve=False))
```

**Mudancas canonicas**:
- `src/tcf/pipeline.py` (novo) — PipelineConfig + DEFAULT_PIPELINE
- `src/tcf/encoder.py` — encode() aceita `layers=` param; _encode_column
  consulta cfg pra decidir pre_pass/obat/hcc
- `src/tcf/multi.py` — _encode_multi/_encode_columns_serial/parallel
  propagam cfg pra workers
- `src/tcf/__init__.py` — exporta PipelineConfig

**Validacao byte-canonical CRITICAL**:
- D17a 322B INVARIANT preservado com default
- D1-D9 byte-canonical preservado com default (test parametrized
  em test_pipeline_config.py)
- `encode(data)` == `encode(data, layers=PipelineConfig())` byte-identical
- 25 tests novos test_pipeline_config.py PASSAM
- Suite completa: 236 passed (+25 novos) + 1 xfailed + 1 pre-existing fail

**Comportamento ablacao**:
- D17a sem seq-RLE: 403B (vs 322B M10) — 25% maior, M9 comportamento
- D-IP-subnet 1000 sem seq-RLE: 16213B (vs 560B M10) — confirma valor
  enorme do seq-RLE + multi-delta fix
- Pre-pass off + shape-preserve off + seq-RLE off: pior caso mas RT OK

**Status**: Fase 1 WELDED. Fase 2 (online adaptive + fallback marker
no body) pendente.

**Adiado pra Fase 2**:
- Detector adaptive de eficacia da camada per eval_window
- Marker body indicando transicao on->off mid-stream
- Decoder reverse fallback markers
- Integration com T-CODE-ENCODER-MANAGER (sinks compostos com toggle)
