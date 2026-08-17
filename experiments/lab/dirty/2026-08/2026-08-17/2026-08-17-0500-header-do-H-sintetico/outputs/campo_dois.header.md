# campo_dois

**Produção**: dois campos escalares, separados por `,`

## Entrada

```json
[{"a": "x", "b": "y"}, {"a": "z", "b": "w"}]
```

## Wire

```
#TCF.8Ha:4,b
x
z
y
w

```

header = **12 B** de **21 B** (57%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a:4,b`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
