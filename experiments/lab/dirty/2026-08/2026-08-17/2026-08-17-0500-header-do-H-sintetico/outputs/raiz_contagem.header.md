# raiz_contagem

**Produção**: `#D<N>` — lista de objetos SEM campo (só a contagem sobrevive)

## Entrada

```json
[{}, {}, {}]
```

## Wire

```
#TCF.8H#D3

```

header = **10 B** de **11 B** (91%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `#D3`  disc de RAIZ — lista de N objetos sem campo

## Round-trip

`decode(encode(x)) == x` -> **True**
