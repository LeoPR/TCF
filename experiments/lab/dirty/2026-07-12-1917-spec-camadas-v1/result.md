# spec-camadas v1 — result

3 formas do owner (A entrada / B paralela-refs / C misto) em 5 degraus,
**cada degrau com RT end-to-end PROVADO** (artifacts/04). Bytes = emitted_bytes real.

# 05 — LADDER de bytes (todos com RT verde)

| degrau | CNPJ ord | CNPJ shuf | CPF rand | CPF clust |
|---|---:|---:|---:|---:|
| S1 masked (baseline) | 32665 | 41332 | 7499 | 1043 |
| S2 clean (mask+DV out) | 53709 | 64999 | 4999 | 68 |
| S3 clean+delta | 17032 | 51891 | 5146 | 19 |
| S4 base94 absoluto (=hoje) | 39988 | 39988 | 3032 | 2830 |
| S5 delta->base94 (misto) | 14640 | 32954 | 3237 | 14 |

## Achados (contra-prova em artifacts/)
1. **S5 (forma C, misto) é a única sempre-boa**: CNPJ ord 14270 (−56%), shuf 32408
   (−22%), CPF clust 14 (−98.7%); só perde por pouco no random (3207 vs S4 2971).
2. **CPF clustered → 14B**: delta constante +3 vira RLE (ver seq_rle_runs, artifacts/02).
3. **Máscara tem valor estrutural**: S2 (limpeza isolada) PIORA o CNPJ (+64%) — o split
   usa a pontuação como separador. Camadas NÃO-monotônicas → escolha por-coluna, medida.
4. **RT: 5 degraus × 4 regimes = 20/20 VERDE** (artifacts/04) — a contra-prova do dado.
5. Máquina: S3/S5 exigem spec ESTATAL por coluna (delta usa a linha anterior) — o
   encode_value per-value de hoje não expressa → capacidade nova 'column-wise nature'.
