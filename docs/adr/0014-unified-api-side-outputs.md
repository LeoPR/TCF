# 0014 — API unificada `encode(list|dict)` + SideOutputs recipiente

**Status**: accepted + welded
**Date**: 2026-05-24
**Deciders**: project owner
**Tags**: welding, api, unification, side-outputs, debug, schema-builder-preparation

## Context and Problem Statement

ADR-0013 (2026-05-23) welded multi-column como `encode_table` / `decode_table`
separados de `encode` / `decode` single-column. Opcao A foi escolhida com
argumento "Explicit > implicit". Owner revisou a decisao 2026-05-24:

1. **"Single eh caso particular de multi com 1 coluna"** — observacao
   conceitual. A "encode unit" eh sempre per-coluna; "single" e "multi"
   sao apenas politicas de empacotamento.

2. **Formato eh self-describing pelo shebang** (`#TCF.6 M` indica multi).
   Decoder pode dispatchar sem ambiguidade. O argumento "explicit" do
   ADR-0013 nao se sustenta na pratica: type-dispatch eh idiomatico em
   Python (`json.dumps`, `len`, `iter`).

3. **Logs internos sao gerados mas descartados**. OBAT `processar` retorna
   `(tokens, log)`; encoder descarta com `_log`. HCC tem `get_trace()` /
   `get_rede()` publicos. `detect_cadence_from_features` retorna info que
   eh descartada. Tudo desperdicado — poderia ser exposto via recipiente
   opcional pra debug, schema builder, analise.

4. **Plano v0.4 D13 (EncodeManager)** previa arquitetura multi-saida
   (file/multi-file/HTTP/TCP). Pre-requisito conceitual: a fachada deve
   nao distinguir single/multi — uma so' API que pode escalar pra workers
   paralelos.

## Considered Options

### Opcao A — Manter ADR-0013 (4 funcoes)

```python
encode(list) -> str
decode(text) -> list
encode_table(dict) -> (str, info)
decode_table(text) -> dict
```

Pros: explicit por nome
Contras: duplicacao, dispatcher fica externo ao TCF (caller decide)

### Opcao B — `encode(values)` overload aceitando dict

```python
encode(list | dict) -> str
decode(text) -> list | dict
```

Pros: 1 funcao, type-safe via dispatch, self-describing via shebang
Contras: return type variavel (str sempre — info via SideOutputs)

### Opcao C — `encode_columns(table)` (nome O-FMT-05 antigo)

Plural inconsistente com `encode` singular. Descartada em ADR-0013 ja'.

## Decision Outcome

**Opcao B — unificacao por dispatch**, ADR-0013 superseded (mas tickets
e diagramas que o referenciam permanecem validos pra historia).

### API publica final

```python
from tcf import encode, decode, SideOutputs

# Single (lista)
text = encode(["a", "b", "c"])           # -> str (body puro, sem shebang)
values = decode(text)                    # -> list[str]

# Multi (dict)
text = encode({"id": [...], "name": [...]})  # -> str (#TCF.6 M + bodies)
table = decode(text)                          # -> dict[str, list[str]]

# Side outputs opcional (debug, stats, schema futuro)
side = SideOutputs()
text = encode(data, side_outputs=side)
print(side.hcc_trace)
print(side.column_features)
print(side.multi_info)  # se data era dict
```

### Dispatch

- **Encoder**: por tipo (`isinstance(data, list)` vs `dict`)
- **Decoder**: pelo shebang (`startswith("#TCF.6 M")` -> multi)

### Backward compat

`encode_table` / `decode_table` permanecem como aliases re-exportados de
`tcf.multi`. Emitem `DeprecationWarning` com mensagem clara. Mantidos
indefinidamente pra migracao em passos; remocao decidida em ADR futuro
quando uso externo estiver baixo.

## Implementacao

### Novo modulo `src/tcf/side_outputs.py`

```python
@dataclass
class SideOutputs:
    # Pre-pass per-coluna
    column_features: ColumnFeatures | None = None
    cadence_detected: bool | None = None
    cadence_info: dict | None = None
    min_len: int | None = None

    # OBAT per-coluna
    obat_log: str | None = None
    obat_used_hint: bool | None = None

    # HCC per-coluna
    hcc_trace: str | None = None
    hcc_rede: str | None = None
    seq_rle_runs: list[dict] = field(default_factory=list)

    # Bytes per-coluna (pra schema/stats)
    body_bytes: int | None = None

    # Multi-col (so' se input foi dict)
    multi_info: dict | None = None
    per_col: dict[str, SideOutputs] | None = None
```

### Refactor `src/tcf/encoder.py`

`encode()` dispatcher + `_encode_column()` (a "encode unit" interna,
preparando D13 EncoderManager).

### Refactor `src/tcf/decoder.py`

`decode()` dispatcher pelo shebang + `_decode_column()` interno.

### Refactor `src/tcf/multi.py`

`_encode_multi` / `_decode_multi` privados (chamados via dispatch).
`encode_table` / `decode_table` permanecem como aliases deprecated.

### Atualizacoes em `src/tcf/__init__.py`

```python
from tcf.encoder import encode
from tcf.decoder import decode
from tcf.side_outputs import SideOutputs
from tcf.multi import encode_table, decode_table  # deprecated

__all__ = ["encode", "decode", "SideOutputs", "encode_table", "decode_table"]
```

## Consequences

**Positivas**:
- API publica enxuta (2 funcoes + 1 dataclass)
- Self-describing format aproveitado (decoder roteia sem caller decidir)
- Side outputs capturados sem reinventar — 100% reusa info ja' produzida
- "Encode unit" (`_encode_column`) explicita pra futura paralelizacao
  (D13 EncoderManager, T-CODE-ENCODER-MANAGER)
- Schema builder futuro vira consumidor de SideOutputs (T-CODE-SCHEMA-BUILDER)
- D17a 322B INVARIANT preservado byte-canonical

**Neutras**:
- ADR-0013 superseded (mas historicamente valido — manteremos tickets
  citando-o)
- Aliases deprecated ainda nao removidos (decisao adiada)

**Negativas**:
- Pequeno overhead (`isinstance` checks) na fachada — negligenciavel
- SideOutputs eh dataclass mutavel — risco de uso compartilhado entre
  threads no futuro; mitigado por cada `encode()` instanciar per_col novo

## Validacao byte-canonical

- D17a sint: 322 bytes (INVARIANT, identico pre/pos refactor)
- D1-D9 single-col: 1523 bytes (INVARIANT M10)
- Suite completa: 117 passed + 1 xfailed (era 96 passed pre-refactor,
  +21 tests novos: SideOutputs + UnifiedDispatch + DeprecatedAliases)
- 1 falha pre-existente em `test_shaper` (nao relacionada)

## Links

- [ADR-0013](0013-multi-column-canonical-api.md) — superseded (4 funcoes)
- [ADR-0011](0011-pacote1-weld-canonical.md) — pipeline M10 (base)
- [Plano v0.4 D13 EncodeManager](../workbench/research-notes/_archive/2026-05-05-v04-design-recap.md)
- [T-CODE-ENCODER-MANAGER](../../tickets/T-CODE-ENCODER-MANAGER.md) — P2 (paralelismo + sinks)
- [T-CODE-PLAN-CONTRACT](../../tickets/T-CODE-PLAN-CONTRACT.md) — P3 (Plan dataclass)
- [T-CODE-SCHEMA-BUILDER](../../tickets/T-CODE-SCHEMA-BUILDER.md) — P3 (consumidor SideOutputs)
- [T-CODE-OUTPUT-SINKS](../../tickets/T-CODE-OUTPUT-SINKS.md) — P2 (sinks pluggable)
