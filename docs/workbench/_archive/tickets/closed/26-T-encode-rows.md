---
title: encode_rows() — converte list[dict] para columnar e chama encode_columns
type: task
status: OPEN
priority: 25
parent: 24-M-phase2-tcf-refactor
---

# encode_rows()

## API proposta

```python
def encode_rows(
    table_name: str,
    rows: list[dict[str, Any]],
    *,
    config: EncodeConfig | None = None,
) -> str:
    """Encode row-oriented data to TCF text.

    Convenience wrapper: transposes rows to columns, then calls
    encode_columns(). This is what the shaper output naturally
    produces (list[dict]).
    """
```

## Implementacao

```python
def encode_rows(table_name, rows, *, config=None):
    if not rows:
        return encode_columns(table_name, {}, config=config)
    col_names = list(rows[0].keys())
    columns = {col: [str(row.get(col, "")) for row in rows] for col in col_names}
    return encode_columns(table_name, columns, config=config)
```

Trivial — a logica esta em `encode_columns()`.

## Conversao de tipos

Rows do shaper/SQLite podem ter int, float, None.
`encode_rows()` converte tudo para string antes de passar:
- `None` → `""` (string vazia)
- `int` → `str(int)`
- `float` → `str(float)` (ou `fmt_num` se precision configurada)

## Tarefas

- [ ] Criar `encode_rows()` em `src/tcf/encoder.py`
- [ ] Garantir conversao de tipos (int/float/None → str)
- [ ] Testes: encode_rows produz mesmo output que encode_columns com mesmos dados
- [ ] Testes: roundtrip encode_rows → decode → comparar com input
