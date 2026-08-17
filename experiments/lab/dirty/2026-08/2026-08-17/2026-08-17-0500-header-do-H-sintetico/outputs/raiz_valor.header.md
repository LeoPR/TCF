# raiz_valor

**Produção**: `#V` + nome de campo `\z` — escalar solto na raiz

## Entrada

```json
"x"
```

## Wire

```
#TCF.8H#V\z
x

```

header = **11 B** de **14 B** (79%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `#V`  disc de RAIZ — valor solto na raiz
- `\z`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
