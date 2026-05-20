# 0009 — OBAT: hash index de trigramas em `_melhor_pref` / `_melhor_suf`

**Status**: accepted
**Date**: 2026-05-19
**Deciders**: project owner
**Tags**: performance, obat, indexing, h-perf-02, h-rw-05, src-tcf-canonical

## Context and Problem Statement

EXP-014 (2026-05-19) caracterizou encode pipeline em TPC-H lineitem
escalando como **O(N^1.75)**. Extrapolacao pra 60175 linhas: 71 min —
proibitivo pra iterativo.

Profile (sub-exp 01) confirmou H-PERF-01:
- `_melhor_pref` + `_melhor_suf` = **74% do tempo total** (192s/259s)
- 29.4M chamadas de `lcp_len`/`lcs_len`
- 216.7M chamadas de `len()` builtin
- HCC `_detect_compositions` = **24%** (segundo hotspot, nao tratado aqui)

Causa raiz: loop linear contra TODAS as strings anteriores a cada
nova string. Para min_len=3, qualquer match valido implica
`s[:3] == prev[:3]`, mas algoritmo nao explora isso.

## Considered Options

### Opcao A — Hash de trigramas (k=3)

`prefix_index[s[:3]] → list[ids]` + `suffix_index[s[-3:]] → list[ids]`.

Pra cada nova string, busca SO' candidatos com mesmo trigrama
inicial/final. Reduz O(N) → O(B) onde B = bucket size.

Bucket ordenado por insercao = ordem de id ascendente = preserva
tie-break `>` strict (primeira ocorrencia ganha em empate).

### Opcao B — Hash de bigramas (k=2)

Menos seletivo (buckets maiores) mas captura mais matches incluindo
strings de comprimento 2-3.

### Opcao C — Patricia trie ou suffix array

O(N log N) garantido, mas alocacao + manutencao mais complexa.
Overhead constante maior pra N pequeno.

### Opcao D — Eliminar `len()` redundantes apenas

Passa `len_a`/`len_b` como arg. Ganho modesto (1.3x sub-exp 02 v1).

### Opcao E — Otimizar HCC primeiro (24% do tempo)

Sub-exp 01 mostrou HCC como segundo hotspot. Justificativa pra
adiar: OBAT desbloqueia mais (74% > 24%) e e' mais bem entendido.

## Decision Outcome

**Opcao A — Hash de trigramas (k=3).**

Razoes:
1. **k=3 = min_len**: nenhum match valido escapa do bucket
2. **Preserva byte-canonical**: empirico em D1-D9 + lineitem 1k/5k
   (sub-exp 02 + 03)
3. **5.4x speedup global** em lineitem 5k em isolamento, 1.77x no
   pipeline completo (8/16 cols usam `processar_with_hint`)
4. **Codigo simples**: ~50 LOC adicionais, conceito direto
5. **Memoria aceitavel**: 2 dicts, ~2-4MB pra lineitem 5k

## Validacao empirica

### Sub-exp 02 (prototipos isolados)

RT 33/33 OK em D1-D9 + lineitem 1k+5k (todas variantes v1/v2/v3).

| Variante | Mudanca | Speedup lineitem 5k |
|---|---|---:|
| v0 | baseline | 1x |
| v1 | len-elim + slice-elim | 1.3x |
| v2 | + hash prefix | 1.8x |
| **v3** | + hash suffix | **5.4x** |

Por coluna em 5k:
- l_partkey: 264x
- l_orderkey: 200x
- l_extendedprice: 132x
- l_comment: 100x
- l_shipdate/commitdate/receiptdate: 2x (buckets grandes por
  prefixos `199`/`200`/`202`)

### Sub-exp 03 (pipeline completo, monkey-patched)

| Dataset | Bytes esperados | Bytes obtidos | Match |
|---|---:|---:|---|
| D1-D9 (total) | 1,615 | **1,615** | OK |
| lineitem 1k | 102,366 | **102,366** | OK |
| lineitem 5k | 498,271 | **498,271** | OK |

Encode time lineitem 5k: 40.78s (vs 71.5s baseline = **1.77x**).

### EXP-014 (lineitem scale) pos-welding

| Volume | Antes (alpha=1.75) | Depois (alpha=1.42) | Speedup |
|---:|---:|---:|---:|
| 1,000 | 10.2s | 7.9s | 1.3x |
| 5,000 | 71.5s | 40.5s | 1.77x |
| 10,000 | 186.9s | 86.6s | 2.16x |
| 20,000 | 626.5s | 232.0s | **2.70x** |

**Speedup AUMENTA com escala** — exato o esperado pra otimizacao
atacar componente quadratico.

Bytes IDENTICOS em todos volumes (102366 / 498271 / 1003986 / 2048101).

**Lineitem full 60175 estimado**: 71 min → **18.5 min** (-74%).

### Pos-welding validacao multi-camada

| Camada | Antes | Depois |
|---|---|---|
| EXP-007 (D1-D9) | 1615B, 9/9 OK | **1615B, 9/9 OK** |
| EXP-010 (20 datasets) | RT 20/20 | **RT 20/20** |
| EXP-011 (D17a) | RT OK | **RT OK** |
| EXP-012 (Adult 4 vol) | RT 4/4 | **RT 4/4** |
| EXP-013 (TPC-H 8 tabs) | RT 8/8 | **RT 8/8** |
| **EXP-014 (lineitem scale)** | alpha=1.75 | **alpha=1.42** (estimativa 60175 caiu 71min → 18.5min) |

Zero regressao byte-canonical em todos cenarios.

## Pros and Cons

| Opcao | Pros | Cons |
|---|---|---|
| **A (hash k=3)** | Empirico 5.4x, simples, preserva byte-canonical | Buckets grandes em datas (2x apenas) |
| B (hash k=2) | Mais seletivo p/ strings curtas | Buckets maiores em geral, complexidade extra |
| C (Patricia trie) | O(N log N) garantido | Implementacao complexa, alocacao custosa |
| D (len-elim apenas) | Trivial | So 1.3x — insuficiente |
| E (HCC primeiro) | Endereca 2o hotspot | Menor ganho (24%); OBAT mais bem entendido |

## Implementacao

Welded em:
- `src/tcf/core/online.py` — versao indexada de `_melhor_pref`/`_melhor_suf`/`_escolher_par` + indexes mantidos em `processar`
- `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/obat_shape.py` — adaptado pra nova assinatura indexed de `_escolher_par`

API publica preservada: `lcp_len(a, b)`, `lcs_len(a, b)`, `processar(strings_unicas, min_len=3)`.

### Garantia byte-canonical

- Iteracao em ordem de id ascendente (insercao em bucket = id ascendente)
- Tie-break `>` strict mantido (primeira ocorrencia vence em empate)
- `_escolher_par` mantem ordem de candidatos: tie por cobertura → mais pref

## Riscos residuais

- **Memoria**: para datasets gigantes (>10M strings), indexes podem ficar
  grandes. Sem cap atual. Aceitavel pra batch encoding; rever se for
  problema empirico.
- **Buckets grandes**: datas TPC-H tem prefixos `199`/`200`/`202`,
  reduz benefit a 2x. Otimizacao futura: trigrama de **meio**
  (`s[len(s)//2-1:len(s)//2+2]`).
- **HCC ainda e' 24% do tempo**: encode lineitem 5k caira de 71s pra
  ~40s. HCC vira gargalo relativo. Tratamento em sub-exp/lab futuro.

## Hipoteses decorrentes

- **H-PERF-04** (aberta): trigrama de meio reduz buckets em datas
  (~2x → 5x+ esperado em l_shipdate)
- **H-PERF-05** (aberta): otimizar HCC `_detect_compositions` (24%
  tempo) via dynamic-programming ou estrutura indexada
- **H-PERF-06** (aberta): Cython / Rust port de `lcp_len`/`lcs_len`
  pra cortar Python overhead

## Cross-references

- [ADR-0003](0003-tripartite-pre-obat-hcc.md) — tripartite pre+obat+hcc
- [Sub-exp 01 (profile)](../../experiments/lab/dirty/2026-05-19-obat-perf-optimization/01-profile-baseline/)
- [Sub-exp 02 (prototipos)](../../experiments/lab/dirty/2026-05-19-obat-perf-optimization/02-index-prototypes/)
- [Sub-exp 03 (welding)](../../experiments/lab/dirty/2026-05-19-obat-perf-optimization/03-welding-decision/)
- [EXP-014 (lineitem scale)](../../experiments/lab/clean/EXP-014-tpch-lineitem-scale/) — caracterizacao O(N^1.75)
- [OBAT spec](../algorithms/OBAT.md)
