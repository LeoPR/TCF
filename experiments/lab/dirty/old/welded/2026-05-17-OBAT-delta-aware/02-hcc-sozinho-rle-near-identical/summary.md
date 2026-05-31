# Resultado — Tentativa 02 (HCC sozinho seq-RLE)

## Tabela

| Dataset | rows | unicas | canon (B) | fork (B) | Δ (B) | Δ (%) | runs | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| [D11a-datas-dia](D11a-datas-dia/3-diff-canonical-vs-fork.md) | 12 | 12 | 87 | 84 | -3 | -3.4% | 2 | OK |
| [D11b-datas-borda](D11b-datas-borda/3-diff-canonical-vs-fork.md) | 14 | 14 | 173 | 173 | +0 | +0.0% | 0 | OK |
| [D11c-datas-mensal](D11c-datas-mensal/3-diff-canonical-vs-fork.md) | 13 | 13 | 109 | 78 | -31 | -28.4% | 1 | OK |
| [D11d-datetime-min](D11d-datetime-min/3-diff-canonical-vs-fork.md) | 13 | 13 | 110 | 73 | -37 | -33.6% | 1 | OK |
| [D11e-datetime-mensal](D11e-datetime-mensal/3-diff-canonical-vs-fork.md) | 13 | 13 | 121 | 90 | -31 | -25.6% | 1 | OK |
| [D11f-datetime-ms](D11f-datetime-ms/3-diff-canonical-vs-fork.md) | 13 | 13 | 115 | 78 | -37 | -32.2% | 1 | OK |
| [D11g-datetime-us](D11g-datetime-us/3-diff-canonical-vs-fork.md) | 13 | 13 | 120 | 83 | -37 | -30.8% | 1 | OK |
| [D11h-datetime-ns](D11h-datetime-ns/3-diff-canonical-vs-fork.md) | 13 | 13 | 123 | 86 | -37 | -30.1% | 1 | OK |

## Resumo

- Total canonical: 958 bytes
- Total fork:      745 bytes
- Delta total:     -213 bytes (-22.2%)
- RT: 8/8 OK

## Para analise detalhada por dataset, ver `outputs/<ds>/`

Sintese final + revisao de Q15 em `result.md` (proxima etapa).

