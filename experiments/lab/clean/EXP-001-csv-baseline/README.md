# EXP-001 — CSV Baseline

**Status**: aberto
**Pergunta**: como CSV se comporta como baseline (sem TCF) em datasets
de teste? Bytes, timing, roundtrip OK?

## Hipotese

H1: CSV consegue **roundtrip exato** com `infer_types=True` para
datasets simples (numericos, strings, bools).

H2: CSV+gzip atinge **40-65% reducao** vs raw CSV em datasets com
repeticao categorica.

H3: CSV+brotli melhora ~10% sobre CSV+gzip ao custo de ~10× tempo.

## Metodo

Para cada dataset (`micro`, `small`, `categorical_heavy`,
`wide_random`):

1. Encode com CSVEncoder (3 compressoes: none/gzip/brotli)
2. Decode e comparar com input
3. Reportar bytes/timing/roundtrip

5 iteracoes por combinacao para timing estavel (mediana).

## Datasets

- `micro` — 5 rows × 4 cols (com repeticoes leves)
- `small` — 20 rows × 5 cols
- `categorical_heavy` — 100 rows × 6 cols (mix tipo Adult Census)
- `wide_random` — 100 rows × 11 cols (adverso para compressao)

## Reproduzir

```bash
python experiments/lab/clean/EXP-001-csv-baseline/run.py
```

Saida: `manifest.jsonl` + `report.md` + tabelas no stdout.

## Resultados

Ver [report.md](report.md) (gerado pelo run.py).
