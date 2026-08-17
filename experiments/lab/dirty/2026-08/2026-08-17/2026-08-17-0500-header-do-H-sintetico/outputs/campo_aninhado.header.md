# campo_aninhado

**Produção**: `{` — objeto dentro de campo, achatado no caminho

## Entrada

```json
[{"a": {"b": "x"}}, {"a": {"b": "y"}}]
```

## Wire

```
#TCF.8Ha{b
x
y

```

header = **10 B** de **15 B** (67%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a{b`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
