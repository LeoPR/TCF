---
title: Sub-exp 02 — Variante A (raw + M10, sem pre-tx)
status: completed-via-01
---

# Sub-exp 02 — Variante A (raw)

**Mesmo que sub-exp 01**: `encode(values)` direto, sem pre-tx.

Resultados em [`../01-caracterizacao/manifest.jsonl`](../01-caracterizacao/manifest.jsonl).

Variante A serve de **baseline** pra comparar com B (base-encoded)
e C (hibrido). Achado em 01: M10 ratio = 120-126% (PIOR que raw),
porque marcadores fixos + alta entropia geram overhead sem ganho.

Decisao: nao re-rodar — usar numeros do 01 diretamente. Sub-exps
03/04 comparam contra estes.
