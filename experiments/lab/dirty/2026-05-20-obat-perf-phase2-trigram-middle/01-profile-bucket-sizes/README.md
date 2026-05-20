# Sub-exp 01 — profile bucket sizes (caracterizar problema)

**Objetivo**: medir distribuicao de bucket sizes pra trigramas
diferentes em colunas lineitem (5000 rows). Decidir abordagem antes
de prototipar.

## Pergunta

Pra cada coluna, qual key (prefix/suffix/middle/combined) gera
buckets mais finos?

## Metodo

Calcula:
1. `prefix_index[s[:3]]` — atual (referencia)
2. `suffix_index[s[-3:]]` — atual (referencia)
3. `middle_index[s[(L-3)//2:(L-3)//2+3]]` — proposta H-PERF-04a
4. `combined_index[s[:3] + s[-3:]]` — proposta H-PERF-04b
5. `combined_full[s[:3] + middle + s[-3:]]` — combinacao maxima

Estatisticas por key:
- N buckets
- max bucket size
- avg bucket size (so' buckets >= 2)
- # strings em bucket >= 10 (alvo seriam matches caros)

## Aceite

- Tabela comparativa por coluna mostrando winners
- Decisao informada pra sub-exp 02 (qual variante prototipar primeiro)

## Output

- `profile.py` — script
- `result.md` — analise
