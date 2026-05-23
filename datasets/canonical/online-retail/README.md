# Online Retail — UCI ML Repository

Dataset financeiro canonical (transactional sales) pra testar
**natureza #8 (arredondamento implicito)** — UnitPrice tem padroes
.99/.95/.50 caracteristicos de pricing varejo.

## Source

- **Name**: Online Retail
- **Origin**: UCI ML 352 (UK online retailer, 2010-2011)
- **License**: CC BY 4.0
- **Citation**: Chen, D. (2015). Online Retail. UCI Machine Learning
  Repository.
- **URL**: https://archive.ics.uci.edu/dataset/352/online+retail

## Schema

8 colunas × 541,909 rows (transacoes individuais):

| Column | Type | Notes |
|---|---|---|
| InvoiceNo | TEXT | Invoice number; 'C' prefix = cancelado |
| StockCode | TEXT | Product code (~4k unicos) |
| Description | TEXT | Product description (~0.27% NaN) |
| Quantity | INT | Pode ser negativo (returns) |
| InvoiceDate | DATETIME | M/D/YYYY HH:MM (UK format) |
| **UnitPrice** | FLOAT | **GBP — padroes .99/.95/.50 caracteristicos** |
| CustomerID | FLOAT | Customer code (~25% NaN) |
| Country | TEXT | Country name (~37 paises) |

## Naturezas alvo

**Hipoteses a re-testar** (T-EXP-NATUREZAS-RARAS-V2 futuro):
- **#8 Arredondamento implicito**: UnitPrice tem padroes .99/.95/.50
  caracteristicos de pricing varejo psicologico. Encoder "prefix + sufixo
  fixo" pode comprimir significativamente.
- **#7 Enumerated** Country (~37 unicos em 542k rows = card 0.0001 — alta
  compressao via dedup esperada). Mas pacote 5 ja' refutou enumerated
  explicit; reuso confirmacao M10.

## How to download

```bash
pip install -e ".[datasets]"  # requer requests + pandas (xlsx)
python scripts/setup_online_retail.py
python scripts/csv_to_sqlite.py
```

Saida:
- Raw: `Z:/tcf-data/external/online-retail/online_retail.csv` (~45MB)
- SQLite: `Z:/tcf-data/interim/online-retail.db`
- Sample git: `datasets/samples/online-retail/online-retail-sample.csv`

## Notas

- UCI ships como Excel (.xlsx); script converte pra CSV
- Encoding original tem chars Latin-1; convertido pra UTF-8
- CustomerID e' float (NaN-friendly em pandas) mas semanticamente int

## Conexoes

- [T-DATA-1](../../../tickets/T-DATA-1-datasets-financeiros-cientificos.md)
- [Reflexao naturezas numericas](../../../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md)
- [T-EXP-NATUREZAS-RARAS (refutada em datasets gerais)](../../../tickets/T-EXP-NATUREZAS-RARAS-EXPLORACAO.md)
