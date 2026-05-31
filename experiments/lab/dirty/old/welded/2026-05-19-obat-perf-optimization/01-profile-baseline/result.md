# Sub-exp 01 — profile baseline (resultado)

**Dataset**: lineitem 5000 rows × 16 colunas
**Encode time (com cProfile overhead)**: 258.6s
**Encode time real (EXP-014, sem overhead)**: 71.5s
**Bytes TCF**: 498,271
**Cadence detected**: 8/16 colunas

## Top 30 por cumulative time (snapshot reduzido)

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.006    0.006  258.619  258.619 multi_col.py:44(encode_table)
       16    0.004    0.000  258.612   16.163 delta_aware.py:45(encode_column)
        8    0.475    0.059  192.417   24.052 online.py:134(processar)        ← OBAT
    11391    0.068    0.000  191.740    0.017 online.py:85(_escolher_par)
    18646   23.820    0.001  108.149    0.006 online.py:75(_melhor_suf)
    18646   23.923    0.001   83.484    0.004 online.py:61(_melhor_pref)
 29371792   50.177    0.000   78.522    0.000 online.py:53(lcs_len)
       16    0.176    0.011   65.908    4.119 hcc_seqrle.py:210(encode)       ← HCC
       16    0.013    0.001   65.319    4.082 syntax.py:646(encode)
       16   35.382    2.211   63.120    3.945 syntax.py:225(_detect_compositions)
 29371792   37.122    0.000   53.591    0.000 online.py:45(lcp_len)
216688563   40.106    0.000   40.106    0.000 {built-in method builtins.len}
117471154   23.464    0.000   23.464    0.000 {built-in method builtins.min}
  1116611    8.498    0.000   16.359    0.000 syntax.py:364(_estimate_baseline_chars)
```

## Top 10 por tottime (self time)

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
 29371792   50.177    0.000   78.522    0.000 online.py:53(lcs_len)
216688563   40.106    0.000   40.106    0.000 {built-in method builtins.len}
 29371792   37.122    0.000   53.591    0.000 online.py:45(lcp_len)
       16   35.382    2.211   63.120    3.945 syntax.py:225(_detect_compositions)
    18646   23.923    0.001   83.484    0.004 online.py:61(_melhor_pref)
    18646   23.820    0.001  108.149    0.006 online.py:75(_melhor_suf)
117471154   23.464    0.000   23.464    0.000 {built-in method builtins.min}
  1116611    8.498    0.000   16.359    0.000 syntax.py:364(_estimate_baseline_chars)
```

## Analise

### Distribuicao de tempo (cumulative, % de 258.6s total)

| Componente | Tempo | % |
|---|---:|---:|
| **OBAT** (`processar`) | 192.4s | **74.4%** |
| ↳ `_melhor_suf` (cumulative) | 108.1s | 41.8% |
| ↳ `_melhor_pref` (cumulative) | 83.5s | 32.3% |
| ↳ `lcs_len` (self) | 50.2s | 19.4% |
| ↳ `lcp_len` (self) | 37.1s | 14.3% |
| **HCC** (`hcc_seqrle.encode` + `syntax.encode`) | 65.9s | **25.5%** |
| ↳ `_detect_compositions` (self) | 35.4s | 13.7% |
| ↳ `_estimate_baseline_chars` | 16.4s | 6.3% |
| Resto (auto_pre + I/O + outros) | ~0.3s | <1% |

### H-PERF-01 — CONFIRMADA empirica

> `_melhor_pref` + `_melhor_suf` dominam (>60%).

**Combinados cumulative**: 191.6s = **74% do tempo total**. Confirmado.

### Diagnostico fino

**Funcoes "atomicas" mais quentes** (self time):
1. `lcs_len`: 50.2s em 29.4M chamadas → **1.7 us/chamada**
2. `lcp_len`: 37.1s em 29.4M chamadas → 1.3 us/chamada
3. `len()` builtin: 40.1s em **216.7M chamadas** → muitas redundantes
4. `min()` builtin: 23.5s em **117.5M chamadas**

29.4M chamadas de `lcs_len`/`lcp_len` por **8 colunas com processar**
(restante 8 usa `processar_with_hint`, mais barato). Isso vem do
loop dentro de `_melhor_pref`/`_melhor_suf` iterando todas anteriores.

**Estimativa do loop**: 18646 chamadas combinadas de `_melhor_pref`+`_suf`,
gerando ~29M `lcp_len`/`lcs_len`. Ratio: ~1500 anteriores/chamada
em media (consistente com N grande nas colunas categoricas).

### H-PERF-01b (novo) — HCC `_detect_compositions` e' o **segundo** hotspot

Nao previsto na hipotese original. HCC consome 24% do tempo. Mesmo
otimizando OBAT 10x, encode cai pra ~85s (linear OBAT 5s + HCC 65s).
Para ganho global >5x precisa otimizar AMBOS.

Cadeia de chamadas no syntax.py (`_detect_compositions`):
- Chama `_estimate_baseline_chars` (1.1M vezes, 16.4s)
- 4.3M genexpr calls em line 381 (custo 1.6s)
- Suggests: busca quadratica de candidatos de composicao

### Decisao para sub-exp 02

**Focar em OBAT primeiro** (maior ganho, ja' compreendido):

1. **H-PERF-02 (proposta)**: hash de prefixos/sufixos por bigramas
   - `prefix_index[s[:k]] → list[string_id]` (k=2 ou 3)
   - `_melhor_pref` consulta `prefix_index[novo[:k]]` → so' compara
     contra esses candidatos
   - Suffix analogo: `suffix_index[s[-k:]]`
   - Custo update: O(1) por string
   - Custo lookup: O(B) onde B=bucket size (esperado <<N)
   - Preserva byte-canonical SE empate continuar resolvendo a favor
     do menor id (mesma escolha tie-break)

2. **Otimizacoes secundarias** (low-hanging, sem mudar algoritmo):
   - `lcp_len`/`lcs_len`: passar `len_a`/`len_b` como arg pra evitar
     `len()` redundante (potencial: ~30% das chamadas `len()`)
   - Substituir loop while por `os.path.commonprefix` ou similar? (testar)
   - Substituir `min(max_len, lcp_len(...))` por `lcp_len(... max_len)` →
     evita 1 min e n iteracoes alem do cap

3. **HCC `_detect_compositions`** (sub-exp futuro, nao agora)

### Riscos byte-canonical

Qualquer otimizacao precisa preservar:
- **Same string_id chosen** em empates (atual: menor id por iteracao
  natural `for i, prev in enumerate(anteriores)`)
- **Same length** sempre (max length valida)
- **Same prefix/suffix preference** em `_escolher_par`

Hash de bigramas preserva isso SE itera buckets em ordem de id
ascendente (ordenar bucket por insercao).

## Proximos passos

**Sub-exp 02** (a abrir):
- `02-index-prototypes/`
  - `01-hash-prefix.py`: prototipo hash[bigram] → ids, mede ganho
  - `02-hash-prefix-suffix.py`: estende pra ambos
  - `03-len-redundancy-elim.py`: passa len_a/len_b como arg
  - Validacao: byte-canonical em D1-D9 (1615 bytes) + RT em
    lineitem 1k subset

**Aceite sub-exp 02**:
- Pelo menos 1 prototipo: encode 5x mais rapido em lineitem 5k SEM
  mudar bytes em D1-D9
- Documentar trade-offs (memoria, k otimo, etc.)
