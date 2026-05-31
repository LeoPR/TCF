# Sub-exp 03 — welding decision (resultado FINAL)

## Setup

- v3 (hash trigram prefix+suffix) monkey-patched no pipeline completo
- Validacao isolada em D1-D9 + lineitem 1k/5k
- Welding em `src/tcf/core/online.py` + `experiments/lab/clean/EXP-010/obat_shape.py`
- Re-validacao multi-camada (EXP-007/010/011/012/013/014)

## Validacao isolada (pre-welding)

| Dataset | Bytes esperados | Bytes obtidos | Match | Encode (s) | Speedup |
|---|---:|---:|---|---:|---:|
| D1-D9 (total) | 1,615 | 1,615 | OK | <0.1 | n/a |
| lineitem 1k | 102,366 | 102,366 | OK | 7.80 | 1.3x |
| lineitem 5k | 498,271 | 498,271 | OK | 40.78 | 1.8x |

RT 100% em todos. Verdict: **PROCEDER COM WELDING**.

### Detalhe D1-D9

| dataset | bytes | RT |
|---|---:|---|
| D1-emails-simples | 118 | OK |
| D2-emails-quote-id | 166 | OK |
| D3-stress-substring | 177 | OK |
| D4-caos-mix | 113 | OK |
| D5-padroes-multiplos | 281 | OK |
| D6-poucos-em-ruido | 287 | OK |
| D7-aninhamento | 215 | OK |
| D8-cabeca-cauda | 100 | OK |
| D9-frequencia-alta | 158 | OK |
| **TOTAL** | **1615** | **9/9** |

## Welding aplicado

### `src/tcf/core/online.py`

- Adicionado: `_lcp_len_capped`, `_lcs_len_capped` (variantes que
  recebem `la`/`lb`/`cap`)
- Reescrito: `_melhor_pref`, `_melhor_suf`, `_escolher_par` com
  assinatura `(s, ls, strings, lens, index, max_len, min_len)`
- Reescrito: `processar` mantem `prefix_index` + `suffix_index`,
  atualiza apos cada string
- API publica intacta: `lcp_len`, `lcs_len`, `processar`, `reconstroi`,
  dataclasses

### `experiments/lab/clean/EXP-010/obat_shape.py`

- Adaptado pra nova assinatura indexed de `_escolher_par`
- `_try_preserve_shape` agora recebe `(strings, idx_limit)` em vez
  de `anteriores` (evita slice)
- Mantem indexes locais como em `processar`

## Re-validacao multi-camada

| Camada | Esperado | Obtido | Status |
|---|---|---|---|
| EXP-007 (D1-D9) | 1615B, 9/9 RT | **1615B, 9/9 RT** | OK |
| EXP-010 (20 datasets) | RT 20/20 | **RT 20/20** | OK |
| EXP-011 (D17a multi-col) | RT OK | **RT OK** | OK |
| EXP-012 (Adult 4 vol) | RT 4/4 | **RT 4/4** | OK |
| EXP-013 (TPC-H 8 tabs) | RT 8/8 | **RT 8/8** | OK |

Zero regressao byte-canonical. M9 baseline preservado.

## EXP-014 pos-welding (caracterizacao novo alpha)

| Volume | Antes | Depois | Speedup |
|---:|---:|---:|---:|
| 1k | 10.2s | 7.9s | 1.3x |
| 5k | 71.5s | 40.5s | 1.77x |
| 10k | 186.9s | 86.6s | 2.16x |
| 20k | 626.5s | 232.0s | **2.70x** |

- **alpha**: 1.75 → **1.42**
- **Speedup AUMENTA com escala** (ataque ao componente quadratico)
- **Lineitem full 60175 estimado**: 71 min → **18.5 min** (-74%)
- Bytes IDENTICOS em todos volumes

## Hipoteses fechadas neste lab

- **H-PERF-01** (confirmada): `_melhor_pref` + `_melhor_suf` = 74% tempo
- **H-PERF-01b** (confirmada, nao prevista): HCC `_detect_compositions`
  e' o 2o hotspot (24%)
- **H-PERF-02** (CONFIRMADA): hash trigrama reduz O(N²) a O(N) amortizado
- **H-PERF-03** (confirmada parcial): len-elim sozinho 1.3x
- **H-RW-05** (originalmente "encode O(N²)") — atualizada: alpha caiu
  de 1.75 → 1.42 pos-otimizacao

## Hipoteses decorrentes (registradas)

- **H-PERF-04**: trigrama de meio reduz buckets em datas (esperado 5x+)
- **H-PERF-05**: otimizar HCC `_detect_compositions` (24% tempo)
- **H-PERF-06**: Cython/Rust port de `lcp_len`/`lcs_len`

## Conclusao

**Welding bem-sucedido em src/tcf**. Otimizacao byte-canonical
preservada, 2.70x speedup em 20k, alpha 1.75 → 1.42. ADR-0009 accepted.

Proximo passo natural: rodar **lineitem full 60175** real (~18.5min)
para confirmar extrapolacao.

## See also

- [Sub-exp 01 profile](../01-profile-baseline/)
- [Sub-exp 02 prototipos](../02-index-prototypes/)
- [ADR-0009](../../../../../docs/adr/0009-obat-trigram-index-optimization.md)
- [EXP-014 report](../../../../clean/EXP-014-tpch-lineitem-scale/report.md)
