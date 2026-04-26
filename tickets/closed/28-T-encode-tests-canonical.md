---
title: Testes roundtrip do encoder com dados canonicos
type: task
status: OPEN
priority: 27
parent: 24-M-phase2-tcf-refactor
---

# Testes Roundtrip Canonicos

## Objetivo

Validar que `encode_columns → decode` funciona com dados reais:
- TPC-H lineitem (60K rows, 16 cols, tipos mistos)
- TPC-H customer (1.5K rows, 8 cols, strings longas)
- Adult (48K rows, 15 cols, NULLs reais)

## Cenarios

```python
# 1. Lineitem 100 rows, L0-L3 roundtrip
# 2. Customer full (1.5K), L2 roundtrip
# 3. Adult 1000 rows, L0-L3 roundtrip
# 4. Adult com NULLs preservados no roundtrip
# 5. Lineitem full (60K), L3 — stress test
# 6. Tamanhos: TCF < CSV para L2+ em lineitem
# 7. encode_rows(list[dict]) == encode_columns(transposed)
```

## Depende de

- Ticket 25 (encode_columns)
- Ticket 26 (encode_rows)
- SQLite databases em Z: (ticket 06 DONE)
- DatasetReader (ticket 07 DONE)

## Tarefas

- [ ] Criar `tests/test_encode_canonical.py`
- [ ] Testes 1-7 acima
- [ ] Verificar que NULLs do Adult sobrevivem ao roundtrip
- [ ] Verificar que tipos numericos (int, float) sobrevivem
- [ ] Medir e registrar tamanhos (chars) por formato e nivel
