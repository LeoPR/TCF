# nome_vazio

**Produção**: `\z` — chave vazia num objeto

## Entrada

```json
{"": "x"}
```

## Wire

```
#TCF.8H#O\z
x

```

header = **11 B** de **14 B** (79%)

## Header, pedaço a pedaço

- `#TCF.8H`  (7 B)  assinatura + discriminador H
- `#O`  disc de RAIZ — objeto único na raiz
- `\z`  os campos

## Round-trip

`decode(encode(x)) == x` -> **True**
