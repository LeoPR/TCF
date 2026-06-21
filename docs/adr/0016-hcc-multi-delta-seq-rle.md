# 0016 — HCC seq-RLE multi-delta (Bug #2 sub-exp 14 fix)

**Status**: accepted + welded
**Date**: 2026-05-24
**Deciders**: project owner
**Tags**: welding, hcc, seq-rle, bug-fix, sub-exp-14, multi-delta

## Context and Problem Statement

Sub-exp 14 (2026-05-24, cross-subnet investigation) identificou Bug #2
em [`hcc_seqrle.py:88`](../../src/tcf/composicional/hcc_seqrle.py):

```python
if len(set(deltas)) != 1:
    return None   # ← rejeita multi-run delta [0,0,0,1]
```

Heuristica original requeria delta UNIFORME entre todos runs. Quando
linhas tinham prefix invariante (3 runs com delta=0) + suffix cadenced
(1 run com delta=1), rejeicao falsa.

### Impacto medido (sub-exp 14)

D-IP-subnet 1000 IPs sem nature:
- M10 atual: 15747B = 117.51% ratio (PIOR que raw!)
- Causa: cada subnet (subnet 1 atomizada como ref `1`, subnet 2..10
  literais cheios) gerava lines como `\125.\114.\71.\1` com 4 runs.
  Multi-delta [0,0,0,1] -> rejeitado -> sem compactacao.

## Considered Options

### Opcao A — Per-run delta vector em marker

Marker novo `*N+d1,d2,d3,d4|template` (CSV de deltas per run).

Pros: max flexibilidade, suporta qualquer combo deltas
Contras: marker format change, decoders antigos quebram

### Opcao B — Run idx em marker

Marker `*N+delta@runIdx|template` (single delta + qual run shifta).

Pros: marker menor que Opcao A
Contras: so' 1 run pode incrementar; menos flexivel

### Opcao C — Heuristica decoder

Decoder identifica positions de diff entre template e template+delta.

Pros: zero marker change
Contras: ambiguo em edge cases; decoder complexo

## Decision Outcome

**Opcao A com backward compat** (M10 markers preserved):

### Marker syntax

```
M10 uniform delta (compat):    *N+delta|template
ADR-0016 multi-delta novo:     *N+d1,d2,d3,d4|template   (CSV se misto)
```

Disambiguacao: presenca de `,` no portion de delta → novo formato.

### Comportamento por caso

| Caso | Deltas detectados | Marker emit |
|---|---|---|
| Single run, delta non-zero | `[1]` (uniform=1) | `*N+1\|template` (M10) |
| Multi run, mesmo delta | `[1,1,1]` (uniform=1) | `*N+1\|template` (M10) |
| Multi run, 1 non-zero + zeros | `[0,0,0,1]` | `*N+0,0,0,1\|template` (NOVO) |
| Multi run, multiple different | `[1,2]` | rejeita (Fase 2) |
| All zero | `[0,0,0]` | rejeita (no change) |

### Restricao Fase 1

Multi-delta limitado a **1 unico valor non-zero** (resto zeros).
Casos como `[1,2,3]` ou `[1,0,2]` rejeitados — defer pra Fase 2 se
aparecer use case.

## Implementacao

### `compare_for_seq` — retorna list[int]

Antes:
```python
def compare_for_seq(...) -> int | None
```

Depois:
```python
def compare_for_seq(...) -> list[int] | None
```

Sempre retorna lista de deltas (1 por run). Caller decide se emit
M10 single ou CSV multi.

### `shift_escape_digits` — aceita int OR list

```python
def shift_escape_digits(template: str, delta) -> str:
    # M10 compat: int -> apply to ALL runs (mesmo delta)
    # ADR-0016:   list[int] -> per-run delta
```

### `compact_body` — escolhe marker format

```python
uniform = _is_uniform_delta(deltas)  # int OR None
if uniform is not None:
    marker = f"*{count}+{uniform}|{template}"          # M10 compat
else:
    marker = f"*{count}+{','.join(...)}|{template}"    # ADR-0016 CSV
```

### `expand_seq_marker` — detecta formato

```python
if ',' in delta_str:
    delta_arg = [int(d) for d in delta_str.split(',')]   # ADR-0016
else:
    delta_arg = int(delta_str)                           # M10 compat
```

## Validacao byte-canonical

**CRITICAL — M10 invariant preservado:**

- D1-D9 sint baseline `test_m10_baseline_invariant`: 1523B PASSA
- D17a multi-col invariant: 322B PASSA
- 30 tests test_core_rt.py PASSAM
- 21 tests test_natures.py PASSAM
- 16 tests test_natures_ip.py PASSAM
- 19 tests test_hcc_multi_delta.py PASSAM (novos)
- Suite completa: **211 passed** (+19 novos vs commit anterior) + 1 xfailed + 1 pre-existing fail

Razao M10 invariant preservado: D1-D9 datasets nao tem casos
multi-run com mixed deltas. Markers emit identicos.

## Impacto medido

D-IP-subnet (sem nature, M10 puro):

| N | Pre-fix (sub-exp 14) | **Pos-fix (este ADR)** | Redução |
|---:|---:|---:|---:|
| 50 | 37B (5.78%) | 37B (5.78%) | preserved |
| 100 | 37B (2.87%) | 37B (2.87%) | preserved |
| 200 | 1827B (68.17%) | **96B (3.58%)** | **-94.7%** |
| 500 | 6897B (105.30%) | **267B (4.08%)** | **-96.1%** |
| 1000 | 15747B (117.51%) | **560B (4.18%)** | **-96.4%** |

Comparacao com SPEC_IP nature (ADR-0015 extensao):
- SPEC_IP em 1000: 229B (1.71%)
- M10 fix em 1000: 560B (4.18%)

SPEC_IP ainda vence (-59% adicional vs fix sozinho) por padding 12-digit
visivel + ativa cadence detection. Mas **agora ambos disponiveis** — user
pode escolher overhead nature vs deixar M10 cuidar.

## Consequences

**Positivas**:
- Cross-subnet ratios reduzidos dramaticamente (~25x)
- M10 INVARIANT byte-canonical preservado (D1-D9, D17a)
- Backward compat preservado (M10 markers ainda funcionam, novo
  format opcional)
- Bug arquitetural sub-exp 14 corrigido na fonte
- 19 tests novos validam comportamento

**Neutras**:
- Marker format ampliado (CSV opcional) — documentado em HCC.md
- Decoders externos antigos (se existirem) precisam atualizar pra ler
  CSV deltas. Mitigacao: M10 markers unchanged em maioria dos casos.

**Negativas**:
- Compare_for_seq retorno mudou (int -> list[int]). Codigo externo
  que importa diretamente pode quebrar (encoder/decoder internos
  atualizados; ninguem externo deveria depender).

## Trade-off vs SPEC_IP

| Aspecto | SPEC_IP nature | M10 multi-delta fix |
|---|---|---|
| Compression D-IP-subnet 1000 | 229B (1.71%) | 560B (4.18%) |
| Requer config | opt-in (`nature=SPEC_IP`) | automatico |
| Decoder precisa spec | sim (out-of-band) | nao |
| Bytes per IP | ~0.23B | ~0.56B |

Ambos valem ter — SPEC_IP pra max compression em IPs canonical,
M10 fix pra default behavior sem config.

## Links

- Sub-exp 14: [report.md](../../experiments/lab/dirty/old/welded/2026-05-24-cpf-templated-checked/14-cross-subnet-investigation/report.md)
- Ticket [T-CODE-HCC-MULTI-DELTA-FIX](../../tickets/T-CODE-HCC-MULTI-DELTA-FIX.md) (closing this)
- ADR-0011 (Pacote 1 weld canonical, base do seq-RLE)
- ADR-0015 (natures welding, alternative path pra IP via SPEC_IP)
- HCC.md (precisa atualizar com novo marker format)

## Updates

### 2026-05-24 — welded

Implementacao: ~80 linhas de mudancas em `hcc_seqrle.py`
(compare_for_seq, shift_escape_digits, detect_seq_runs, compact_body,
expand_seq_marker, novo `_is_uniform_delta`).

Tests: 19 novos em `tests/test_hcc_multi_delta.py`.

Bug #1 (T-CODE-HCC-ATOM-DETECTION-REFINE) NAO precisa mais — Bug #2
fix cobre cross-subnet via mecanismo alternativo (seq-RLE multi-delta
em vez de M8A atom secundario). Ticket atom-refine pode ser marcado
**deferred** ou closed-superseded.
