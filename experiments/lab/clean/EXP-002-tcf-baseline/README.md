# EXP-002 — TCF Baseline (vs CSV de EXP-001)

**Status**: aberto
**Pergunta**: como TCF v0.2 atual se comporta nos mesmos datasets de
EXP-001? Em quais cenarios TCF brilha vs CSV?

## Hipoteses

H1: TCF L0 (raw columnar) tem **bytes similares ou mais baixos** que
CSV em datasets onde nomes de colunas pesam.

H2: TCF L2 (RLE+STATS) reduz bytes vs L0 em **datasets categoricos
heavy** (>30% reducao esperada).

H3: TCF roundtrip e exato em datasets com tipos primitivos.

H4: TCF + brotli e mais compacto que CSV + brotli em datasets
adequados (com sinergia entre estruturas TCF e LZ77).

## Metodo

Para cada dataset (`micro`, `small`, `categorical_heavy`,
`wide_random`):

1. Encode com TCFEncoder em 3 niveis: L0, L2 (default), L3
2. Para cada nivel: 3 compressoes (none/gzip/brotli)
3. Decode e comparar com input
4. Reportar bytes/timing/roundtrip

5 iteracoes por combinacao para timing estavel.

## Reproduzir

```bash
# 1. Rodar EXP-001 primeiro (baseline para comparar)
python experiments/lab/clean/EXP-001-csv-baseline/run.py

# 2. Rodar EXP-002
python experiments/lab/clean/EXP-002-tcf-baseline/run.py
```

Saida: `manifest.jsonl` + `report.md` (com tabela comparativa CSV vs TCF).

## Resultados

Ver [report.md](report.md) (gerado pelo run.py).

## Observacao sobre TCF v0.2

EXP-002 usa TCF v0.2 atual (sem DICT, sem stratified STATS, sem
auto-sort). Quando v0.4 estiver pronto, criar EXP-005-tcf-v04 para
comparar evolucao.
