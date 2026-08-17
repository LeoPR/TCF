# nome_com_separador

**Produção**: nome que contém os separadores do meta (`,` `:` `#`)

## Entrada

```json
[{"a,b": "x", "c:d": "y"}, {"a,b": "z", "c:d": "w"}]
```

## Wire

```
#TCF.8Ha\,b:4,c\:d
x
z
y
w

```

header = **18 B** de **27 B** (67%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `a\,b:4,c\:d`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
