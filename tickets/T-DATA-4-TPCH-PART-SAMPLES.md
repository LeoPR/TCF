---
title: T-DATA-4-TPCH-PART-SAMPLES — Emitir samples committed de part/partsupp do TPC-H (categoria hierarquica observavel)
status: closed-done
priority: P3
created: 2026-06-01
updated: 2026-06-01
closed: 2026-06-01
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

- [x] `datasets/samples/tpch-sf001/part-sample.csv` (100 rows) committed
- [x] `datasets/samples/tpch-sf001/partsupp-sample.csv` (100 rows) committed
- [x] idem para tpch-sf01 (part + partsupp, 100 rows cada)
- [x] p_type/p_brand/p_container observaveis dos samples

## Resolucao (2026-06-01)

4 samples emitidos (part + partsupp para sf001 e sf01), 100 rows cada,
como fatia direta das primeiras 101 linhas do CSV externo em Z: (mesmo
metodo dos samples tpch existentes — nao re-serializado via SQLite, pra
manter consistencia byte). Header de cada um confere com a ordem de
colunas do metadata.json (verificado). p_type (hierarquia space-separated,
ex "PROMO BURNISHED COPPER"), p_brand, p_mfgr, p_container agora observaveis
dos samples git-tracked (antes metadata-deep). Sem download; pura emissao
do que ja' estava em Z:.

## Conexoes

- Origem: design workflow 2026-06-01 (gap: categoria hierarquica so'
  metadata-deep no TPC-H)
- Complementa ibge-municipios (unica outra fonte hierarquica)
