---
title: EXP-012 — Real-world test em Adult Census via shaper
type: clean-experiment
status: active
tags: [tcf, real-world, multi-column, adult-census, scale]
created: 2026-05-18
updated: 2026-05-18
predecessor: EXP-011-multi-column-basic
related:
  - scripts/shaper/README.md
  - scripts/dataset_reader.py
  - experiments/lab/dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md
---

# EXP-012 — Real-world test em Adult Census

**Data**: 2026-05-18
**Tipo**: experimento clean
**Estado**: ativo
**Predecessor**: EXP-011 (multi-column basic em D17a sintetico)

## Pergunta cientifica

EXP-011 pipeline (`encode_table`) generaliza pra dados reais
**multi-coluna em escala** (Adult Census, 15 colunas × 48k rows)?

Especificamente:
- RT byte-canonical preservado?
- Bytes vs raw CSV em volumes variados (100, 500, 1000, 5000 rows)?
- Auto-detect cadence per-coluna funciona em tipos reais
  (int, string categorica, com missing `?`)?
- Algum tipo de coluna QUEBRA o pipeline?
- Comportamento de escala: bytes/row converge ou degrade?

## Infra utilizada (NAO recriar — ja' existe)

- **`scripts/dataset_reader.py`** — `DatasetReader("adult-census")`
- **`scripts/shaper/`** — `Shaper().apply(ShapeRequest(...))`
- **`Z:/tcf-data/interim/adult-census.db`** — SQLite hub
- **`scripts/_paths.py`** — resolve via `config/storage.json`

Sub-amostragem controlada via shaper:
```python
req = ShapeRequest(
    dataset="adult-census",
    volume=1000,        # ou 100, 500, 5000
    order="natural",    # ou random/sorted/reverse
    seed=42,
    fk_preserving=False,  # Adult Census e' single-table
)
```

## Pipeline aplicado

EXP-011 `encode_table` (welded em EXP-010):
- Pre: `detect_cadence(strings, threshold=0.7)` por coluna
- OBAT: canonical OU shape-preserve (decidido pelo Pre)
- HCC: fork seq-RLE
- Header: `#TCF.6 M` + `# size=name,...`

## Datasets

| Dataset | rows | cols | Tipos |
|---|---:|---:|---|
| Adult Census full | 48,842 | 15 | int, string, categorical |
| Volumes testados | 100, 500, 1000, 5000 | 15 | shaper amostrado |

## Validacao

Cada volume:
1. RT byte-canonical: `decode_table(encode_table(t)) == t`
2. Bytes total vs raw CSV equivalente
3. Stats per-coluna (cadence_detected, n_seq_runs)
4. Bytes/row pra detectar overhead

## Aceite

- **RT 100%** em todos os volumes (sine qua non)
- **Bytes < raw CSV** em ao menos 1 volume (compressao real)
- **Comportamento de escala documentado** (bytes/row pra cada N)

## Hipoteses derivadas (testar tambem)

- **H-RW-01**: pipeline RT OK em real-world multi-col
- **H-RW-02**: auto-detect cadence funciona em colunas
  numericas reais (int sem cadencia forte)
- **H-RW-03**: colunas com missing `?` nao quebram
- **H-RW-04**: ganho vs raw CSV aumenta com volume (mais
  redundancia detectavel)

## Estrutura

```
EXP-012-real-world-adult-census/
├── README.md (este)
├── run.py (varias volumes via shaper)
├── report.md (gerado)
└── outputs/
    └── adult-volume-<N>.tcf
```

## See also

- **Predecessor**: [EXP-011 multi-column basic](../EXP-011-multi-column-basic/)
- **Infra usada**: [shaper README](../../../../scripts/shaper/README.md)
- **Checkpoint retomado**: [`2026-05-18 pausa`](../../dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md)
- **ADR header multi**: [ADR-0004](../../../../docs/adr/0004-multi-column-header-compacto.md)
