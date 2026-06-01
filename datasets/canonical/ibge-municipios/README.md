# ibge-municipios (canonical dataset)

> Metadata + 100-row sample tracked in git. Full data lives in
> `Z:/tcf-data/external/ibge-municipios/` (see `config/storage.json`).

## Source

- **Origin**: IBGE Localidades API — `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`
- **License**: Open data (IBGE)
- **Download**: `python scripts/setup_ibge_municipios.py`
- **Build hub**: `python scripts/csv_to_sqlite.py ibge-municipios`

## Schema

`municipios` table — 5571 rows × 8 columns (one row per Brazilian
municipality). Flattened from the IBGE administrative hierarchy
(municipio → microrregiao → mesorregiao → UF → regiao). High categorical
repetition: 27 UFs, 5 regioes — real-world accented UTF-8 text.

| Column | Type | Notes |
|--------|------|-------|
| id | int | IBGE municipality code (7 digits), pk |
| municipio | string | Municipality name (UTF-8, accented) |
| microrregiao | string | Microregion (falls back to immediate region) |
| mesorregiao | string | Mesoregion (falls back to intermediate region) |
| uf_sigla | string | State 2-letter code (e.g. SP) |
| uf_nome | string | State full name (e.g. São Paulo) |
| regiao_sigla | string | Region code (N/NE/SE/S/CO) |
| regiao_nome | string | Region full name (e.g. Sudeste) |

Note: a small number of recent municipalities have `microrregiao = null`
in the API; for those, `microrregiao`/`mesorregiao` are filled from the
`regiao-imediata`/`regiao-intermediaria` hierarchy (same UF/regiao).

## Usage

```python
from scripts.dataset_reader import DatasetReader

reader = DatasetReader("ibge-municipios")
for row in reader.rows("municipios"):
    ...
```
