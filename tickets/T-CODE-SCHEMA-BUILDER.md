---
title: T-CODE-SCHEMA-BUILDER — Orquestrador que consume SideOutputs
status: open-fase-1-welded
priority: P3
created: 2026-05-24
updated: 2026-05-24
blocked-by: []
related:
  - docs/adr/0014-unified-api-side-outputs.md
  - tickets/META-TYPE-ENCODERS.md
  - experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md
---

# T-CODE-SCHEMA-BUILDER — Helper orquestrador

## Contexto

ADR-0014 introduziu `SideOutputs` recipiente. Captura ColumnFeatures,
cadence_info, min_len, OBAT log, HCC trace/rede, seq_rle_runs, bytes
per coluna — tudo info ja' produzida pelo pipeline canonical.

Lacuna: nao ha' **orquestrador formal** que consuma SideOutputs e
produza um "schema" rico do dataset (tipos inferidos, naturezas
detectadas, hints pra encoder/users).

META-TYPE-ENCODERS (OPEN desde 2026-05-15) tem plano de 8 naturezas
(Templated/Enumerated/Checked/Composite/Hierarchical/Lossy/High-entropy)
adiado. Schema builder eh o **frontend natural** dessas naturezas:
detect cada natureza, agrega num schema unificado.

## Hipotese

H1: orquestrador pode produzir schema rico O(N) consumindo SideOutputs
ja' computado (1 passada extra zero — info ja' disponivel).
H2: schema gerado pode alimentar:
- Encoder default (sem usuario configurar — schema auto)
- Documentacao auto (Markdown/JSON com naturezas detectadas)
- Validacao (data nova vs schema previo: drift detection)

## Plano

### Fase 1 — Orquestrador basico

```python
from tcf import build_schema, encode, SideOutputs

# Modo 1: implicito (build_schema chama encode internamente)
schema = build_schema(data)

# Modo 2: explicito (reusa side_outputs ja' capturado)
side = SideOutputs()
text = encode(data, side_outputs=side)
schema = build_schema_from_side(side, data)
```

### Fase 2 — Schema dataclass

```python
@dataclass
class ColumnSchema:
    name: str
    n_rows: int
    n_unicas: int
    avg_len: float
    is_numeric: bool
    cadence: bool
    min_len: int
    body_bytes: int
    # Naturezas detectadas (futuro):
    natures: list[str] = field(default_factory=list)  # ex: ["incremental", "templated:date"]

@dataclass
class TableSchema:
    n_rows: int
    n_cols: int
    columns: dict[str, ColumnSchema]
    total_bytes: int
```

### Fase 3 — Detectores adicionais (META-TYPE-ENCODERS)

Conforme T02-T07 forem validados em real-world, integrar:
- `detect_templated` (date, email, uuid, CPF, IP, telefone)
- `detect_enumerated` (low-card categorical)
- `detect_checked` (digit verificador)
- `detect_composite` (datetime split, money split)
- `detect_hierarchical` (paths, URLs)

Cada detector consome ColumnFeatures + amostra; produz hint/natureza.

### Fase 4 — Outputs derivados

- `schema.to_json()` -> compativel com `datasets/canonical/*/metadata.json`
- `schema.to_markdown()` -> doc auto
- `schema.diff(other_schema)` -> drift detection

## Criterio de aceite

- [ ] Fase 1: `build_schema(data)` retorna `TableSchema` byte-identical
  pra outputs de encode (mesmo bytes)
- [ ] Fase 2: dataclass `ColumnSchema` + `TableSchema` em
  `src/tcf/schema.py`
- [ ] Fase 3: pelo menos 2 detectores novos integrados
- [ ] Fase 4: `to_json` produz output compativel com metadata.json
  canonico

## Riscos

1. **Naturezas T02-T07 sao especulativas**: META-TYPE-ENCODERS adiado
   ate' real-world validar. Schema builder pode ficar com so' Fase 1-2.
2. **Schema vs metadata canonico**: formato `metadata.json` ja' existe
   em `datasets/canonical/`. Convergir ou separar?
3. **Sobreposicao com dataset_reader**: `scripts/dataset_reader.py` ja'
   tem `column_stats()`. Reusar ou refatorar?

## Conexao

- [ADR-0014](../docs/adr/0014-unified-api-side-outputs.md) — SideOutputs
- [META-TYPE-ENCODERS](META-TYPE-ENCODERS.md) — T02-T07 naturezas
- [naturezas-numericas-2026-05-23](../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md)
- [scripts/dataset_reader.py](../scripts/dataset_reader.py) — column_stats
- [datasets/canonical/*/metadata.json](../datasets/canonical/) — formato existente

## Updates datados

### 2026-05-24 — abertura

Ticket aberto pos-ADR-0014. Schema builder eh consumidor natural de
SideOutputs. Plano em 4 fases. Fase 1+2 viaveis ja'; Fase 3+ depende de
META-TYPE-ENCODERS reabrir.

### 2026-05-24 — Fase 1+2 WELDED (orquestrador + dataclasses)

Owner aprovou Fase 1. Implementado num so' commit (Fase 1 + 2 juntas
porque sao trivialmente acopladas):

**Novo `src/tcf/schema.py`**:
- `@dataclass ColumnSchema` (Fase 2): name, n_rows, n_unicas, avg_len,
  cardinality, is_numeric, cadence_detected, cadence_rule, min_len,
  body_bytes, seq_rle_runs_count, sample, **natures placeholder vazio**
- `@dataclass TableSchema`: n_rows, n_cols, columns, total_bytes,
  header_bytes, body_bytes, is_multi_col
- `build_schema(data)` (Fase 1): orquestrador chama `encode()`
  internamente com SideOutputs + monta TableSchema
- `to_dict()` + `to_json(indent=2)` em ambos (Fase 4 parcial)

**`src/tcf/__init__.py`**: exporta `build_schema`, `TableSchema`,
`ColumnSchema`.

**Tests** (`tests/test_schema.py`):
- 24/24 passing
- TestBuildSchemaDispatch (3): list/dict/invalid
- TestColumnSchema (8): features, numeric, cadence, sample, etc.
- TestTableSchemaMulti (3): n_rows, byte breakdown, per-col features
- TestTableSchemaSingle (2): no header, val default name
- TestD17aSchema (4): basic shape (322B INVARIANT), timestamp cadence,
  id numeric+cadence, categoria low-cardinality
- TestSerialization (3): to_dict, to_json valid, D17a JSON
- TestDeterminism (1): same input -> same schema

**Suite completa**: 155 passed (+24) + 1 xfailed + 1 pre-existing
fail test_shaper (nao relacionado).

**Reaproveitamento (zero recomputacao)**:
- ColumnFeatures: analyze_column via SideOutputs.column_features
- detect_cadence_from_features: cadence_detected + cadence_rule
- detect_min_len_from_features: min_len
- HCC seq_rle_runs: len(side.seq_rle_runs)
- multi_info: total/header/body bytes diretamente

**Status Fase 1+2**: WELDED. Output deterministico (mesmo input -> mesmo
schema). JSON serializavel pra storage/diff/doc auto.

### Proximos passos

- **Fase 3** (P3, depende META-TYPE-ENCODERS reabrir): integrar
  detectores de naturezas (templated/checked/enumerated/etc) — populariam
  `column.natures: list[str]` que hoje eh placeholder vazio
- **Fase 4** (P3 opcional): outputs derivados
  - `schema.to_markdown()` -> doc auto formatado
  - `schema.diff(other_schema)` -> drift detection
  - `schema.to_metadata_json()` -> compat com `datasets/canonical/*/metadata.json`
