# tipo_numero

**Produção**: tag `n` na forma do campo

## Entrada

```json
[{"a": 1}, {"a": 2}]
```

## Wire

```
#TCF.8Ha:6n
\1
\2

```

header = **11 B** de **18 B** (61%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a:6n`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
