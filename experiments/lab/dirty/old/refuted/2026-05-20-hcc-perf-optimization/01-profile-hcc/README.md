# Sub-exp 01 — profile HCC `_detect_compositions`

**Objetivo**: profile detalhado pra entender onde HCC consome tempo
dentro de `_detect_compositions`. Decidir abordagem de otimizacao.

## Metodo

1. cProfile pipeline encode em lineitem 5k (ja' caracterizado)
2. Print stats focados em `syntax.py`
3. Adicionar prints de scale dentro de `_detect_compositions`:
   - N iteracoes do outer loop
   - N subs unique counted
   - N candidates por iteracao
   - K distribution (tamanhos de sub)
4. Pra cada coluna lineitem, salvar:
   - Total tempo em HCC
   - N outer iterations
   - N candidates total

## Aceite

- Identificar top 3 hotspots dentro de syntax.py
- Quantificar escala (N=quantos itens em cada loop)
- Decisao informada pra sub-exp 02 (qual H-PERF-05a..e prototipar)
