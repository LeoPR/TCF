# Larguras do índice bN — gerada de `_largura`, não digitada

`w = ceil(log2(k))`, **não** arredondado pra potência de 2: `k=5` usa 3 bits, não 4.
O teto é `MAX_W=8` — a primeira faixa com `w > 8` é onde o bN se retira.

| `k` | `w` | |
|---:|---:|---|
| 1 | 0 | não ativa — o core resolve com RLE |
| 2 | 1 | ativa |
| 3–4 | 2 | ativa |
| 5–8 | 3 | ativa |
| 9–16 | 4 | ativa |
| 17–32 | 5 | ativa |
| 33–64 | 6 | ativa |
| 65–128 | 7 | ativa |
| 129–256 | 8 | ativa |
| 257–512 | 9 | **não ativa** — passa do teto MAX_W=8 |

O desperdício que o `T-BN-LARGURA-VARIAVEL` ataca não é arredondamento pra
potência de 2 (não existe) — é arredondamento pro **inteiro**: `k=5` gasta 3 bits
onde a entropia pede log2(5) ≈ 2,32.
