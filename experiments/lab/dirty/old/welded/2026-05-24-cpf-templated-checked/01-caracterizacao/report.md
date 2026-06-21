# Sub-exp 01 — Caracterizacao baseline M10 (report)

## Resultados

| dataset | rows | raw | m10 | ratio | b/CPF raw | b/CPF m10 | cadence | min_len | rle_runs |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|---:|
| D-CPF-uniform | 1000 | 15000 | 18936 | 126.24% | 15.00 | 18.94 | False | 6 | 0 |
| D-CPF-clustered | 1000 | 15000 | 18042 | 120.28% | 15.00 | 18.04 | False | 6 | 0 |
| D-CPF-mixed | 1000 | 13500 | 16304 | 120.77% | 13.50 | 16.30 | False | 6 | 170 |
| D-CPF-corrupt | 1000 | 14985 | 18959 | 126.52% | 14.98 | 18.96 | False | 6 | 0 |

## Interpretacao

- **D-CPF-uniform** (126.2%): CPFs uniformes aleatorios. M10 captura pouco — sem padrao administrativo, OBAT/HCC nao acha refs significativos.
- **D-CPF-clustered** (120.3%): 3 digitos compartilhados em blocos de 100. M10 deveria capturar prefix comum via OBAT — comparar com uniform.
- **D-CPF-mixed** (120.8%): 50% formatados / 50% sem mascara. Dois 'sub-padroes' coexistindo.
- **D-CPF-corrupt** (126.5%): 5% corruptos. M10 trata todos como string normal — mistura nao prejudica nem ajuda.

## Observacoes pre-pass

- **D-CPF-uniform**: cadence=False (rule=None), min_len=6, is_numeric=False, seq_rle_runs=0
- **D-CPF-clustered**: cadence=False (rule=None), min_len=6, is_numeric=False, seq_rle_runs=0
- **D-CPF-mixed**: cadence=False (rule=None), min_len=6, is_numeric=False, seq_rle_runs=170
- **D-CPF-corrupt**: cadence=False (rule=None), min_len=6, is_numeric=False, seq_rle_runs=0

## Conclusao parcial

Baseline M10 medido. Sub-exps 02/03/04 vao comparar:
- Variante A (raw, igual a 01)
- Variante B (base-encoded)
- Variante C (hibrido strip-marcadores)

