# receita-cnpj (canonical dataset) — REAL CNPJ (non-PII)

> Metadata + samples tracked in git. Full data (200k rows) + SQLite hub live
> in `Z:/tcf-data/` (gitignored, regenerable). **Real company data, non-PII.**

## What this is

A **real** slice of Brazilian company registrations (estabelecimentos) from
the Receita Federal open-data CNPJ base. This is the **ecological counterpart**
to the synthetic [`br-identidades`](../br-identidades/README.md): company CNPJs
are public, **non-PII** data, so a real CNPJ column CAN be sourced — and it is
the only path that can move the ADR-0015 CNPJ nature toward `confirmada-empirica`
(see [T-DATA-2-RECEITA-CNPJ](../../../tickets/T-DATA-2-RECEITA-CNPJ.md)).

Only **non-PII company columns are projected** (CNPJ, matriz/filial flag, trade
name, status, start date, primary CNAE, UF, municipality code). Person-level
fields present in the raw file (phone, e-mail, street address) are **deliberately
dropped** in the setup script.

## Source

- **Origin**: Receita Federal — Dados Públicos CNPJ, file `Estabelecimentos`
- **API**: Nextcloud public share over WebDAV at
  `https://arquivos.receitafederal.gov.br/public.php/webdav` (share token
  `YggdBLfdninEJX9`); downloads via `/public.php/dav/files/<token>/<YYYY-MM>/`.
  The older flat `dadosabertos.rfb.gov.br/CNPJ/...` HTTP paths are gone.
- **Period sliced**: 2026-05, part `Estabelecimentos0.zip` (~2 GB compressed;
  the setup STREAMS only as far as needed — does not download the full part)
- **License**: Dados abertos (Receita Federal). Pessoa jurídica = não-PII.
  Confirmar termos de uso antes de redistribuir o dado bruto.

## Schema

`estabelecimentos` — 200,000 rows × 8 columns (CNPJ re-assembled from the
3 split source columns `cnpj_basico`+`cnpj_ordem`+`cnpj_dv` into the masked
form `NN.NNN.NNN/NNNN-DD`).

| Column | Type | Notes |
|--------|------|-------|
| cnpj | string (pk) | Masked `NN.NNN.NNN/NNNN-DD`; nature='cnpj' target |
| matriz_filial | string | 1=matriz, 2=filial |
| nome_fantasia | string (nullable) | Trade name (real free text); empty for many rows |
| situacao | string | Situação cadastral code (01..08), low-card |
| data_inicio | string (nullable) | Activity start date, raw YYYYMMDD |
| cnae_principal | string (nullable) | Primary CNAE (7-digit code) |
| uf | string (nullable) | State 2-letter code (+ `EX` = exterior) |
| municipio_cod | string (nullable) | Receita municipality code (NOT the IBGE code) |

## Measured — CNPJ nature on REAL data (10k slice)

| | bytes | ratio vs raw |
|---|---|---|
| raw | 190,000 | 100% |
| TCF, no nature (M10) | 205,944 | **108.4%** (inflates — CNPJ is unique, no M10 redundancy) |
| TCF, nature='cnpj' | 121,744 | **64.1%** |

**Nature gain on real data: 40.9%** vs M10. 100% of the 200k CNPJs classify as
`compressible` under `SPEC_CNPJ` (real Receita check digits match the welded
mod-11 exactly), so the `n_compressible >= ~50%` activation gate is satisfied.
This is the ecological evidence the synthetic `br-identidades` could not provide
(well above the 5% real-world threshold).

## Reproduce

```bash
# stream-slice 200k rows (downloads only what's needed, not the full 2 GB):
python scripts/setup_receita_cnpj.py --rows 200000 --cap-mb 600 --period 2026-05
python scripts/csv_to_sqlite.py receita-cnpj

# inspect the remote tree first (no download):
python scripts/setup_receita_cnpj.py --list
# process an already-downloaded zip (no network):
python scripts/setup_receita_cnpj.py --zip <path/to/Estabelecimentos0.zip> --rows 200000
```

## Caveats

- **Volume 200k > shaper's validated ≤100k regime** (T-SHAPER-CODE-HARDENING):
  use direct `encode()` on columns, not shaper sampling.
- `municipio_cod` is the **Receita** municipality code, not the IBGE code used by
  `ibge-municipios` — they are different code systems.
- The 2000-row fixture `datasets/samples/receita-cnpj/cnpj-2k.csv` is committed
  for a future real-world snapshot gate (real CNPJ check-digit column).
