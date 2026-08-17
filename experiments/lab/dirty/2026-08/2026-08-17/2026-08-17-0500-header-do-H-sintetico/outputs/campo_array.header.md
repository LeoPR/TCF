# campo_array

**Produção**: `#:<size>[` — coluna de contagem + coluna de itens

## Entrada

```json
[{"a": ["x", "y"]}, {"a": ["z"]}]
```

## Wire

```
#TCF.8Ha#:6[
\2
\1
x
y
z

```

header = **12 B** de **25 B** (48%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a#:6[`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
