# tipo_bool

**Produção**: tag `b` na forma do campo

## Entrada

```json
[{"a": true}, {"a": false}]
```

## Wire

```
#TCF.8Ha:11b
true
false

```

header = **12 B** de **24 B** (50%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a:11b`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
