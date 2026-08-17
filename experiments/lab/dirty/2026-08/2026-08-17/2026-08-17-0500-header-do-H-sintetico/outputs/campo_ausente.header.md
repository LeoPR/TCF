# campo_ausente

**Produção**: ragged: campo que falta numa linha (também usa máscara)

## Entrada

```json
[{"a": "x", "b": "y"}, {"a": "z"}]
```

## Wire

```
#TCF.8Ha:4,b?:4
x
z
.
-
y

```

header = **15 B** de **26 B** (58%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a:4,b?:4`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
