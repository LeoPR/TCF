# Sub-exp 01 — profile HCC (resultado)

**Dataset**: lineitem 5000 rows × 16 cols
**Encode time (com cProfile)**: 80.8s
**Bytes TCF**: 498,271
**Total _detect_compositions time**: 60.90s (75% do encode)
**Total outer iterations**: 408 (16 cols)
**Total candidates iter1**: 20050
**Total pairs (R>=2) iter1**: 20085

## Top 30 cumulative — syntax.py

```
Wed May 20 00:48:11 2026    C:\Users\leona\OneDrive\Documents\Projects\Acadêmicos\TCF\experiments\lab\dirty\2026-05-20-hcc-perf-optimization\01-profile-hcc\hcc_baseline.prof

         79536865 function calls (79536798 primitive calls) in 80.814 seconds

   Ordered by: cumulative time
   List reduced from 109 to 33 due to restriction <'syntax.py'>
   List reduced from 33 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
       16    0.011    0.001   63.010    3.938 syntax.py:646(encode)
       16   34.621    2.164   60.901    3.806 syntax.py:225(_detect_compositions)
  1116611    7.964    0.000   15.397    0.000 syntax.py:364(_estimate_baseline_chars)
  4256444    1.550    0.000    1.550    0.000 syntax.py:381(<genexpr>)
       16    0.398    0.025    0.759    0.047 syntax.py:151(_tokenize_pieces)
       16    0.135    0.008    0.708    0.044 syntax.py:391(_emit_body)
  1814718    0.663    0.000    0.663    0.000 syntax.py:277(<genexpr>)
  1266245    0.454    0.000    0.454    0.000 syntax.py:305(<genexpr>)
       16    0.257    0.016    0.349    0.022 syntax.py:545(_build_trace)
    14057    0.102    0.000    0.347    0.000 syntax.py:470(_emit_ref_run)
       16    0.073    0.005    0.247    0.015 syntax.py:614(_build_rede)
   522574    0.220    0.000    0.220    0.000 syntax.py:281(<genexpr>)
    16593    0.114    0.000    0.178    0.000 syntax.py:52(_escape_lit)
  1113377    0.168    0.000    0.168    0.000 syntax.py:308(<lambda>)
    16877    0.047    0.000    0.150    0.000 syntax.py:90(_emit_refs_range)
       16    0.087    0.005    0.124    0.008 syntax.py:121(_coletar_quebras)
    11473    0.015    0.000    0.063    0.000 syntax.py:116(_count_ids_in_refs)
    28722    0.046    0.000    0.063    0.000 syntax.py:75(_runs_pos)
       16    0.040    0.003    0.056    0.004 syntax.py:42(_rle_adjacente)
    17240    0.019    0.000    0.030    0.000 syntax.py:495(_emit_alias)
    53876    0.020    0.000    0.020    0.000 syntax.py:100(<genexpr>)
     4356    0.004    0.000    0.016    0.000 syntax.py:610(_fmt_sub)
    14171    0.010    0.000    0.014    0.000 syntax.py:119(<genexpr>)
    15022    0.006    0.000    0.006    0.000 syntax.py:612(<genexpr>)
      372    0.001    0.000    0.005    0.000 syntax.py:103(_emit_composition)
    16593    0.005    0.000    0.005    0.000 syntax.py:177(<genexpr>)
     5351    0.002    0.000    0.002    0.000 syntax.py:640(<lambda>)
     5352    0.001    0.000    0.001    0.000 syntax.py:607(<genexpr>)
  953/900    0.001    0.000    0.001    0.000 syntax.py:511(expand)
     1761    0.001    0.000    0.001    0.000 syntax.py:602(<genexpr>)
```

## Top 30 tottime (self) — syntax.py

```
Wed May 20 00:48:11 2026    C:\Users\leona\OneDrive\Documents\Projects\Acadêmicos\TCF\experiments\lab\dirty\2026-05-20-hcc-perf-optimization\01-profile-hcc\hcc_baseline.prof

         79536865 function calls (79536798 primitive calls) in 80.814 seconds

   Ordered by: internal time
   List reduced from 109 to 33 due to restriction <'syntax.py'>
   List reduced from 33 to 30 due to restriction <30>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
       16   34.621    2.164   60.901    3.806 syntax.py:225(_detect_compositions)
  1116611    7.964    0.000   15.397    0.000 syntax.py:364(_estimate_baseline_chars)
  4256444    1.550    0.000    1.550    0.000 syntax.py:381(<genexpr>)
  1814718    0.663    0.000    0.663    0.000 syntax.py:277(<genexpr>)
  1266245    0.454    0.000    0.454    0.000 syntax.py:305(<genexpr>)
       16    0.398    0.025    0.759    0.047 syntax.py:151(_tokenize_pieces)
       16    0.257    0.016    0.349    0.022 syntax.py:545(_build_trace)
   522574    0.220    0.000    0.220    0.000 syntax.py:281(<genexpr>)
  1113377    0.168    0.000    0.168    0.000 syntax.py:308(<lambda>)
       16    0.135    0.008    0.708    0.044 syntax.py:391(_emit_body)
    16593    0.114    0.000    0.178    0.000 syntax.py:52(_escape_lit)
    14057    0.102    0.000    0.347    0.000 syntax.py:470(_emit_ref_run)
       16    0.087    0.005    0.124    0.008 syntax.py:121(_coletar_quebras)
       16    0.073    0.005    0.247    0.015 syntax.py:614(_build_rede)
    16877    0.047    0.000    0.150    0.000 syntax.py:90(_emit_refs_range)
    28722    0.046    0.000    0.063    0.000 syntax.py:75(_runs_pos)
       16    0.040    0.003    0.056    0.004 syntax.py:42(_rle_adjacente)
    53876    0.020    0.000    0.020    0.000 syntax.py:100(<genexpr>)
    17240    0.019    0.000    0.030    0.000 syntax.py:495(_emit_alias)
    11473    0.015    0.000    0.063    0.000 syntax.py:116(_count_ids_in_refs)
       16    0.011    0.001   63.010    3.938 syntax.py:646(encode)
    14171    0.010    0.000    0.014    0.000 syntax.py:119(<genexpr>)
    15022    0.006    0.000    0.006    0.000 syntax.py:612(<genexpr>)
    16593    0.005    0.000    0.005    0.000 syntax.py:177(<genexpr>)
     4356    0.004    0.000    0.016    0.000 syntax.py:610(_fmt_sub)
     5351    0.002    0.000    0.002    0.000 syntax.py:640(<lambda>)
      372    0.001    0.000    0.005    0.000 syntax.py:103(_emit_composition)
     5352    0.001    0.000    0.001    0.000 syntax.py:607(<genexpr>)
     1761    0.001    0.000    0.001    0.000 syntax.py:602(<genexpr>)
  953/900    0.001    0.000    0.001    0.000 syntax.py:511(expand)
```

## Top 20 cumulative — geral

```
Wed May 20 00:48:11 2026    C:\Users\leona\OneDrive\Documents\Projects\Acadêmicos\TCF\experiments\lab\dirty\2026-05-20-hcc-perf-optimization\01-profile-hcc\hcc_baseline.prof

         79536865 function calls (79536798 primitive calls) in 80.814 seconds

   Ordered by: cumulative time
   List reduced from 109 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.006    0.006   80.819   80.819 multi_col.py:44(encode_table)
       16    0.005    0.000   80.812    5.051 delta_aware.py:45(encode_column)
       16    0.176    0.011   63.569    3.973 hcc_seqrle.py:210(encode)
       16    0.011    0.001   63.010    3.938 syntax.py:646(encode)
       16    0.019    0.001   60.933    3.808 run_profile_hcc.py:41(instrumented_detect)
       16   34.621    2.164   60.901    3.806 syntax.py:225(_detect_compositions)
        8    0.159    0.020   17.109    2.139 online.py:179(processar)
    11391    0.030    0.000   16.794    0.001 online.py:129(_escolher_par)
    18646    6.547    0.000   16.296    0.001 online.py:97(_melhor_pref)
  1116611    7.964    0.000   15.397    0.000 syntax.py:364(_estimate_baseline_chars)
 13630846    9.741    0.000    9.741    0.000 online.py:75(_lcp_len_capped)
 33009614    6.678    0.000    6.678    0.000 {built-in method builtins.len}
  1907323    2.269    0.000    3.838    0.000 {method 'extend' of 'list' objects}
 11527859    3.333    0.000    3.333    0.000 {method 'append' of 'list' objects}
  1278300    1.377    0.000    2.515    0.000 {built-in method builtins.sum}
  4256444    1.550    0.000    1.550    0.000 syntax.py:381(<genexpr>)
       16    0.398    0.025    0.759    0.047 syntax.py:151(_tokenize_pieces)
       16    0.135    0.008    0.708    0.044 syntax.py:391(_emit_body)
  1814718    0.663    0.000    0.663    0.000 syntax.py:277(<genexpr>)
  1200442    0.571    0.000    0.633    0.000 {method 'join' of 'str' objects}
```

## Callers `_detect_compositions` + `_estimate_baseline_chars`

```
(no data)
```

## Scale por coluna (instrumented)

| col_idx | n_lines | n_refs_total | refs_max_len | atom_count | n_iter | n_aliases | candidates_iter1 | pairs_iter1 | time(s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1241 | 0 | 0 | 1241 | 1 | 0 | 0 | 0 | 0.00 |
| 2 | 1832 | 0 | 0 | 1832 | 1 | 0 | 0 | 0 | 0.00 |
| 3 | 100 | 0 | 0 | 100 | 1 | 0 | 0 | 0 | 0.00 |
| 4 | 7 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0.00 |
| 5 | 50 | 0 | 0 | 50 | 1 | 0 | 0 | 0 | 0.00 |
| 6 | 4769 | 0 | 0 | 4769 | 1 | 0 | 0 | 0 | 0.00 |
| 7 | 11 | 1 | 1 | 12 | 1 | 0 | 0 | 0 | 0.00 |
| 8 | 9 | 8 | 1 | 9 | 1 | 0 | 0 | 0 | 0.00 |
| 9 | 3 | 0 | 0 | 3 | 1 | 0 | 0 | 0 | 0.00 |
| 10 | 2 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0.00 |
| 11 | 2160 | 14820 | 8 | 129 | 99 | 99 | 3753 | 3762 | 8.91 |
| 12 | 2090 | 14812 | 8 | 122 | 99 | 99 | 4098 | 4106 | 9.21 |
| 13 | 2135 | 14324 | 8 | 133 | 99 | 99 | 3613 | 3623 | 9.15 |
| 14 | 4 | 0 | 0 | 4 | 1 | 0 | 0 | 0 | 0.00 |
| 15 | 7 | 2 | 1 | 8 | 1 | 0 | 0 | 0 | 0.00 |
| 16 | 4987 | 28984 | 16 | 8172 | 99 | 99 | 8586 | 8594 | 33.63 |

## Analise

### Distribuicao do tempo (75% do encode em _detect_compositions)

| Componente | Self time | Cumulative |
|---|---:|---:|
| `_detect_compositions` (linha 225) | **34.6s** | 60.9s |
| `_estimate_baseline_chars` (364) | 8.0s | 15.4s |
| `<genexpr>` line 381 (dentro _est_baseline) | 1.6s | 1.6s |
| Outros syntax.py genexprs | ~1.4s | — |
| `_build_trace` + `_build_rede` | ~0.6s | ~0.6s |

### Por coluna — 4 colunas dominam (98% do tempo)

| Coluna | n_unicas | n_refs_total | n_iter_outer | tempo |
|---|---:|---:|---:|---:|
| l_shipdate | 2160 | 14820 | **99 (cap!)** | 8.9s |
| l_commitdate | 2090 | 14812 | **99 (cap!)** | 9.2s |
| l_receiptdate | 2135 | 14324 | **99 (cap!)** | 9.2s |
| l_comment | 4987 | 28984 | **99 (cap!)** | 33.6s |
| 12 outras | — | <10 cada | 1 | ~0s |

**Achado-chave**: as 4 colunas problema **SEMPRE batem cap de 99
iteracoes** outer. Cada iter processa milhares de candidates. Pra
l_comment: 99 × ~8500 candidates = 840k sub-counting + filter ops.

### Cadeia de gargalos

1. **Loop central de counting** (linhas 246-249):
   ```python
   for a in range(len(refs)):
       for b in range(a + 2, len(refs) + 1):
           sub = tuple(refs[a:b])
           contagem[sub] += 1
   ```
   Pra refs_max_len=16 → C(16,2)+C(15,2)+... = ~120 sub-tuplas por piece.
   l_comment: 5k linhas × 120 subs = 600k sub-tuplas por iter outer.
   × 99 iters = **60M sub-tuplas** geradas e contadas em 1 coluna.

2. **Recompute Counter from scratch a cada iter outer** — apos substituir
   uma sub por virtual_id, refazer TUDO. Maioria das subs nao mudou.

3. **`_estimate_baseline_chars` 1.1M chamadas** — usa `parts.extend(str(r)
   for r in run)` + `",".join(parts)` + `len(...)`. Pode ser
   counting direto (sem construir string).

4. **`_build_trace` + `_build_rede` SEMPRE rodam** apos `_detect_compositions`,
   mas resultados (em `self._trace` / `self._rede`) sao consumidos so'
   via `get_trace()` / `get_rede()` (usado apenas em dirty labs de debug,
   nunca no pipeline canonical).

### Hipoteses revisadas

| ID | Hipotese | Risco bytes | Ganho potencial |
|---|---|---|---|
| **H-PERF-05a (cache)** | Cache `_estimate_baseline_chars` por (sub, comp_acc_k) | zero | baixo (atom_count + comp_acc_k mudam) |
| **H-PERF-05b (counting direto)** | Reescrever `_estimate_baseline_chars` sem `parts+join+len` | zero | medio (~5-8s economizados) |
| **H-PERF-05c (skip trace)** | Flag `enable_trace=False` default; pular `_build_trace`/`_build_rede` | zero | baixo (~0.6s) MAS deixa de ordenar `candidates_sorted` no detect |
| **H-PERF-05d (counter incremental)** | Re-conta so' partes afetadas apos substituicao | zero | **alto** (~50-70% reducao em colunas grandes) |
| **H-PERF-05e (cap K)** | Limitar K maximo (K=6 ou 8 vs ate' 16) | **possivel byte loss** | medio (~30% reducao) |
| **H-PERF-05f (cap iter)** | Cap iter_traces=30 ou 50 vs 99 | **possivel byte loss** | medio |

### Decisao sub-exp 02

**Comecar zero-risk (b + c)**, validar bytes IDENTICOS, depois explorar
incremental (d) e por ultimo investigar cap (e/f) com medicao de
bytes perdidos.

Plano:
- v1: H-PERF-05b + 05c — counting direto + skip trace (zero-risk)
- v2: v1 + H-PERF-05d — counter incremental (zero-risk mas complexo)
- v3: v2 + H-PERF-05e — cap K com medicao de byte loss

### Aceite revisado

- v1: encode lineitem 5k <30s (vs 40.5s), bytes IDENTICOS
- v2: encode lineitem 5k <20s, bytes IDENTICOS
- v3: encode lineitem 5k <15s, byte loss <0.5% em real-world


