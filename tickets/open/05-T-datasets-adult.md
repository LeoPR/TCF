---
title: Download e setup Adult (Census Income)
type: task
status: OPEN
priority: 4
parent: 01-M-datasets-setup
---

# Adult (Census Income)

## O que e

Dataset de classificacao demografica mais usado em ML academico.
Origem: US Census Bureau 1994, via UCI Machine Learning Repository.

## Caracteristicas

- **Rows:** 48.842 (train+test)
- **Colunas:** 14 features + 1 target
- **Tipos:** int, categorical, binary
- **Missing values:** sim (`?` em algumas celulas — precisa tratar)
- **Target:** `income` (>50K ou <=50K)

### Colunas

| Nome | Tipo | Nullable | Descricao |
|------|------|----------|-----------|
| age | int | no | Idade |
| workclass | category | yes (`?`) | Tipo de emprego |
| fnlwgt | int | no | Peso amostral do Census |
| education | category | no | Nivel educacional |
| education-num | int | no | Anos de educacao |
| marital-status | category | no | Estado civil |
| occupation | category | yes (`?`) | Ocupacao |
| relationship | category | no | Relacao familiar |
| race | category | no | Raca declarada |
| sex | binary | no | Male/Female |
| capital-gain | int | no | Ganho de capital (anual) |
| capital-loss | int | no | Perda de capital (anual) |
| hours-per-week | int | no | Horas trabalhadas por semana |
| native-country | category | yes (`?`) | Pais de origem |
| **income** | binary | no | `>50K` ou `<=50K` (target) |

## Como obter

```python
# scripts/setup_adult.py
from sklearn.datasets import fetch_openml
import pandas as pd
from pathlib import Path

OUTPUT = Path("datasets/canonical/adult-census")
OUTPUT.mkdir(parents=True, exist_ok=True)

print("Downloading Adult dataset from OpenML...")
data = fetch_openml("adult", version=2, as_frame=True)
df = data.frame

print(f"Downloaded: {len(df)} rows, {len(df.columns)} columns")
print(f"Dtypes: {df.dtypes.to_dict()}")

# Save as CSV
csv_path = OUTPUT / "adult.csv"
df.to_csv(csv_path, index=False)
print(f"Saved to {csv_path}")
```

## Metadata

`datasets/canonical/adult-census/metadata.json`:

```json
{
  "name": "adult-census",
  "source": "UCI ML Repository (via OpenML id=1590)",
  "origin": "https://archive.ics.uci.edu/ml/datasets/adult",
  "license": "CC BY 4.0",
  "downloaded": "2026-04-10",
  "dataset_id_openml": 1590,
  "dataset_id_uci": "adult",
  "citation": "Ronny Kohavi and Barry Becker (1996). UCI Machine Learning Repository.",
  "tables": {
    "adult": {
      "pk": null,
      "columns": { ... },
      "missing_value_marker": "?"
    }
  }
}
```

## Tarefas

- [ ] Criar `scripts/setup_adult.py`
- [ ] Rodar e verificar 48.842 rows
- [ ] Criar `metadata.json` com schema completo
- [ ] Criar `README.md` do dataset com citation correto
- [ ] Verificar licenca (CC BY 4.0 — permite uso)
- [ ] Commit do metadata + README, CSV no .gitignore

## Verificacao

- `datasets/canonical/adult-census/adult.csv` existe
- 48.842 rows, 15 colunas
- Contem `?` em algumas celulas (missing values reais)
- `metadata.json` valido
- Reproducivel: `python scripts/setup_adult.py`
