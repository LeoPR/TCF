# Sub-exp 02 — index prototypes (resultado)

## Resumo executivo

**Winner: v3 (hash prefix + suffix index)**
- **5.4x speedup global** em lineitem 5k (weighted)
- **100-264x em colunas categoricas/numericas** (l_partkey, l_comment)
- **2x em colunas datetime** (l_shipdate etc — buckets grandes)
- **RT 33/33 OK** em D1-D9 + lineitem 1k + lineitem 5k (todas variantes)
- **Zero risco byte-canonical** confirmado empirico

## Variantes testadas

| ID | Otimizacao | Mudanca |
|---|---|---|
| v0 | baseline | copia exata de src/tcf/core/online.py |
| v1 | len-elim + slice-elim | pre-computa `lens`, evita `strings[:idx]`, passa `la`/`lb` |
| v2 | + hash prefix | v1 + indexa por `s[:3]` (trigrama) |
| v3 | + hash suffix | v2 + indexa por `s[-3:]` |

## Correctness (RT 33/33)

Todas variantes produzem **tokens IDENTICOS** a v0 em:
- D1-D9 sinteticos (9/9 OK)
- lineitem 1k per-col (16/16 OK)
- lineitem 5k per-col (8/8 OK em colunas com >100 unicas)

Garantia: iteracao em ordem de id ascendente preserva tie-break
strict `>` (primeira ocorrencia ganha).

## Performance (lineitem 5k)

| Coluna | n_unicas | v0 | v1 | v2 | **v3** | speedup v3/v0 |
|---|---:|---:|---:|---:|---:|---:|
| l_orderkey | 1241 | 1.4s | 981ms | 524ms | **7.07ms** | **200x** |
| l_partkey | 1832 | 2.9s | 2.4s | 1.2s | **11ms** | **264x** |
| l_suppkey | 100 | 6.7ms | 5.8ms | 2.8ms | **0.19ms** | 35x |
| l_extendedprice | 4769 | 18.7s | 14.7s | 8.1s | **142ms** | **132x** |
| l_shipdate | 2160 | 8.5s | 7.1s | 6.6s | **4.4s** | 2x |
| l_commitdate | 2090 | 8.1s | 6.6s | 6.5s | **3.9s** | 2x |
| l_receiptdate | 2135 | 8.5s | 6.9s | 6.5s | **4.2s** | 2x |
| l_comment | 4987 | 20.9s | 16.4s | 8.9s | **210ms** | **100x** |
| **Total** | — | **69.1s** | 55.0s | 38.4s | **12.8s** | **5.4x** |

## Analise

### Por que v3 ganha massivamente em colunas categoricas/numericas

Trigramas inicial/final dispersam bem em strings numericas (`"123"`,
`"456"`) e comentarios variados. Bucket size pequeno (esperado ~N/K
onde K = numero de trigramas distintos). Lookup vira praticamente
O(1).

### Por que datas sao "so" 2x

Datas TPC-H tem prefixos repetitivos:
- `"199"`, `"200"`, `"202"` para anos
- `"-01"`, `"-02"`, etc. para meses (final)
- Buckets grandes (centenas de strings compartilham mesmo trigrama)
- Hash ainda ajuda (2x) mas nao tanto quanto colunas dispersas

Otimizacao futura (v4 nao testado): trigrama de **meio**
(`s[len(s)//2 - 1:len(s)//2 + 2]`) pode dispersar melhor pra datas.
**NAO necessario agora** — 5.4x global ja' atinge aceite (>5x).

### Por que v1 sozinho da' 1.3x

Eliminar `len()` redundantes corta self-time de built-ins mas o
loop O(N) por iteracao continua dominando. Otimizacao idiomatica
sem mudar algoritmo = ganho modesto.

### Why v2 (so prefix) da' 1.8x mas v3 (pref+suf) da' 5.4x

`_melhor_suf` era ainda mais caro que `_melhor_pref` (108s vs 83s
no profile original — sufixos dominantes em strings UTF-8 com
backtracking). Eliminar ambos era necessario.

## Custos

### Memoria

`prefix_index` + `suffix_index` = 2 dicts com entradas (~N/K cada).
Para lineitem 5k:
- ~16 colunas × 5000 strings = 80k entries por index
- ~2-4 MB total (estimativa)
- Aceitavel para encode em batch

### Codigo

- +50 linhas em `online.py` (3 funcoes novas + 2 indexes mantidos)
- Complexidade conceitual: baixa (apenas hash + iteracao filtrada)

## Decisao para sub-exp 03

**Promover v3 a canonical via welding em `src/tcf/core/online.py`.**

Plano sub-exp 03:
1. Validacao end-to-end pipeline (EXP-007/010/011/012/013) com v3
   substituindo OBAT — bytes IDENTICOS esperados
2. Re-run EXP-014 com v3 — esperar alpha < 1.5 (linear-ish)
3. Welding em src/tcf (somente apos validacao 100% OK)
4. ADR-0009 documentando otimizacao

### Riscos remanescentes

- **Memoria**: para datasets enormes (milhoes de strings), indexes
  podem ficar grandes. Sem cap atual. Aceitar — pre-otimizar nao
  vale se 5.4x ja' destrava lineitem full.
- **HCC ainda e' 24%**: encode lineitem 5k cai de 71s pra ~14s.
  HCC vira gargalo relativo (~10s). Otimizar HCC = sub-exp futuro
  (fora deste lab).
