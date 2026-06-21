# Result — caracterizacao de ORDENACAO (O-FMT-01..04, Segment #5) [probatório]

**Data**: 2026-06-14. **Objetivo**: medir o ganho de ordenar ANTES de
implementar (disciplina confirmada-empirica). `analyze.py`, 6 datasets, 2000
linhas/coluna.

## B. Sort da tabela por 1 chave (realista multi-col)

Ordenar a tabela por uma coluna-chave (natural, order-free) vs as-is:

| dataset | best% | chave | base B | mapCost | netReversivel |
|---|---:|---|---:|---:|---:|
| adult | **14.6%** | relationship | 72763 | 8000 | +2657 |
| receita | **11.4%** | uf | 71681 | 8000 | +142 |
| ibge | 7.5% | microrregiao | 54436 | 8000 | −3929 |
| br-pessoas | 5.6% | municipio_id | 138544 | 8000 | −227 |
| tpch-lineitem | 1.3% | l_returnflag | 176163 | 8000 | −5661 |
| online-retail | 0.3% | Country | 53831 | 8000 | −7856 |

- **Natural (O-FMT-02, ordem livre)**: ganho real **5-15%** onde existe uma chave
  low-card boa; ~0% onde nao (online-retail, lineitem dominados por free-text).
- **Reversivel (O-FMT-01)**: o mapa reverso (N indices como texto, ~N*digitos =
  8000 chars p/ 2000 linhas) **quase sempre supera o ganho** -> net NEGATIVO,
  exceto adult (+2657) e receita (+142). Mapa ingenuo nao vale; mapa esperto
  (delta/RLE da permutacao) talvez resgate, mas e' marginal.

## A. Sort por-coluna isolada (single-col, pura)

Ordenar CADA coluna sozinha derruba o body drasticamente:

| classe | exemplos | ganho |
|---|---|---|
| categorico low-card | relationship 98.3%, l_returnflag 99.3%, l_linenumber 99.1%, uf 97% | **90-99%** |
| numerico repetitivo | quantity 93%, discount 98%, hours-per-week 93% | 90-98% |
| free-text | nome 19.7%, Description 10.5%, nome_fantasia 19.7%, cnae 60% | 10-60% |

**MAS isto NAO e' realizavel** em tabela row-aligned: ordenar cada coluna
independente exigiria UMA permutacao reversa POR COLUNA (C perms = C*N indices)
-> custo explode (muito > o ganho). So' da' pra ordenar a tabela inteira por 1
chave (= B), com 1 permutacao.

## Conclusoes

1. **O-FMT-02 (natural, 1 chave, ordem livre)** e' o unico lever de ordenacao
   realista: 5-15% onde ha' chave low-card. Opt-in (usuario aceita perder a
   ordem original). Zero custo de mapa.
2. **O-FMT-01 (reversivel)** quase sempre perde pro custo do mapa. Skip (ou so'
   com mapa esperto, ganho marginal).
3. **O-FMT-04 (column-aware)** = escolher a melhor chave; testado em B (pegamos
   o min sobre chaves low-card).
4. **Ordenacao por-coluna independente** = nao viavel (perms por coluna).

## CONEXAO-CHAVE p/ a revisao do multi-column (V2-B)

Os ganhos enormes de A (90-99% em low-card ordenado) sao **redundancia de
baixa-cardinalidade** que **um DICIONARIO (V2-B) captura ORDER-FREE, sem
permutacao e sem reordenar**. Ou seja: pra colunas categoricas/low-card, **V2-B
dicionario tende a ser um lever MAIOR que ordenacao** (pega a mesma redundancia
sem perder a ordem nem pagar mapa). Ordenacao ajuda a tabela toda por 1 chave;
dicionario ajuda cada coluna sem reordenar. **Levar isso pra revisao multi-col.**

## Decisao / proximo passo

- **O-FMT-02** vale como knob opt-in (`encode(table, sort_by="col")` ou
  `sort_rows=True` auto-pick), ordem-livre, default off. Ganho 5-15% em datasets
  amenos. Pequeno, baixo risco (so' reordena antes de encodar; decode retorna a
  ordem ordenada).
- Mas a CONEXAO acima sugere priorizar **V2-B dicionario** na revisao multi-col
  (captura mais, order-free). Decisao do owner: O-FMT-02 agora (rapido) OU
  pular pra discussao multi-col/V2-B.

## Artefatos
- `analyze.py` — B (table sort por chave) + A (por-coluna puro)
