# 01 — Baseline OBAT+HCC atual (sem modificacao)

**Estado**: ativo (1o sub-exp do lab)
**Macro pai**: [`../README.md`](../README.md)

## Pergunta cientifica

Antes de propor qualquer fork delta-aware, **o que exatamente OBAT+HCC
produzem hoje** nos datasets D11a-h?

Especificamente:
1. Quais tokens OBAT emite por linha?
2. Onde tokens repetem identicos (oportunidade pra RLE)?
3. Onde literais variam (oportunidade perdida pra RLE)?
4. Quantos bytes do .tcf final sao "literais variantes"?
5. Qual a estrutura do trace/rede do HCC?

## Metodologia

Para cada dataset D11a-h:
1. Carregar valores (`csv.reader`, col 0, skipping header)
2. Deduplicar mantendo ordem → strings_unicas
3. Rodar `processar(strings_unicas, min_len=3)` (OBAT canonical)
4. Dump tokens em formato legivel
5. Rodar `M8AVirtualRefsSyntax().encode(values, unicas, tokens, "val")`
6. Dump body (.tcf), trace, rede
7. Analisar: estatisticas + onde delta-awareness ajudaria

**Importante**: zero modificacao em `src/tcf/`. Imports diretos da fonte.

## Datasets

- D11a (12 dias sequenciais)
- D11b (14 datas com bordas)
- D11c (13 datas mensais)
- D11d (13 datetimes minute-cadence)
- D11e (13 datetimes monthly)
- D11f/g/h (cadencias ms/us/ns)

## Saida esperada (por dataset)

```
outputs/<dataset>/
├── 1-obat-tokens.txt    ← tokens limpos, 1 linha por string
├── 2-hcc-body.tcf       ← output canonico do encode
├── 3-hcc-trace.txt      ← rede de composicoes do HCC
└── 4-analysis.md        ← estatisticas + apontamentos pra delta-aware
```

## Como rodar

```bash
python experiments/lab/dirty/2026-05-17-OBAT-delta-aware/01-baseline-obat-hcc-atual/run.py
```

## Conexoes

- [`../README.md`](../README.md) — lab pai
- [`../notas/modelo-conceitual.md`](../notas/modelo-conceitual.md) — hipoteses
