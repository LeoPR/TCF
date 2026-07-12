# spec-camadas — a escada medida (formas A/B/C do owner)

Gerado por run.py. Bytes = emitted_bytes da coluna pelo pipeline REAL.
Cada degrau é lossless por construção (decode: base94 -> delta -> zfill ->
DV -> máscara). S5 vencendo por dict ≡ 'troca nas referências' (forma B).

## CNPJ real (receita, 5000)

### CNPJ ordenado (PK do hub)  (n=5000; S1 baseline = 32665B)

| degrau | bytes | modo | vs S1 |
|---|---:|---|---:|
| S1 masked (baseline) | 32665 | split | +0.0% |
| S2 clean (mask+DV out) | 53709 | tcf | +64.4% |
| S3 clean+delta | 17032 | dict | -47.9% |
| S4 base94 absoluto (=hoje) | 39958 | raw | +22.3% |
| S5 delta->base94 (misto) | 14270 | dict | -56.3% |

### CNPJ embaralhado  (n=5000; S1 baseline = 41332B)

| degrau | bytes | modo | vs S1 |
|---|---:|---|---:|
| S1 masked (baseline) | 41332 | split | +0.0% |
| S2 clean (mask+DV out) | 64999 | raw | +57.3% |
| S3 clean+delta | 51891 | raw | +25.5% |
| S4 base94 absoluto (=hoje) | 39958 | raw | -3.3% |
| S5 delta->base94 (misto) | 32408 | raw | -21.6% |

## CPF sintético (efêmero §2.3, 500)

### CPF RANDOM  (n=500; S1 baseline = 7499B)

| degrau | bytes | modo | vs S1 |
|---|---:|---|---:|
| S1 masked (baseline) | 7499 | raw | +0.0% |
| S2 clean (mask+DV out) | 4999 | raw | -33.3% |
| S3 clean+delta | 5146 | raw | -31.4% |
| S4 base94 absoluto (=hoje) | 2971 | raw | -60.4% |
| S5 delta->base94 (misto) | 3207 | raw | -57.2% |

### CPF CLUSTERED (lote +3)  (n=500; S1 baseline = 1043B)

| degrau | bytes | modo | vs S1 |
|---|---:|---|---:|
| S1 masked (baseline) | 1043 | split | +0.0% |
| S2 clean (mask+DV out) | 68 | tcf | -93.5% |
| S3 clean+delta | 19 | tcf | -98.2% |
| S4 base94 absoluto (=hoje) | 2999 | raw | +187.5% |
| S5 delta->base94 (misto) | 14 | tcf | -98.7% |

## Leitura por camada (em que grau cada uma dá vantagem)

| camada isolada | CNPJ ord | CNPJ shuf | CPF rand | CPF clust |
|---|---:|---:|---:|---:|
| L1+L2 limpeza+DV (S1→S2) | +21044 | +23667 | -2500 | -975 |
| L3 pré-forma delta (S2→S3) | -36677 | -13108 | +147 | -49 |
| L5 base94 nos resíduos (S3→S5) | -2762 | -19483 | -1939 | -5 |
| forma A hoje (S1→S4) | +7293 | -1374 | -4528 | +1956 |
| forma C misto (S1→S5) | -18395 | -8924 | -4292 | -1029 |

Nota de máquina: S3/S5 exigem spec ESTATAL por coluna (delta depende da linha
anterior) — encode_value per-value de hoje não expressa; é a capacidade nova
('column-wise nature') a registrar. S5≡troca-nas-referências quando dict vence.