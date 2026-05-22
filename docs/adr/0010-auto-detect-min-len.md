# 0010 — Auto-detect min_len por coluna

**Status**: accepted
**Date**: 2026-05-22
**Deciders**: project owner
**Tags**: heuristic, pre-stage, h-da-11, real-world, encoder, single-col, multi-col

## Context and Problem Statement

OBAT `processar(unicas, min_len=N)` aceita parametro `min_len` (tamanho
minimo de prefix/suffix considerado em LCP/LCS). Default M0 e' `min_len=3`
(decisao exploratoria, sem justificativa empirica forte).

Revalidacao H-DA-10 (ticket T-REVAL-H-DA-01-06-10, sub-exp
`2026-05-21-revalidacao-categoria-B/03-h-da-10-min-len-realworld/`)
mostrou que `min_len=3` deixa **9.92% bytes weighted** na mesa em
real-world (Adult Census + TPC-H 58 colunas).

Padrao identificado:
- Strings longas (comments, fnlwgt): `min_len=6` otimo
- Strings medias (phone, acctbal): `min_len=5` otimo
- IDs sequenciais (orderkey, partkey): `min_len=4` otimo
- Categoricas baixa-cardinalidade (sex, race): `min_len=3` (default OK)

Ganho potencial: ~9% bytes real-world weighted.

## Considered Options

### Opcao A — Hard-coded default
Manter `min_len=3` fixo. Perde ~9% em real-world.

### Opcao B — Parametro user-facing
Expor `encode(values, min_len=...)`. Usuario decide. Onus na UX.

### Opcao C — Auto-detect via heuristica (H-DA-11)
Pre-pass leve (avg_len + cardinality + is_numeric) escolhe `min_len`
automaticamente. Sub-exp `2026-05-21-h-da-11-auto-min-len/` valida.

### Opcao D — Auto-detect via busca exaustiva (oracle)
Tentar todos `min_len in {2,3,4,5,6}` e escolher melhor. 5x custo encode.
Marginal benefit vs heuristica (99.5% captura).

### Opcao E — ML-based
Treinar classifier nos audit data. Overhead alto.

## Decision Outcome

**Opcao C — Auto-detect via heuristica v3 com gating por n_rows.**

Implementacao:
```python
def _is_numeric_string(v):
    if not v: return False
    try:
        float(v); return True
    except (ValueError, TypeError):
        return False

def detect_min_len(values, n_threshold=100):
    n = len(values)
    if n < n_threshold:
        return 3  # gating: datasets pequenos usam default seguro

    avg_len = sum(len(v) for v in values) / n
    n_unicas = len(set(values))
    card = n_unicas / n
    sample = values[:min(20, n)]
    is_num = all(_is_numeric_string(v) for v in sample) if sample else False

    if card < 0.2: return 3                                 # baixa-card seguro
    if avg_len >= 25: return 6                              # long-form
    if avg_len >= 8 and card >= 0.4: return 6               # dates, mid-len high-card
    if avg_len >= 5 and is_num and card >= 0.8: return 6    # numeric high-card
    if avg_len >= 12 and card >= 0.7: return 5              # c_phone
    if avg_len >= 3 and card >= 0.2: return 4               # IDs sequenciais, D9
    return 3
```

Gating `n >= 100`:
- Preserva M9 baseline EXATO (1615B em D1-D9 single-col, n=12-20)
- Datasets pequenos sao tipicamente exemplos/sinteticos onde min_len=3
  ja' funciona bem
- Datasets reais (Adult/TPC-H tem n=1000-5000+) recebem heuristica completa

## Validacao empirica

### Sub-exp 02 (heuristica isolada em real-world)

`experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/02-heuristica-v1/`

58 colunas (D9 controle + Adult 1k/5k + TPC-H region/customer/lineitem 5k):

| Estrategia | gain weighted | captura oracle | regressoes |
|---|---:|---:|---:|
| default (ml=3) | 0.00% | — | — |
| oracle (best per col) | 9.92% | 100% | — |
| heur v1 (so' avg_len) | 3.41% | 34.3% | 8 |
| heur v2 (+ card + num) | 7.39% | 74.5% | 5 |
| **heur v3** | **9.87%** | **99.5%** | **1** (irrelevante) |

### Sub-exp 03 (M9 baseline preservation)

`experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/03-validar-baseline-D1-D9/`

D1-D9 single-col:

| Estrategia | bytes | delta vs M9 |
|---|---:|---:|
| default ml=3 (M9) | **1615B** | — |
| heur v3 (sem gating) | 1610B | -5B (melhora liquida) |
| **heur v3 + gating n>=100** | **1615B** | **+0B** (preserva exato) |

Gating escolhido: n<100 → fallback ml=3. D1-D9 todos passam (n=12-20),
recebem default → baseline preservado.

### Validacao multi-camada pos-welding (prototype EXP-010)

`experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/04-validacao-prototipo-EXP-010/`

| Camada | base (B) | new (B) | delta | RT |
|---|---:|---:|---:|---|
| D1-D9 single-col (M9 baseline) | **1523** | **1523** | +0 | 9/9 OK |
| Adult-1000 (15 cols) + Adult-5000 + TPC-H | **940,720** | **889,757** | **-50,963 (-5.42%)** | 57/57 OK |

**Nota sobre 5.42% vs 9.87% predito**: sub-exp 02 mediu vs encoder
canonical M8A puro (`M8AVirtualRefsSyntax + processar(min_len=3)`).
EXP-010 prototype baseline ja' inclui HCC seq-RLE near-identical +
auto-detect cadence — comprime parte do mesmo espaco. 5.42% adicional
sobre EXP-010 ja' otimizado e' o ganho LIQUIDO real do auto-min_len.
Welding canonical em src/tcf (sem HCC seq-RLE/auto-cadence) provavelmente
atingira proximo de 9.87%.

**Top wins reais (prototype)**:
- `tpch.lineitem-5k/l_comment`: -29,647B (-18.18%) com ml=6
- `tpch.lineitem-5k/l_shipdate`: -5,239B (-12.70%) com ml=6
- `tpch.customer-5k/c_phone`: -4,149B (-12.26%) com ml=6
- `tpch.lineitem-5k/l_commitdate`: -4,545B (-11.36%) com ml=6
- `tpch.lineitem-5k/l_receiptdate`: -4,065B (-10.16%) com ml=6
- `tpch.customer-5k/c_comment`: -3,310B (-3.05%) com ml=6

## Pros and Cons

| Opcao | Pros | Cons |
|---|---|---|
| A (hard-coded) | Simples | Perde 9.87% real-world |
| B (param user) | Flexivel | Onus UX; usuario nao sabe escolher |
| **C (heuristica + gating)** | Captura 99.5% oracle; preserva M9; pre-pass O(N) | 1 regra adicional no encoder |
| D (busca exaustiva) | Otima | 5x custo encode |
| E (ML) | Potencialmente otimo | Overhead, complexidade |

## Implementacao

### Status atual (2026-05-22): prototype confirmed, canonical pending

Implementacao em DUAS etapas (mesmo padrao de ADR-0008):

**Etapa 1 (FEITA)** — Welding em EXP-010 prototype:
- Novo modulo `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/auto_min_len.py`
- Modificacao em `delta_aware.encode_column`: default `min_len=None`
  → auto-detect

**Etapa 2 (PENDENTE)** — Welding canonical em `src/tcf/`:
- Aguarda aprovacao explicita do project owner
- Mudanca prevista:
  - Novo modulo `src/tcf/auto_min_len.py` (copia de EXP-010 + adjustments)
  - `src/tcf/encoder.py` — `encode()` chama `detect_min_len(values)`

### Backward compat

- Output bytes-canonical IDENTICO pra D1-D9 (n<100, fallback ml=3)
- Output bytes diferente pra colunas n>=100 (esperado e desejado — ganho)
- Decoder NAO precisa mudanca (min_len e' decisao do encoder; output
  preserva sintaxe HCC canonical)

## Riscos residuais

- **Cardinality threshold 0.2 / avg_len buckets**: arbitrarios. Tuned em
  58 colunas reais; pode nao generalizar pra outros datasets.
  Mitigacao: revisar empirico em datasets novos quando forem testados.
- **n_threshold=100**: arbitrario. Escolhido pra preservar D1-D9 (n<=20)
  como default. Datasets entre 50-200 rows podem ter perfil diferente.
  Mitigacao: testar quando relevante.
- **Pre-pass overhead**: 1 passada O(N) sobre values pra avg/card.
  Negligivel vs encode O(N^2). H-PERF nao afetado.
- **Welding em src/tcf canonical**: mudanca em interface (assinatura
  publica `encode()` inalterada, mas comportamento interno muda).

## Hipoteses decorrentes (registrar)

- **H-DA-11b** (tunar): cardinality threshold 0.2 vs 0.3 vs 0.1
- **H-DA-11c** (extrair): pre-pass features para outros encoders
  (HCC seq-RLE near-identical, OBAT shape-preserve) — talvez
  consolidar em `detect_features()` unificado

## Cross-references

- [Sub-exp H-DA-10 (oracle origem)](../../experiments/lab/dirty/2026-05-21-revalidacao-categoria-B/03-h-da-10-min-len-realworld/)
- [Lab H-DA-11 (heuristica + validacao)](../../experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/)
- [Ticket T-EXP-H-DA-11](../../tickets/T-EXP-H-DA-11.md)
- [ADR-0008 detect_cadence (template similar)](0008-detect-cadence-numeric-rule.md)
- [Roadmap H-DA-11](../../experiments/lab/dirty/notas/roadmap-hipoteses.md)
