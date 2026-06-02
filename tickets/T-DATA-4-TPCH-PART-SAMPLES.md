---
title: T-DATA-4-TPCH-PART-SAMPLES — Emitir samples committed de part/partsupp do TPC-H (categoria hierarquica observavel)
status: open
priority: P3
created: 2026-06-01
updated: 2026-06-01
blocked-by: []
related:
  - datasets/samples/tpch-sf001/   (faltam part-sample.csv / partsupp-sample.csv)
  - datasets/samples/tpch-sf01/
  - scripts/dataset_reader.py       (le hub SQLite ja' em Z:)
  - scripts/setup_tpch.py
---

# T-DATA-4-TPCH-PART-SAMPLES — Samples de part/partsupp

## Contexto

Achado do design workflow 2026-06-01: os samples committed de TPC-H cobrem
region/nation/supplier/customer/orders/lineitem mas **NAO part nem partsupp**.
Logo `p_type` (hierarquia slash/space), `p_brand`, `p_container`, `p_mfgr` —
a unica outra fonte de **categoria hierarquica/composta** alem do ibge —
existem so' em `metadata.json`, invisiveis pra quem trabalha dos samples
git-tracked (testes, snapshots, leitura read-only).

## Plano

1. Confirmar que o hub `Z:/tcf-data/interim/tpch-sf001.db` (e sf01) tem
   part/partsupp (ja' confirmado: partsupp 8000/80000 rows).
2. Via `scripts/dataset_reader.py`, ler part e partsupp e emitir
   `part-sample.csv` (100 rows) + `partsupp-sample.csv` (100 rows) em
   `datasets/samples/tpch-sf001/` (e opcionalmente sf01).
3. Header na ordem do metadata. Commitar so' os samples leves.

**Custo**: trivial (S). Sem download, sem tocar dado de producao — pura
emissao de sample do que ja' esta' no disco em Z:.

## Criterio de aceite

- [ ] `datasets/samples/tpch-sf001/part-sample.csv` (100 rows) committed
- [ ] `datasets/samples/tpch-sf001/partsupp-sample.csv` (100 rows) committed
- [ ] (opcional) idem para tpch-sf01
- [ ] p_type/p_brand/p_container observaveis dos samples

## Conexoes

- Origem: design workflow 2026-06-01 (gap: categoria hierarquica so'
  metadata-deep no TPC-H)
- Complementa ibge-municipios (unica outra fonte hierarquica)
