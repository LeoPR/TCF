# O custo da ambiguidade de data

`n=480` por caso. **Todas as datas são ambíguas** (dia e mês ≤ 12): a mesma string tem leitura válida em BR e em US.

| caso | ignorar (hoje) | spec CERTO | spec ERRADO | custo bruto | **com FLOOR** | vs hoje | RT |
|---|---:|---:|---:|---:|---:|---:|:-:|
| `consecutivo-no-mes` | 852 | 529 | 3159 | 497.2% | **852** | **0.0%** | ok |
| `consecutivo-no-mes-espelhado` | 849 | 3159 | 529 | -83.3% | **529** | **-37.7%** | ok |
| `ambiguo-sem-ordem` | 1816 | 1669 | 1667 | -0.1% | **1667** | **-8.2%** | ok |
| `ambiguo-k12` | 399 | 411 | 411 | 0.0% | **399** | **0.0%** | ok |

A coluna **com FLOOR** é `min(spec errado, ignorar)` — o que sai se o spec entrar como **candidato** em vez de substituto. **`vs hoje` é o prejuízo real da ambiguidade.**

## O que cada caso é

| caso | por quê |
|---|---|
| `consecutivo-no-mes` | dias 1..12 correndo — REGULAR lido como BR, espalhado lido como US |
| `consecutivo-no-mes-espelhado` | o espelho: REGULAR lido como US, espalhado lido como BR |
| `ambiguo-sem-ordem` | dia e mês ≤ 12 sem ordem — nenhuma leitura ganha regularidade |
| `ambiguo-k12` | 12 datas cicladas, todas ambíguas |

---

**falhas de RT: 0**
