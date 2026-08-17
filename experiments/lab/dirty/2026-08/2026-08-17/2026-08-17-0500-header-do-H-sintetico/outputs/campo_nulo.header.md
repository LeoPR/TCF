# campo_nulo

**Produção**: máscara `?:<size>` — vem ANTES da coluna do campo

## Entrada

```json
[{"a": "x"}, {"a": null}]
```

## Wire

```
#TCF.8Ha?:5
.
\0
x

```

header = **11 B** de **19 B** (58%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a?:5`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
