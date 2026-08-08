# Data lazy (spec ISO) — pré-tx no molde da nature do CPF

`n=500` por caso. **`rt`** = o round-trip completo (pré-tx → encode → decode →
pós-tx) devolve os dados **originais**, com tipo. É a prova que decide a viabilidade;
as colunas de byte só dizem se vale a pena.

| caso | % compressível | bytes hoje | bytes lazy | Δ | vence | RT |
|---|---:|---:|---:|---:|:-:|:-:|
| `limpo-diario` | 100.0% | 348 | 22 | -93.7% | **lazy** | ok |
| `limpo-mensal` | 100.0% | 4856 | 23 | -99.5% | **lazy** | ok |
| `limpo-espalhado` | 100.0% | 4592 | 3548 | -22.7% | **lazy** | ok |
| `sujo-01pct` | 99.0% | 1784 | 1488 | -16.6% | **lazy** | ok |
| `sujo-02pct` | 98.0% | 1807 | 1519 | -15.9% | **lazy** | ok |
| `sujo-05pct` | 95.0% | 1968 | 1692 | -14.0% | **lazy** | ok |
| `sujo-10pct` | 90.0% | 2210 | 1947 | -11.9% | **lazy** | ok |
| `sujo-25pct` | 75.0% | 2954 | 2409 | -18.4% | **lazy** | ok |
| `sujo-50pct` | 50.0% | 3403 | 3298 | -3.1% | **lazy** | ok |
| `com-nulo` | 95.0% | 782 | 407 | -48.0% | **lazy** | ok |
| `com-vazio` | 90.0% | 2084 | 2089 | +0.2% | hoje | ok |
| `misto-iso-br` | 75.0% | 3601 | 3403 | -5.5% | **lazy** | ok |
| `tudo-br` | 0.0% | 369 | 387 | +4.9% | hoje | ok |
| `ambiguo-br-us` | 100.0% | 418 | 425 | +1.7% | hoje | ok |
| `grafia-frouxa` | 99.8% | 1732 | 1442 | -16.7% | **lazy** | ok |
| `bissexto` | 100.0% | 212 | 198 | -6.6% | **lazy** | ok |
| `bissexto-invalido` | 66.7% | 212 | 209 | -1.4% | **lazy** | ok |
| `virada-ano` | 100.0% | 1758 | 22 | -98.7% | **lazy** | ok |
| `epoca-remota` | 100.0% | 125 | 109 | -12.8% | **lazy** | ok |

## Por que cada valor não foi comprimido

| caso | contagem por status |
|---|---|
| `limpo-diario` | — |
| `limpo-mensal` | — |
| `limpo-espalhado` | — |
| `sujo-01pct` | `comprimento`=5 |
| `sujo-02pct` | `comprimento`=10 |
| `sujo-05pct` | `comprimento`=25 |
| `sujo-10pct` | `comprimento`=50 |
| `sujo-25pct` | `comprimento`=125 |
| `sujo-50pct` | `comprimento`=250 |
| `com-nulo` | `nulo`=25 |
| `com-vazio` | `vazio`=50 |
| `misto-iso-br` | `nao-parseia`=125 |
| `tudo-br` | `nao-parseia`=500 |
| `ambiguo-br-us` | — |
| `grafia-frouxa` | `comprimento`=1 |
| `bissexto` | — |
| `bissexto-invalido` | `nao-parseia`=166 |
| `virada-ano` | — |
| `epoca-remota` | — |

## Onde a válvula de escape mata o ganho

| sujeira | % compressível | Δ bytes | vence |
|---|---:|---:|:-:|
| 01pct | 99.0% | -16.6% | lazy |
| 02pct | 98.0% | -15.9% | lazy |
| 05pct | 95.0% | -14.0% | lazy |
| 10pct | 90.0% | -11.9% | lazy |
| 25pct | 75.0% | -18.4% | lazy |
| 50pct | 50.0% | -3.1% | lazy |

---

**falhas de RT: 0**
