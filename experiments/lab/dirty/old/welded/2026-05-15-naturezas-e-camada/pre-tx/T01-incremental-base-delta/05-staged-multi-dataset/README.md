# 05 — Staged pipeline generalizacao (D11a, D11b, D11c)

**Estado**: aberto (quinta iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Datasets**: [D11a](../../../../../../../datasets/synthetic/D11a-datas-dia.csv), [D11b](../../../../../../../datasets/synthetic/D11b-datas-borda.csv), [D11c](../../../../../../../datasets/synthetic/D11c-datas-mensal.csv)

## Pergunta cientifica

O staged pipeline (3 estagios A/B/C) construido em [`../04-staged-pipeline-D11c/`](../04-staged-pipeline-D11c/)
para D11c se aplica **sem alteracao** a D11a (sequencia dia-only) e
D11b (bordas calendar)? E entrega **os mesmos bytes** dos
sub-experimentos 01 (42 bytes em D11a) e 02 (59 bytes em D11b)?

Em outras palavras: o pipeline e' **independente do dataset**?
Stage A identifica corretamente em todos? Stage B normaliza sem
falha? Stage C otimiza so' onde existe pattern, sem custo onde
nao existe?

## Hipoteses

- **H1 (RT preserved em todos)**: pipeline reconstroi as 3 entradas byte-canonical.
- **H2 (sem retrabalho)**: mesmos modulos rodam em todos os 3 datasets — codigo copiado de [`../04-staged-pipeline-D11c/`](../04-staged-pipeline-D11c/) sem patch.
- **H3 (Stage C inocuo onde nao ha pattern)**: pra D11a e D11b, Stage C nao deve aplicar escala (deltas nao alinham month/year boundaries com mesma day-of-month). Bytes devem igualar Stage B → TCF.
- **H4 (matching com sub-exps anteriores)**:
  - D11a: TCF de C = 42 bytes (= sub-exp 01)
  - D11b: TCF de C = 59 bytes (= sub-exp 02)
  - D11c: TCF de C = 22 bytes (= sub-exp 03 e 04)

## Predicoes detalhadas

**D11a** — deltas `[1,1,1,1,3,1,1,5,1,2,14]`:
- Datas dentro de May-Jun 2026, varias day-of-month diferentes
- Nenhuma transicao alinha day-of-month exato (pra hit M ou Y)
- Stage C output **igual** stage B → TCF = 42 bytes

**D11b** — deltas `[1,27,1,1,305,1,58,1,305,1,30,28,1]`:
- Bordas Jan/Feb/Dec, ano bissexto
- Day-of-month varia 31→1→28→29→1→31→1→28→1→31→1→31→28→1
- Nenhuma alinha → Stage C **igual** stage B → TCF = 59 bytes

**D11c** — deltas `[31,28,31,30,31,30,31,31,30,31,30,31]`:
- Fatura mensal: todos com day-of-month = 5
- Todos sao +1 mes exato
- Stage C aplica **12x `1M`** → TCF = 22 bytes

## Estrutura

Codigo (copia byte-identica de sub-exp 04):
- `stage_a_identify.py`, `stage_b_normalize.py`, `stage_c_optimize.py`, `decoder.py`

Orquestrador `run.py` itera 3 datasets, gera `outputs/<dataset>/`.

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/05-staged-multi-dataset/run.py
```

## Saidas

`outputs/<DATASET>/`:
- `stage-A-metadata.json` — output do identify
- `stage-B.txt` — output do normalize
- `stage-C.txt` — output do optimize
- `tcf-puro.tcf` / `tcf-B.tcf` / `tcf-C.tcf` — TCFs dos 3 pipelines
- `rt.txt` — RT verification

`result.md` (commitavel) — tabela consolidada das 3 datasets.

## Criterio de fechamento

- [ ] H1: RT 3/3 OK em todos os datasets
- [ ] H2: pipeline rodou em D11a, D11b, D11c sem patch nos modulos
- [ ] H3: Stage C output == Stage B output em D11a e D11b
- [ ] H4: TCFs batem com sub-exps anteriores (42, 59, 22)
