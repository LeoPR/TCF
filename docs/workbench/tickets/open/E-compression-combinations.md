---
title: E-compression-combinations — estudo empirico da ordem de transformacoes TCF
type: experiment
status: OPEN
priority: HIGH
created: 2026-04-27
origin: Decisao "ordem precisa ser estudada com combinacoes"
see_also:
  - docs/theory/components/7-combination-study.md (plano completo)
  - docs/workbench/tickets/open/T-test-harness-mvp.md (depende)
  - docs/workbench/tickets/open/H-compression-v04-roadmap.md
---

# E-compression-combinations — descobrir ordem otima por cenario

Em vez de escolher ordem teoricamente, **testar empiricamente**
combinacoes plausiveis × datasets × profiles, e reportar a melhor
por cenario.

Plano completo em
[7-combination-study.md](../../../theory/components/7-combination-study.md).

## Eixos do experimento

1. **Ordem das transformacoes** (8-12 plausiveis): SDRT, SRDT, DSRT, etc.
2. **DICT scope**: none / per_column / cross_auto / cross_forced / cross_subset
3. **RLE threshold**: off / fixed_2 / fixed_3 / adaptive_by_type / bytes_saved
4. **STATS mode**: off / cardinality_only / global / stratified
5. **Sort**: none / manual / auto_compress / auto_cardinality
6. **Column ordering**: natural / pk_first / by_compress / categorical_first

Espaco bruto: ~12,800 combinacoes. Reduzido via screening fatorial
fracional para ~1000 testaveis.

## Datasets de cenario

- `min_5x3` — 5 rows, 3 cols (overhead alto)
- `time_series_1000` — sensor com baixa variacao
- `adult_100` — Adult Census 100 rows
- `tpch_partsupp_100` — TPC-H 100 rows (FKs)
- `wide_random_100` — 100×50 aleatorios (adverso)
- `nested_flat_100` — JSON flatten 100 rows

## Estrategia de reducao

Fase A (screening 1D): variar 1 eixo, fixar outros. ~180 combos
Fase B (pares): testar interacoes entre 2 eixos. ~200 combos
Fase C (top combos): finalistas em todos cenarios. ~300 combos
Fase D (replicacao): top 5-10 com 10 iteracoes para timing. ~50 combos

Total: ~1000 execucoes (4 semanas).

## Saida esperada

Tabela 3D `(profile, dataset, top_combo)`:

| Profile | Dataset | Best combo | Bytes | Encode ms | vs CSV+gzip |
|---------|---------|-----------|-------|-----------|-------------|
| minimal_bytes | adult_100 | S→Dcross→Rsaved→Tcard | 1850 | 8.2 | -47% |
| balanced | adult_100 | S→Dper→Radapt→Tglobal | 5500 | 0.5 | -22% |
| ... | ... | ... | ... | ... | ... |

Plus heatmap "qual combo vence em qual cenario".

## Criterio de aceite

- [ ] Pipeline configuravel implementado no TCF v0.4 (Strategy pattern)
- [ ] Fase A executada em todos os datasets
- [ ] Fase B com top 50% combos
- [ ] Fase C+D com top 10
- [ ] Resultado em CSV + manifest JSONL
- [ ] Documento `defaults_v04.md` com a melhor combinacao por profile

## Dependencias

- T-test-harness-mvp (precisa rodar)
- TCF v0.4 com pipeline pluggable (precisa existir)

## Impacto estimado

4 semanas (paralelo a implementacao TCF v0.4).

## Notas para revisar

Quando reabrir:
- Implementacao em `experiments/harness/scenarios/` + `harness/combinations.py`
- Manifests em `experiments/results/harness/combinations/`
- Saida cientifica entra em Cap 5 do paper
