# br-identidades (canonical dataset) — SYNTHETIC / declared bias

> **SYNTHETIC, built-to-test.** Metadata + 100-row samples tracked in git.
> Full data (600k rows) + SQLite hub live in `Z:/tcf-data/` (gitignored,
> regenerable). Contains **no PII**.

## What this is — and what it is NOT

Synthetic Brazilian CPF/CNPJ identity dataset, generated to exercise the
**ADR-0015 opt-in natures** (`SPEC_CPF` / `SPEC_CNPJ`) and the
`n_compressible >= ~50%` activation gate — the single largest gap in the
canonical corpus (the natures are welded into `src/tcf/natures/` but had **zero
backing dataset**).

- **REAL**: geography (`municipio_id`/`uf_sigla`) reuses canonical
  `ibge-municipios` codes, so município/UF distribution is grounded.
- **SYNTHETIC**: identifiers (random mod-11-valid bodies — no regional 9th-digit
  encoding, not issued documents), names, dates, emails.

**Declared bias (Brunswik 1956 / CLAUDE.md anti-incident checklist Q4):** this
dataset validates **lossless round-trip** and the **activation gate**, but by the
project methodology it **cannot alone justify a `confirmada-empirica` claim**.
Only a real source can close the generalization gate — see
[T-DATA-2-RECEITA-CNPJ](../../../tickets/T-DATA-2-RECEITA-CNPJ.md) (Receita
Federal CNPJ open data; company CNPJs are non-PII).

## Schema

Two related tables in one hub:

### pessoas — 500,000 rows (CPF, `nature='cpf'`)
| Column | Type | Notes |
|--------|------|-------|
| cpf | string (pk) | Masked `NNN.NNN.NNN-DD`, valid mod-11 |
| nome | string | Synthetic BR full name (accented UTF-8) |
| municipio_id | int | 7-digit IBGE code; soft ref into `ibge-municipios.id` |
| uf_sigla | string | UF code denormalized from ibge (27 values) |
| data_cadastro | date | ISO `YYYY-MM-DD`, 2010–2025, recency-weighted |
| email | string (nullable) | Derived from nome; empty for ~8% |

### empresas — 100,000 rows (CNPJ, `nature='cnpj'`)
| Column | Type | Notes |
|--------|------|-------|
| cnpj | string (pk) | Masked `NN.NNN.NNN/NNNN-DD`, valid mod-11; branch `/0001` (matriz) ~90% |
| razao_social | string | Shared suffixes (Ltda/ME/EIRELI/S.A./EPP) |
| municipio_id | int | 7-digit IBGE code; soft ref into `ibge-municipios.id` |
| uf_sigla | string | UF code denormalized from ibge |
| data_abertura | date | ISO `YYYY-MM-DD`, 2005–2025 |
| socio_cpf | string (nullable) | **Real cross-table FK** into `pessoas.cpf` (~30% of rows) |

All identifiers are **valid and masked** ("happy data"). The masked/unmasked/
corrupt mix and impossible-data variants belong to the **deferred edge plan**
([T-DATA-3-EDGE-QUALITY-FIXTURES](../../../tickets/T-DATA-3-EDGE-QUALITY-FIXTURES.md)),
not here.

## Verified on generation

- cpf/cnpj 100% unique (true PKs); `socio_cpf` 0 orphans (FK check OK)
- 3000-row random samples: **100% `classify_value()=='compressible'`** and
  **100% lossless round-trip** under the welded `SPEC_CPF`/`SPEC_CNPJ`
- 0 all-same-digit identifiers (mod-11-passes-but-invalid trap rejected)
- 27 UFs; accented UTF-8 preserved

## Volume note (shaper)

`pessoas` (500k) **exceeds the shaper's validated ≤100k regime**
(T-SHAPER-CODE-HARDENING). Use this dataset via **direct `encode()` on columns**,
not shaper sampling.

## Reproduce

```bash
python scripts/setup_ibge_municipios.py    # prerequisite (geography)
python scripts/setup_br_identidades.py     # deterministic, seed=20260601
python scripts/csv_to_sqlite.py br-identidades
```

## Use with natures

```python
import sqlite3
from tcf import encode, decode, SPEC_CPF

con = sqlite3.connect("Z:/tcf-data/interim/br-identidades.db")
cpfs = [r[0] for r in con.execute("select cpf from pessoas limit 1000")]
text = encode(cpfs, nature=SPEC_CPF)
assert decode(text) == cpfs   # header #TCF.8 autoritativo; lossless
```
