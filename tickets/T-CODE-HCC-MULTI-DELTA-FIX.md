---
title: T-CODE-HCC-MULTI-DELTA-FIX — Bug #2 sub-exp 14 (seq-RLE rejeita multi-run delta)
status: closed-welded-canonical
priority: P2
created: 2026-05-24
updated: 2026-05-24
blocked-by: []
related:
  - experiments/lab/dirty/2026-05-24-cpf-templated-checked/14-cross-subnet-investigation/report.md
  - src/tcf/composicional/hcc_seqrle.py
  - docs/adr/0011-pacote1-weld-canonical.md
  - docs/adr/0016-hcc-multi-delta-seq-rle.md
---

# T-CODE-HCC-MULTI-DELTA-FIX — Bug #2: seq-RLE rejeita multi-run delta

## Contexto

Sub-exp 14 (2026-05-24) identificou que `hcc_seqrle.py:compare_for_seq`
linha 88 rejeita pares com multi-run delta `{0,0,0,1}` mesmo quando
estruturalmente compativeis.

```python
deltas = []
for start, end in runs_a:
    a_int = int(line_a[start:end])
    b_int = int(line_b[start:end])
    deltas.append(b_int - a_int)
if len(set(deltas)) != 1:  # ← BUG: requer uniformidade absoluta
    return None
```

## Repro

Test direto (em IPs subnet sem atom HCC):
```
line_a = '\\125.\\114.\\71.\\1'
line_b = '\\125.\\114.\\71.\\2'
runs_a == runs_b == [(1,4), (6,9), (11,13), (15,16)]
deltas = [0, 0, 0, 1]      # 3 prefix invariantes + 1 cadenced suffix
set(deltas) = {0, 1}       # nao uniforme -> RETURN NONE
```

Pares deveriam ser detectados como near-identical (apenas posicao 15
muda) mas algoritmo rejeita.

## Impacto medido (sub-exp 14)

D-IP-subnet (1000 IPs, 10 subnets):
- M10 atual: 15747B (117.51% ratio — PIOR que raw)
- Estimativa pos-fix: ~300-500B (~3-4% ratio)
- Speedup compressao: ~40x

Impacto similar em qualquer dataset com prefix-invariante + suffix-cadenced
sem atom HCC compartilhado.

## Hipotese / Plano

**Fix proposto** (per-run delta encoding):

Opcao A — Marker format vetor de deltas:
```
Atual: *N+delta|template      (delta uniforme)
Novo:  *N+0,0,0,1|template    (delta per run, CSV)
```

Opcao B — Marker indica run_idx do delta nao-zero:
```
*N+delta@runIdx|template      (delta = 1, runIdx = 3 → so' o ultimo run shifta)
```

Opcao C — Detector identifica unico delta nao-zero:
```python
non_zero = [d for d in deltas if d != 0]
if len(set(non_zero)) > 1: return None  # rejeicao se >1 delta non-zero diferentes
if not non_zero: return None  # sem mudanca real
delta = non_zero[0]
# Decode infere posicoes ativas por re-comparacao template vs template+delta
```

Opcao C eh menos invasiva ao marker format (mantem `*N+delta|`) mas exige
decoder inteligente.

## Criterio de aceite

- [ ] Implementacao escolhida (A/B/C) com ADR justificando
- [ ] D-IP-subnet ratio melhora de 117% pra <= 10% (esperado ~3-4%)
- [ ] RT byte-canonical em D1-D9 (M9/M10 invariants)
- [ ] Backward compat: decoder M10 antigo le novo formato (ou version bump)
- [ ] Tests novos em `tests/test_core_rt.py`
- [ ] Real-world Adult+TPC-H sem regressao

## Riscos

1. **Quebra M10 byte-canonical** — qualquer mudanca em compare_for_seq
   pode produzir diferentes seq_runs em D1-D9. Validar primeiro.
2. **Marker format change** — opcao A/B mudam syntax; quebram decoders
   antigos.
3. **Decoder ambiguity** (opcao C) — heuristica de "qual run shiftou"
   pode falhar em edge cases.

## Conexao

- Sub-exp 14 diagnostico: [report.md](../experiments/lab/dirty/2026-05-24-cpf-templated-checked/14-cross-subnet-investigation/report.md)
- ADR-0011 (Pacote 1 welded canonical) — invariant M10
- T-CODE-HCC-ATOM-DETECTION-REFINE (Bug #1, complementar) — pode mitigar
  parcialmente sem precisar deste fix

## Updates datados

### 2026-05-24 — abertura

Ticket criado pos-sub-exp 14. NAO implementar agora (risco alto canonical).
Owner pode priorizar quando aparecer use case real significativo
(cross-subnet em real-world).

### 2026-05-24 — WELDED via ADR-0016 (Opcao A com backward compat)

Owner aprovou fix mesmo dia. Welded com Opcao A modificada
(M10 markers preserved pra casos uniform delta; novo CSV format pra
casos misto).

**Implementacao** (~80 linhas em hcc_seqrle.py):
- compare_for_seq agora retorna list[int] (sempre)
- shift_escape_digits aceita int (M10 compat) OR list[int] (per-run)
- compact_body emit `*N+delta|` (M10) OR `*N+d1,d2,...|` (CSV)
- expand_seq_marker detecta formato pela presenca de `,`
- _is_uniform_delta helper

**Resultados:**
- D1-D9 byte-canonical preservado (test_m10_baseline_invariant PASS)
- D17a 322B INVARIANT preservado
- D-IP-subnet 1000 sem nature: 117.51% -> **4.18%** (-96.4%)
- D-IP-subnet 200: 68.17% -> 3.58%
- 19 tests novos test_hcc_multi_delta.py
- Suite completa: 211 passed (+19 novos)

**Bug #1 (T-CODE-HCC-ATOM-DETECTION-REFINE) SUPERSEDED**: cross-subnet
agora compactado via Bug #2 fix sem precisar atom secundario.

Status: closed-welded-canonical. ADR-0016 documenta decisao.
