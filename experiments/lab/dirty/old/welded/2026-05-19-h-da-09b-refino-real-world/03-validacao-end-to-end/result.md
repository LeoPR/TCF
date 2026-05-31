# Sub-exp 03 — Validacao end-to-end (heuristica v2)

## Resumo

| Label | raw | v1 (current) | v2 (refinada) | Δ v2 vs v1 | RT v2 |
|---|---:|---:|---:|---:|---|
| `adult vol=100` | 10,895 | 4,571 (cad=0/15) | 4,576 (cad=6/15) | +5 | OK |
| `adult vol=500` | 54,079 | 20,436 (cad=0/15) | 20,242 (cad=6/15) | -194 | OK |
| `adult vol=1000` | 108,226 | 40,386 (cad=0/15) | 39,615 (cad=6/15) | -771 | OK |
| `adult vol=5000` | 539,921 | 212,776 (cad=0/15) | 193,010 (cad=6/15) | -19,766 | OK |
| `tpch.region n=5` | 415 | 429 (cad=0/3) | 429 (cad=1/3) | +0 | OK |
| `tpch.nation n=25` | 2,252 | 2,213 (cad=0/4) | 2,213 (cad=2/4) | +0 | OK |
| `tpch.supplier n=100` | 13,848 | 12,555 (cad=1/7) | 12,556 (cad=4/7) | +1 | OK |
| `tpch.customer n=1500` | 241,155 | 213,661 (cad=1/8) | 210,428 (cad=4/8) | -3,233 | OK |
| `tpch.part n=2000` | 235,202 | 148,833 (cad=3/9) | 147,639 (cad=5/9) | -1,194 | OK |
| `tpch.partsupp n=5000` | 723,936 | 766,475 (cad=0/5) | 721,666 (cad=4/5) | -44,809 | OK |
| `tpch.orders n=5000` | 545,678 | 478,982 (cad=1/9) | 435,033 (cad=4/9) | -43,949 | OK |
| `tpch.lineitem n=5000` | 601,788 | 519,999 (cad=0/16) | 498,271 (cad=8/16) | -21,728 | OK |

## Totais

- raw:  3,077,395 B
- v1:   2,421,316 B  (78.7%)
- **v2**:  **2,285,678 B  (74.3%)**
- **v2 melhor que v1 por**: **+135,638 B**

RT v2: 12/12