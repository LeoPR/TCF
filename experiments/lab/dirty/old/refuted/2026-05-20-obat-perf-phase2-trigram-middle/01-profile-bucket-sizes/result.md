# Sub-exp 01 — profile bucket sizes (lineitem 5k)

Dataset: lineitem 5000 rows x 16 cols

## Max bucket size por key (menor = melhor dispersao)

| coluna | n_unicas | prefix | suffix | middle | combined_ps | combined_full |
|---|---:|:---:|:---:|:---:|:---:|:---:|
| l_orderkey | 1241 | 9 | 2 | - | 1 | 1 |
| l_partkey | 1832 | 11 | 2 | - | 1 | 1 |
| l_suppkey | 100 | 1 | 1 | - | 1 | 1 |
| l_quantity | 50 | 1 | 5 | - | 1 | 1 |
| l_extendedprice | 4769 | 17 | 91 | 15 | 5 | 1 |
| l_shipdate | 2160 | 2160 | 78 | 247 | 78 | 9 |
| l_commitdate | 2090 | 2090 | 74 | 245 | 74 | 9 |
| l_receiptdate | 2135 | 2135 | 77 | 246 | 77 | 9 |
| l_comment | 4987 | 132 | 123 | 119 | 4 | 2 |

## Detalhe colunas grandes (>=500 unicas)

### l_orderkey (1241 unicas)

| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |
|---|---:|---:|---:|---:|---|---:|
| prefix | 377 | 9 | 3.2 | 2 | 9, 9, 9, 9, 9 | 0 (0%) |
| suffix | 1000 | 2 | 1.2 | 1 | 2, 2, 2, 2, 2 | 0 (0%) |
| combined_ps | 1214 | 1 | 1.0 | 1 | 1, 1, 1, 1, 1 | 0 (0%) |
| combined_full | 1214 | 1 | 1.0 | 1 | 1, 1, 1, 1, 1 | 0 (0%) |

### l_partkey (1832 unicas)

| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |
|---|---:|---:|---:|---:|---|---:|
| prefix | 825 | 11 | 2.1 | 1 | 11, 11, 11, 11, 11 | 813 (47%) |
| suffix | 988 | 2 | 1.8 | 2 | 2, 2, 2, 2, 2 | 0 (0%) |
| combined_ps | 1738 | 1 | 1.0 | 1 | 1, 1, 1, 1, 1 | 0 (0%) |
| combined_full | 1738 | 1 | 1.0 | 1 | 1, 1, 1, 1, 1 | 0 (0%) |

### l_extendedprice (4769 unicas)

| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |
|---|---:|---:|---:|---:|---|---:|
| prefix | 856 | 17 | 5.6 | 5 | 17, 16, 15, 15, 15 | 1281 (27%) |
| suffix | 190 | 91 | 25.1 | 19 | 91, 88, 87, 84, 83 | 4531 (95%) |
| middle | 1077 | 15 | 4.4 | 4 | 15, 15, 12, 12, 12 | 265 (6%) |
| combined_ps | 4232 | 5 | 1.1 | 1 | 5, 4, 4, 4, 4 | 0 (0%) |
| combined_full | 4769 | 1 | 1.0 | 1 | 1, 1, 1, 1, 1 | 0 (0%) |

### l_shipdate (2160 unicas)

| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |
|---|---:|---:|---:|---:|---|---:|
| prefix | 1 | 2160 | 2160.0 | 2160 | 2160 | 2160 (100%) |
| suffix | 31 | 78 | 69.7 | 70 | 78, 78, 75, 74, 73 | 2160 (100%) |
| middle | 14 | 247 | 154.3 | 204 | 247, 245, 243, 240, 239 | 2160 (100%) |
| combined_ps | 31 | 78 | 69.7 | 70 | 78, 78, 75, 74, 73 | 2160 (100%) |
| combined_full | 425 | 9 | 5.1 | 4 | 9, 9, 9, 9, 9 | 0 (0%) |

### l_commitdate (2090 unicas)

| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |
|---|---:|---:|---:|---:|---|---:|
| prefix | 1 | 2090 | 2090.0 | 2090 | 2090 | 2090 (100%) |
| suffix | 31 | 74 | 67.4 | 68 | 74, 73, 73, 73, 72 | 2090 (100%) |
| middle | 14 | 245 | 149.3 | 192 | 245, 242, 235, 235, 231 | 2090 (100%) |
| combined_ps | 31 | 74 | 67.4 | 68 | 74, 73, 73, 73, 72 | 2090 (100%) |
| combined_full | 417 | 9 | 5.0 | 4 | 9, 9, 9, 9, 9 | 0 (0%) |

### l_receiptdate (2135 unicas)

| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |
|---|---:|---:|---:|---:|---|---:|
| prefix | 1 | 2135 | 2135.0 | 2135 | 2135 | 2135 (100%) |
| suffix | 31 | 77 | 68.9 | 70 | 77, 74, 74, 73, 73 | 2135 (100%) |
| middle | 14 | 246 | 152.5 | 194 | 246, 240, 239, 238, 233 | 2135 (100%) |
| combined_ps | 31 | 77 | 68.9 | 70 | 77, 74, 74, 73, 73 | 2135 (100%) |
| combined_full | 430 | 9 | 5.0 | 4 | 9, 9, 9, 9, 9 | 0 (0%) |

### l_comment (4987 unicas)

| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |
|---|---:|---:|---:|---:|---|---:|
| prefix | 648 | 132 | 7.7 | 3 | 132, 68, 65, 53, 51 | 3642 (73%) |
| suffix | 647 | 123 | 7.7 | 3 | 123, 83, 65, 55, 47 | 3602 (72%) |
| middle | 657 | 119 | 7.6 | 3 | 119, 79, 64, 62, 58 | 3577 (72%) |
| combined_ps | 4787 | 4 | 1.0 | 1 | 4, 4, 3, 3, 3 | 0 (0%) |
| combined_full | 4986 | 2 | 1.0 | 1 | 2, 1, 1, 1, 1 | 0 (0%) |

## Resumo

Procurando: key onde max_bucket e' menor (especialmente em datas).
Quanto menor max_bucket, menos comparacoes por string nova.

**Datas TPC-H** (l_shipdate/commitdate/receiptdate): comparar
max_bucket de prefix vs middle vs combined_ps.

## Achados

### Datas TPC-H — combined_full e' o vencedor absoluto

| key | l_shipdate max | reducao vs prefix |
|---|---:|---:|
| prefix | 2160 | baseline (100% no MESMO bucket) |
| suffix | 78 | 27.7x |
| middle | 247 | 8.7x |
| combined_ps | 78 | 27.7x (= suffix, porque prefix `199` e' constante) |
| **combined_full** | **9** | **240x** |

**Por que prefix sozinho gera 2160**: TPC-H datas range 1992-1998,
prefixo `199` em todas — 1 bucket gigante.

**Por que combined_ps == suffix**: prefix constante `199` nao agrega
informacao, combined_ps efetivamente vira so suffix.

**Por que combined_full quebra isso**: adiciona middle (`-XX-` ou
similar), captura mes+dia, dispersa massivamente.

### Outras colunas — combined_full mantem perfeito

- l_orderkey, l_partkey, l_suppkey, l_quantity, l_comment, l_extendedprice:
  combined_full max 1-2 (essencialmente sem colisao)
- Custos: key 9-12 chars vs 3 chars. Hash mais caro, mas dispersao
  vence comparacoes O(N).

### Decisao para sub-exp 02

**Prototipo v4 (combined_full universal)**:
- key = `s[:3] + middle + s[-3:]` quando L >= 5
- key = `s[:3] + s[-3:]` quando 3 <= L < 5
- skip indexing quando L < 3

Esperado:
- Datas: **240x reducao em comparacoes** = encode 50-100x mais
  rapido nessas colunas (vs ADR-0009 que so' tinha 2x)
- Outras colunas: mantem speedup atual
- Pipeline lineitem 5k: 40s → 10-15s estimado

### Riscos

- **Mais memoria**: 2 indexes × keys 9-12 chars × N strings
- **Hash overhead**: Python hash em strings 9-12 chars vs 3 chars
  (mas dispersao muito melhor compensa)
- **Edge cases**: strings 3-4 chars (L<5 fallback)

