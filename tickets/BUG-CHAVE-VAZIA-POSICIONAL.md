---
title: BUG-CHAVE-VAZIA-POSICIONAL — dict {"": [...]} volta {"0": [...]} — único caso onde o TCF ALTERA
status: open
priority: P2
severity: R1 (avisa, não é silencioso — mas o RT quebra)
created: 2026-08-01
updated: 2026-08-01
gate: byte-canonical (toca rota flat/multi — precisa aprovação + test_real_world_snapshots)
blocked-by: []
related:
  - src/tcf/encoder.py
  - experiments/lab/dirty/2026-08/2026-08-01/2026-08-01-0309-json-lib-roundtrip-comportamento/
---

# BUG-CHAVE-VAZIA-POSICIONAL — `{"": ["a","b"]}` → `{"0": ["a","b"]}`

Achado do lab `2026-08-01-0309-json-lib-roundtrip-comportamento` (matriz json × tcf, 29 casos):
o **único** caso em que o TCF altera o dataset em vez de preservar ou falhar alto.

## Comportamento observado

```python
decode(encode({"": ["a", "b"]}))   # -> {"0": ["a", "b"]}  (com UserWarning)
```

O encoder trata nome de coluna vazio `""` como **coluna anônima** e avisa (`UserWarning`);
o decode devolve o nome **posicional** `"0"`. O RT `{"": ...}` → `{"0": ...}` quebra tipo
e valor da chave. Não é silencioso (há warning), mas é **mutação** — e o TCF não altera,
ou preserva ou fail-loud; este caso foge do contrato.

## Contraste

- `.8H` já resolve chave `""` **com escape** (weld 2026-07-17, `da1aa73`+`d72b9eb` — escape
  D_json cobre chave vazia/LF/CR em valor e nome, ~57k RT adversarial). A rota que perde é a
  flat/multi (coluna sem nome = anônima posicional).
- json lib: preserva `""` de graça (grupo "ambos preservam" quebrado só por este caso no TCF).

## Opções (a decidir)

1. **fail-loud** na rota flat/multi para chave `""` (alinhado ao contrato "não altera"); ou
2. **preservar** `""` via o mesmo escape do `.8H` (custo: grafia nova na rota flat — verificar
   se há slot livre no name-guard).

## Evidência

`outputs/matriz.csv` do lab (caso `chave-vazia`) + `result.md` §surpresas.
