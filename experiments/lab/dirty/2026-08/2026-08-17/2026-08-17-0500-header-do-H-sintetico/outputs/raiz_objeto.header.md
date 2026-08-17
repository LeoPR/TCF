# raiz_objeto

**Produção**: `#O` — objeto único na raiz

## Entrada

```json
{"a": "x", "b": "y"}
```

## Wire

```
#TCF.8H#Oa:2,b
x
y

```

header = **14 B** de **19 B** (74%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `#O`  disc de RAIZ — objeto único na raiz
- `a:2,b`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
