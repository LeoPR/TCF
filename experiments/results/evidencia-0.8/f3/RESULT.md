# F3 - sinteticos maiores (parcial por amostragem)

Status deste artefato: execucao encerrada por decisao de escopo do fechamento `0.8`.
Objetivo foi preservar evidencia amostral suficiente para continuidade da fila R1-R3,
sem rodar populacao total nesta etapa.

## Cobertura obtida

- F3-1 (suite D1..D17): 31/31 casos (`f3-1-*.jsonl`)
- F3-2 (curva n={20,100,1k,10k,100k} single+multi): 10/10 casos (`f3-2-*.jsonl`)
- F3-3 (paralelismo): 9 casos (`f3-3*.jsonl`)
- F3-4 (br-identidades 600k): 0 casos

Total de registros JSONL produzidos: 50.

## F3-3 - o que ficou faltando

- `f3-3b-lineitem-20k-p4.jsonl`
- `f3-3b-lineitem-20k-p8.jsonl`
- `f3-3d-combo-base.jsonl`
- `f3-3d-combo-natures_per_col.jsonl`
- `f3-3d-combo-sort_by.jsonl`
- `f3-3d-combo-drop_names.jsonl`
- `f3-3d-combo-natures_sort_drop.jsonl`

## Nota metodologica

Esta rodada passa a ser tratada como AMOSTRA (nao populacao total), coerente com a
prioridade de fechar o nucleo `#TCF.8` primeiro. A cobertura completa de massa pode ser
retomada em janela propria, com ambiente estavel e sem conflitar com o closeout do `0.8`.
