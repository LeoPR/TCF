# tipo_misto_de_campos

**Produção**: campos de tipos DIFERENTES lado a lado (str, n, b)

## Entrada

```json
[{"s": "x", "n": 1, "b": true}, {"s": "y", "n": 2, "b": false}]
```

## Wire

```
#TCF.8Hs:4,n:6n,b:11b
x
y
\1
\2
true
false

```

header = **21 B** de **43 B** (49%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `s:4,n:6n,b:11b`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
