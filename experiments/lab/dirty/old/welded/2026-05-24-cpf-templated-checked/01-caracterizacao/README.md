---
title: Sub-exp 01 — Caracterizacao baseline M10 em D-CPF
status: in-progress
---

# Sub-exp 01 — Caracterizacao baseline M10

## Pergunta

Quanto o pipeline canonical M10 (sem pre-tx) ja' captura em cada
perfil de dataset CPF (uniform/clustered/mixed/corrupt)? Onde
OBAT/HCC ganha sozinho e onde fica nivel raw?

## Metodo

Pra cada D-CPF (4 datasets de 1k rows):
1. Ler CSV
2. `encode(values)` canonical (sem pre-tx)
3. Capturar SideOutputs (column_features, cadence, min_len, hcc trace info)
4. Medir bytes raw vs encoded
5. Identificar onde M10 detectou padrao vs onde ficou ~raw

## Output

- `report.md` com tabela comparativa + observacoes
- `manifest.jsonl` com numeros brutos
