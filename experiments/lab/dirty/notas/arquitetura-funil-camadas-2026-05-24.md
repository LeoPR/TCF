---
title: Arquitetura funil de camadas — toggles + online adaptive (2026-05-24)
type: design-note
status: superseded  # faxina 2026-06-21
tags: [architecture, pipeline, filters, toggles, online, literatura]
created: 2026-05-24
related:
  - experiments/lab/dirty/old/welded/2026-05-24-cpf-templated-checked/
  - docs/algorithms/TCF-format.md
  - tickets/T-CODE-SCHEMA-BUILDER.md
  - tickets/T-CODE-ENCODER-MANAGER.md
---

# Arquitetura funil de camadas — toggles + online adaptive

> **SUPERSEDED (faxina 2026-06-21)**: a visão em camadas foi implementada e welded
> (CAMADA 0-3 do pipeline canonical, `PipelineConfig` com toggles, ADR-0011). O mapa
> segmentado oficial vive em [`docs/theory/strategies/INDEX.md`](../../../../docs/theory/strategies/INDEX.md).
> A parte "online adaptive / per-strategy toggle" permanece especulativa, não adotada.
> Ver também [`revisao-implicito-vs-explicito-2026-06-14.md`](revisao-implicito-vs-explicito-2026-06-14.md).

> Sintese pos sub-exps 11/13/14: pipeline TCF eh **funil de
> generalizacao por camada**. Cada camada eh estrategia toggle-able.
> Heuristica online detecta efetividade + fallback se necessario.

## Owner framing

```
- filtro #1: pre-compressao matematica (excluir redundancias obvias)
- filtro #2: classificacao de tipo (classes / identificadores unicos
  / deltable / numericos / arredondaveis / etc.)
- OBAT: padroes por similaridade e aproximacao
- HCC: relacao entre indices/marcadores
```

Cada etapa funil afunila a abstracao: **especifico → geral**.

## Diagrama proposto

```
                       INPUT (raw strings)
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │  CAMADA 0 — Filtro matematico (toggle-able) │
        │  ───────                                     │
        │  Pre-tx por nature:                          │
        │  - TM-CPF / TM-CNPJ (templated+checked)     │
        │  - TM-IP / TM-MAC (templated)               │
        │  - LR-FLOAT-PREC (lossy round)              │
        │  - CP-DATETIME (composite)                  │
        │  Output: payload + marker fallback          │
        │  Schema_builder Fase 3 alimenta             │
        └────────────────┬────────────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────────────┐
        │  CAMADA 1 — Pre-pass classificador          │
        │  ───────                                     │
        │  analyze_column → ColumnFeatures            │
        │  detect_cadence (regras 1+2)                │
        │  detect_min_len (heur v3)                   │
        │  Output: hints pra OBAT                     │
        └────────────────┬────────────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────────────┐
        │  CAMADA 2 — OBAT (tokenizer)                │
        │  ───────                                     │
        │  alg16 LCP+LCS bidirectional                │
        │  processar canonical OU                      │
        │  processar_with_hint (shape-preserve)       │
        │  Output: tokens (TokLit, TokRefPref, ...)   │
        └────────────────┬────────────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────────────┐
        │  CAMADA 3 — HCC (composicional)             │
        │  ───────                                     │
        │  M8.A virtual refs unified                  │
        │  Detector greedy net > 0                    │
        │  HCC seq-RLE near-identical (M10)           │
        │  Output: TCF text body                      │
        └────────────────┬────────────────────────────┘
                         │
                         ▼
              OUTPUT TCF (texto compacto)
```

Cada camada eh:
1. **Independente** (responsabilidade unica)
2. **Toggle-able** (pode ser bypassed: identity transform)
3. **Composable** (acceita input camada anterior, produz pra proxima)
4. **Observable** (SideOutputs captura decisoes)

## Decisoes de design (do owner)

### 1. Funil = generalizacao crescente

CAMADA 0 (filtros) eh ESPECIFICA — sabe que "isto eh CPF/IP/etc."
CAMADA 3 (HCC) eh GENERAL — opera em tokens abstratos.

Cada camada **descobre menos** sobre semantica, **opera mais** com
forma. Lesson sub-exp 13: tentar generalizar camada baixa (seq-RLE
base-aware) com info que so' camada alta tem (semantica) = sub-otimo.

### 2. Toggle por camada

```python
encode(data, layers=[
    Filter(natures=['cpf', 'ip']),  # camada 0 — opcional
    PrePass(min_len_strategy='gating'),  # camada 1 — sempre
    OBAT(mode='canonical'),         # camada 2 — sempre
    HCC(seq_rle=True),              # camada 3 — sempre
])

# Debug mode: skip filtros
encode(data, layers=[
    Identity(),                      # camada 0 bypassed
    PrePass(),
    OBAT(),
    HCC(),
])

# Performance mode: skip seq-RLE pos
encode(data, layers=[..., HCC(seq_rle=False)])
```

### 3. Online adaptive + fallback

**Cenario streaming**: encoder processa values em ordem. Pode detectar
mid-stream que estrategia nao esta ajudando.

Heuristica per-camada:
```python
class AdaptiveCamada:
    def __init__(self, base_strategy, eval_window=100):
        self.strategy = base_strategy
        self.eval_window = eval_window
        self.bytes_in_so_far = 0
        self.bytes_out_so_far = 0
        self.fallback_active = False

    def process(self, value):
        out = self.strategy.process(value)
        self.bytes_in_so_far += len(value)
        self.bytes_out_so_far += len(out)
        if self.bytes_in_so_far % self.eval_window == 0:
            self._evaluate()
        return out

    def _evaluate(self):
        ratio = self.bytes_out_so_far / max(1, self.bytes_in_so_far)
        if ratio > 1.0:  # piorando bytes
            self.fallback_active = True
            self.strategy = Identity()
```

Marker no output indica transicao:
```
<camada-X-ON><dados>
<camada-X-OFF-marker><dados sem camada X>
```

Decoder espelha — re-aplica/desaplica conforme marker.

## Hipotese do espaco numerico — revisao com literatura

Owner pediu: revisar como literatura trata "espaco numerico abstrato"
operado computacionalmente.

### Frame of Reference (FOR) — Goldstein 1998

Encode valores como **delta from frame minimum**:
```
input:  [1000, 1003, 1007, 1010]
frame_min = 1000
encoded: [0, 3, 7, 10]  + frame_min header
```

**TCF equivalente**: M10 seq-RLE com delta. Limitacao: TCF requer
delta UNIFORME entre runs (bug #2 sub-exp 14). FOR-like permitiria
deltas variaveis em torno do minimo.

### PFOR-DELTA — Zukowski 2006

Patched FOR com excecoes pra outliers:
```
99% values fit in 8 bits delta
1% outliers stored separately
```

**TCF equivalente parcial**: fallback marker do sub-exp 05/09 cumpre
papel similar — valores que nao casam pattern caem em literal.

### Gorilla — Pelkonen 2015 (Facebook)

Time-series compression com:
- Delta-of-deltas em timestamps (`d2 = d1 - d0`)
- XOR-based em floats (XOR proximos floats, count leading zeros)

**TCF nao tem**: delta-of-deltas (segunda derivada). HCC seq-RLE eh
delta de primeira ordem. Pra series irregulares (ms variando ±2),
delta-of-deltas ganha mais. Direcao futura registrada.

### Dictionary encoding — Parquet/ORC

Strings/valores -> int IDs via dicionario inline.

**TCF equivalente**: M8A virtual refs (atoms). Cada atom eh dict entry
gerada online.

### VByte / Varint

Integer encoding em base-128, byte-by-byte com continuation bit.

**TCF nao tem**: encoding compacto de int em si. Output textual prioriza
visibilidade sobre densidade.

### Bit-packing — ClickHouse/Lucene

Pack N ints em width minimo. Sempre binario.

**Fora do escopo TCF** (textual format).

### Roaring Bitmaps — Lemire 2016

Bitmaps comprimidos com hybrid encoding (RLE + bitpack + array).
Cada container escolhe melhor encoding adaptive.

**Lesson aplicavel**: detection adaptive de melhor encoding per
chunk eh padrao em comprimores modernos. TCF poderia aplicar em
nivel de coluna (chunks de N rows).

## Operacao no espaco abstrato — sintese

**Pattern comum na literatura**:
1. Parse input → integers (ou outros tipos primitivos)
2. Compute transform (delta, xor, dictionary lookup)
3. Encode transformed values densely (bit-packing, varint, etc.)
4. Add metadata (frame_min, dict, deltas-encoding)

**TCF abordagem atual**:
1. Parse input → strings (preserva representacao textual)
2. Filter por nature (pre-tx opcional, sub-exp 05+)
3. OBAT tokeniza por similaridade
4. HCC compoe refs hierarquicos
5. seq-RLE captura cadence

**Lacuna**: TCF NAO opera em representacao abstrata pura
(integers). Mantem texto ao longo do pipeline. Isso eh **decision
deliberada** (output legivel) mas limita exploracao do espaco
numerico abstrato como FOR/PFOR/Gorilla fazem.

**Caminho hibrido proposto** (futuro):
- CAMADA 0 (filtro) pode converter pra **representacao abstrata
  interna** (e.g., int + delta scheme)
- HCC seq-RLE base-aware (sub-exp 13 abandonado) seria CAMADA 3
  generalizada
- Output textual mantido via decoder reverse

ROI conhecido (sub-exp 13): marginal pra hex IPs (-94B em 1
dataset). Talvez ganhe MAIS em hashes / blockchain TXIDs / UUIDs.
Datasets dedicados necessarios pra validar.

## Conexao com outros sub-exps

- **Sub-exp 05** (fallback marker) eh CAMADA 0 toggle (filtro por nature)
- **Sub-exp 06** (NatureApplyStats) eh observabilidade da CAMADA 0
- **Sub-exp 07** (TemplatedCheckedSpec) eh generalizacao da CAMADA 0
- **Sub-exp 13** (base-aware seq-RLE) tentou generalizar CAMADA 3
  com info da CAMADA 0 — sub-otimo
- **Sub-exp 14** (cross-subnet) identificou bugs intra-CAMADA 3

## Acoes registradas

1. **T-CODE-ENCODER-MANAGER** ja' existe (P2 — paralelizacao + sinks).
   Estender pra incluir layered toggle architecture.
2. **T-CODE-SCHEMA-BUILDER** ja' existe (P3 — Fase 3 detect natures
   alimenta CAMADA 0).
3. **Novo: T-CODE-LAYERED-PIPELINE** (P3) — toggle infrastructure
   + online adaptive + fallback. **A REGISTRAR.**
4. **Novo: T-EXP-DELTA-OF-DELTAS** (P3) — Gorilla-style pra series
   irregulares. Direcao futura.

## Open questions

1. **Toggle granularity**: per-camada (4 toggles) ou per-strategy
   dentro de camada (e.g., HCC seq-RLE on/off independente de HCC
   geral)?
2. **Online window size**: 100? 1000? Adaptive?
3. **Marker overhead**: cada transicao on/off custa bytes. Vale a
   pena se transicoes raras.
4. **Backward compat**: layered toggle inevitavelmente muda marker
   format. Necessario version bump TCF (v0.7?).

## Lesson META reforcada

3 sub-exps (11, 13, 14) convergem: **camadas tem responsabilidades
distintas**. Fix downstream raramente compensa bug upstream.

Toggle architecture + online adaptive eh a forma certa de explorar:
- Permite ablation studies cientificos (turn off camada X, mede
  contribuicao)
- Suporta dirty data + fallback grace
- Operacionaliza filosofia "viavel agora > otimo eventual" (camada
  X opcional se nao garante ganho)

## See also

- [Naturezas templated 2026-05-24](naturezas-templated-2026-05-24.md)
- [Metodologia avaliacao dados](metodologia-avaliacao-dados-2026-05-24.md)
- [Naturezas numericas 2026-05-23](naturezas-numericas-2026-05-23.md)
- [Sub-exp 14 cross-subnet](../old/welded/2026-05-24-cpf-templated-checked/14-cross-subnet-investigation/report.md)
- [Sub-exp 13 base-aware](../old/welded/2026-05-24-cpf-templated-checked/13-base-aware-seq-rle/report.md)
- [TCF format spec](../../../../docs/algorithms/TCF-format.md)
