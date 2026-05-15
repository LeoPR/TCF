# Apendice D: Comparacao Detalhada de Formatos

Comparacao lado a lado dos formatos testados, com exemplos reais.

## D.1 Dados de Exemplo

5 vendas (subset para visualizacao):

```
Ana comprou Caneta por 2.50
Ana comprou Caneta por 3.00
Ana comprou Lapis por 1.00
Bruno comprou Caneta por 11.00
Bruno comprou Borracha por 2.90
```

## D.2 CSV (row-oriented)

```csv
pessoa,produto,total
Ana,Caneta,2.50
Ana,Caneta,3.00
Ana,Lapis,1.00
Bruno,Caneta,11.00
Bruno,Borracha,2.90
```

**Tamanho:** ~100 chars
**Familiar para LLMs:** Sim (alto volume no treinamento)
**Repeticao:** "Ana" aparece 3x, "Caneta" 3x — sem compressao

## D.3 JSONL (row-oriented, self-describing)

```json
{"pessoa":"Ana","produto":"Caneta","total":2.50}
{"pessoa":"Ana","produto":"Caneta","total":3.00}
{"pessoa":"Ana","produto":"Lapis","total":1.00}
{"pessoa":"Bruno","produto":"Caneta","total":11.00}
{"pessoa":"Bruno","produto":"Borracha","total":2.90}
```

**Tamanho:** ~250 chars
**Familiar:** Sim
**Repeticao:** Chaves "pessoa","produto","total" repetidas 5x = 2.5x maior que CSV

## D.4 Markdown Table (row-oriented, visual)

```markdown
| pessoa | produto | total |
|--------|---------|-------|
| Ana | Caneta | 2.50 |
| Ana | Caneta | 3.00 |
| Ana | Lapis | 1.00 |
| Bruno | Caneta | 11.00 |
| Bruno | Borracha | 2.90 |
```

**Tamanho:** ~200 chars
**Familiar:** Sim (muito Markdown no treinamento)
**Repeticao:** Pipes e hifens adicionam overhead visual sem informacao

## D.5 TCF Level 0 (columnar, expanded)

```
## vendas n=5
pessoa:
Ana
Ana
Ana
Bruno
Bruno
produto:
Caneta
Caneta
Lapis
Caneta
Borracha
total:
2.50
3.00
1.00
11.00
2.90
```

**Tamanho:** ~110 chars
**Familiar:** Parcial (Markdown headers, mas layout columnar e novo)
**Vantagem:** Valores de mesma coluna agrupados — soma e scan sao triviais

## D.6 TCF Level 2 (sorted + RLE)

```
# TCF v0.2 level=2
# N*val = val repeated N times

## vendas n=5 sorted_by=pessoa
pessoa:
3*Ana
2*Bruno
produto:
Caneta
Caneta
Lapis
Caneta
Borracha
total:
2.50
3.00
1.00
11.00
2.90
```

**Tamanho:** ~105 chars (com header)
**Compressao:** pessoa: 5 valores → 2 grupos RLE
**Nota:** Dados reordenados por `pessoa` (Ana primeiro, Bruno depois)

## D.7 TCF Level 3 (dict + sorted + RLE)

```
# TCF v0.2 level=3
# N*val = val repeated N times

## vendas n=5 sorted_by=pessoa
# dict pessoa: Ana,Bruno
# dict produto: Caneta,Lapis,Borracha
pessoa:
3*0
2*1
produto:
0
0
1
0
2
total:
2.50
3.00
1.00
11.00
2.90
```

**Tamanho:** ~95 chars
**Compressao:** Nomes → indices (0=Ana, 1=Bruno). Max compressao.
**Tradeoff:** Indices confundem LLMs em perguntas FK (F23: L3 = 53% vs L0 = 67%)

## D.8 Tabela Comparativa

| Formato | Tamanho (5 rows) | Tamanho (500 rows) | LLM Accuracy | Tipo |
|---------|-----------------|--------------------|--------------| ------|
| JSONL | ~250 | ~62KB | 19% | Row, self-describing |
| MD Table | ~200 | ~35KB | nao testado | Row, visual |
| CSV | ~100 | ~18KB | 19% | Row, compacto |
| TCF L0 | ~110 | ~20KB | **49%** | Column, expanded |
| TCF L2 | ~105 | ~18KB | 36% | Column, sorted+RLE |
| TCF L3 | ~95 | ~12KB | 27%* | Column, dict+RLE |

*L3 accuracy varia: 53% com dados pequenos, menor em escala.
Accuracy de LLMs medida em Etapa 2 (12 modelos, retail_200).
Fonte: [article/07-results-e4-e8.md](../07-results-e4-e8.md)

## D.9 Quando Usar Cada Formato

| Cenario | Formato recomendado | Razao |
|---------|--------------------|----- -|
| Poucos dados (< 50 rows) | CSV ou MD Table | Familiar, sem overhead |
| Dados medios (50-500 rows) | **TCF L2** | Melhor accuracy + compressao |
| Dados grandes (500+ rows) | **TCF L2** ou L3 | CSV/JSONL colapsam em escala |
| Max compressao (armazenamento) | TCF L3 | 32-47% menor que CSV |
| LLM precisa de nomes (FK queries) | TCF L0 ou L2 | Nomes inline, nao indices |
| Debugging / inspecao visual | TCF L0 | Legivel sem decompressao |
