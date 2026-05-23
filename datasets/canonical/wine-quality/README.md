# Wine Quality — UCI ML Repository

Dataset cientifico canonical pra testar **natureza #5 (range narrow)**
e **decimais com precisao fixa** (features quimicas).

## Source

- **Name**: Wine Quality (Red + White merged)
- **Origin**: UCI ML 186 (red), via OpenML (id=40691 red, id=40692 white)
- **License**: CC BY 4.0
- **Citation**: Cortez, P., Cerdeira, A., Almeida, F., Matos, T., & Reis, J.
  (2009). Modeling wine preferences by data mining from physicochemical
  properties. Decision Support Systems, 47(4), 547-553.
- **URL**: https://archive.ics.uci.edu/dataset/186/wine+quality

## Schema

13 colunas × 6,497 rows (1,599 red + 4,898 white):

| Column | Type | Notes |
|---|---|---|
| fixed_acidity | FLOAT | Range narrow (~3-16) |
| volatile_acidity | FLOAT | Range narrow (~0.08-1.6) |
| citric_acid | FLOAT | Range narrow (~0-1.7) |
| residual_sugar | FLOAT | Range mais amplo (~0.6-66) |
| chlorides | FLOAT | Decimais pequenos (~0.009-0.6) |
| free_sulfur_dioxide | FLOAT | Range narrow inteiros (~1-300) |
| total_sulfur_dioxide | FLOAT | Range narrow inteiros (~6-440) |
| density | FLOAT | Range MUITO narrow (~0.987-1.04) — **#5 range** |
| pH | FLOAT | Range narrow (~2.7-4.0) — **#5 range** |
| sulphates | FLOAT | Range narrow (~0.2-2.0) |
| alcohol | FLOAT | Range narrow (~8-15) |
| **quality** | INT | Target: 3-9 (0-10 scale, mas observado 3-9) |
| **variant** | TEXT | red ou white |

## Naturezas alvo

**Hipoteses a re-testar** (T-EXP-NATUREZAS-RARAS-V2 futuro):
- **#5 Range narrow**: density (0.987-1.04), pH (2.7-4.0), alcohol (8-15),
  sulphates (0.2-2.0). Encoder "base + local" pode dar ganho significativo.
- **Decimais precisao fixa**: density tem ~5 decimais consistentes.
  Possivel ganho via fixed-decimal encoding.

## How to download

```bash
pip install -e ".[datasets]"
python scripts/setup_wine_quality.py
python scripts/csv_to_sqlite.py
```

Saida:
- Raw: `Z:/tcf-data/external/wine-quality/wine.csv` (~100KB)
- SQLite: `Z:/tcf-data/interim/wine-quality.db`
- Sample git: `datasets/samples/wine-quality/wine-sample.csv` (100 rows)

## Conexoes

- [T-DATA-1](../../../tickets/T-DATA-1-datasets-financeiros-cientificos.md)
- [Reflexao naturezas numericas](../../../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md)
- [T-EXP-NATUREZAS-RARAS (refutada em datasets gerais)](../../../tickets/T-EXP-NATUREZAS-RARAS-EXPLORACAO.md)
