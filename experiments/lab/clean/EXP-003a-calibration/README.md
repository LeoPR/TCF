# EXP-003a — Calibracao CSV + compressor generico

## Hipotese

Nenhuma direta. **Estabelece referencia base**: quanto gzip/brotli/zstd
ganham sozinhos sobre CSV em datasets variados? Sem isso, nao podemos
interpretar EXP-003b (TCF vs gzip).

## Metodo

1. 5 datasets com perfis diferentes:
   - `tpch-supplier-100`: TPC-H supplier (real, 100 rows × 7 cols)
   - `adult-1k`: Adult Census (real, 1000 rows × 15 cols)
   - `categorical-heavy`: status/categoria repetidos (sintetico)
   - `time-series`: datas + valores numericos (sintetico)
   - `mixed`: schema relacional simulado em 1 tabela

2. Encode em CSV simples (com `lineterminator="\n"`)

3. Aplicar 4 compressores: `none`, `gzip`, `brotli`, `zstd`
   (brotli/zstd opcionais; pular se nao instalados)

4. Medir bytes em cada combinacao + ratio

## Saida

Tabela:
```
dataset × compressor → bytes, ratio
```

E arquivo `results.json` reproduzivel.

## Critério de pivot

| Resultado | Pivot |
|-----------|-------|
| gzip nao comprime CSV (<5% de ganho) | revisar datasets — talvez muito pequenos ou aleatorios |
| gzip > 50% em todos | excelente baseline; HP-T1 fica decisiva |
| ratio muito instavel entre datasets | normal; documentar variabilidade |

## NAO eh objetivo

- Comparar TCF (vai ser EXP-003b)
- Comparar formatos JSON/Parquet
- Otimizar codigo

---

## Extensao (2026-05-08): CSV ordenado vs CSV naive

**Pergunta**: o sort sozinho (sem TCF) ja da vantagem para gzip?

Adicionou-se variante onde o CSV eh **reordenado** por uma coluna
de baixa cardinality (heuristica: `cardinality < N/2`, prefere a
que reduz mais runs).

### Resultados

| Dataset | sort_by | csv+gz | csv-sorted+gz | diff |
|---------|---------|-------:|--------------:|-----:|
| tpch-supplier-100 | s_nationkey | 6343 | 6353 | +0.16% |
| adult-1k | age | 13169 | 12343 | **-6.27%** |
| categorical-heavy | qtd | 4564 | 4428 | -2.98% |
| time-series | temperatura | 5684 | 5649 | -0.62% |
| mixed-relational | produto_nome | 9913 | 9732 | -1.83% |
| **media** | | | | **-2.31%** |

### Comparativo com TCF (cruza com EXP-003b)

| Dataset | csv-srt+gz | compact+gz | smart+gz | srt vs comp | srt vs smart |
|---------|-----------:|-----------:|---------:|------------:|-------------:|
| tpch-supplier-100 | 6353 | 6141 | 5906 | +3.5% | +7.6% |
| adult-1k | 12343 | 11525 | 10146 | +7.1% | +21.7% |
| categorical-heavy | 4428 | 4098 | 2912 | +8.1% | **+52.1%** |
| time-series | 5649 | 5011 | 5008 | +12.7% | +12.8% |
| mixed-relational | 9732 | 8363 | 6229 | +16.4% | **+56.2%** |

### Conclusao da extensao

**Sort sozinho NAO substitui TCF.** Mesmo CSV ordenado + gzip:
- Perde para TCF compact em todos os 5 datasets (+3.5% a +16.4%)
- Perde MUITO para TCF smart em 2/5 datasets (+52% a +56%)

**Implicacao**: o ganho do TCF nao vem so do sort. Vem da combinacao:
- Estrutura colunar (separa coluna em bloco contiguo)
- RLE inline
- (em smart) DICT inline + cross-DICT + key-elim + affix

CSV ordenado + gzip eh **competitivo apenas com TCF raw** (colunar
sem RLE), nao com compact ou smart.

### Implicacao para HP-T1 (revisita)

EXP-003b mostrou que smart+gz vence compact+gz por -14% medio
(intermediario). Esta extensao mostra que:

1. **TCF compact tem valor real** vs CSV+gzip (ganho 3-16%)
2. **TCF smart tem valor ainda maior** em casos relacionais (+52% a +56% vs sort sozinho)
3. **Caminho hibrido confirmado**: smart como default com auto-bypass.
   Em datasets onde Propostas nao agregam, cai pra compact (que ja
   tem valor proprio sobre CSV ordenado).

### Arquivos adicionais

`results/{dataset}-csv-sorted.csv` e `.csv.gz` para inspecao.
`results/results-with-sort.json` reproduzivel.

### Codigo

`run-with-sort.py` reusa os mesmos datasets de `run.py`. Para reproduzir:

```bash
python run-with-sort.py
```
