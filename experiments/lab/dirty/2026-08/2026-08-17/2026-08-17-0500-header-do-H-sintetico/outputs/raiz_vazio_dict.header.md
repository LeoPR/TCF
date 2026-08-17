# raiz_vazio_dict

**Produção**: `#E` — `{}`, sem corpo nenhum

## Entrada

```json
{}
```

## Wire

```
#TCF.8H#E

```

header = **9 B** de **10 B** (90%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `#E`  disc de RAIZ — objeto vazio

## Round-trip

`decode(encode(x)) == x` -> **True**
