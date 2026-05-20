# Sub-exp 01 — profile baseline OBAT (lineitem 5000)

**Objetivo**: identificar hotspots do pipeline encode (OBAT + HCC)
via cProfile. Decidir onde otimizar antes de propor solucao.

## Pergunta

Dado encode O(N^1.75) em EXP-014, **qual funcao domina tempo
cumulativo?** Hipotese H-PERF-01: `_melhor_pref` + `_melhor_suf`
juntos > 60%.

## Dataset

`lineitem` 5000 rows (16 colunas). Mesmo dataset usado em EXP-014.
Tempo esperado: ~71s (encode), suficiente pra cProfile sem cap.

## Metodo

1. `DatasetReader("tpch-sf001").rows("lineitem", limit=5000)`
2. `cProfile.run(encode_table)` → 16 colunas processadas
3. Dump stats:
   - Top 30 por `cumulative time`
   - Top 30 por `tottime` (self time)
   - Caller stats das top 3
4. Salvar `.prof` binario + texto em `result.md`

## Aceite

- Identificar top-3 funcoes (>50% tempo cumulativo)
- Confirmar ou refutar H-PERF-01
- Documentar contagem de chamadas vs tempo por chamada

## Output

- `profile.py` — script
- `baseline.prof` — pstats binary
- `result.md` — analise + decisoes
