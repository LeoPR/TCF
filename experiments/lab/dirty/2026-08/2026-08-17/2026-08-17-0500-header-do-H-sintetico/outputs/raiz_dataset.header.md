# raiz_dataset

**Produção**: dataset `list[dict]` — SEM disc de raiz (o caso base)

## Entrada

```json
[{"a": "x"}, {"a": "y"}]
```

## Wire

```
#TCF.8Ha
x
y

```

header = **8 B** de **13 B** (62%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
