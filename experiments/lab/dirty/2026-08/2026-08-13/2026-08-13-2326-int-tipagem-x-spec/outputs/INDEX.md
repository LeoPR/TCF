# INDEX — a matriz tipagem × spec

| regime | str+core | str+spec | int+core | int+spec* | alvo(str) | alvo(int) |
|---|---:|---:|---:|---:|---|---|
| `prog-passo1` | 36 | 26 | 37 | 27 | int-pad | int-pad |
| `prog-passo7` | 48 | 27 | 49 | 28 | int-pad | int-pad |
| `prog-largura-fixa` | 22 | 22 | 23 | 30 | int-pad | int-pad |
| `prog-epoch` | 81 | 29 | 82 | 30 | int-offpad | int-offpad |
| `prog-base-alta` | 65 | 26 | 66 | 27 | int-offpad | int-offpad |
| `id-aleatorio-6` | 4209 | 3217 | 4210 | 3017 | int-b94 | int-b94 |
| `id-aleatorio-11` | 7209 | 4730 | 7210 | 4217 | int-b94 | int-b94 |
| `faixa-0-100` | 1110 | 1110 | 1111 | 1044 | int-pad | int-b94 |
| `cardinalidade-5` | 333 | 333 | 334 | 337 | int-pad | int-b94 |
| `quase-constante` | 25 | 25 | 26 | 32 | int-pad | int-b94 |
| `negativos` | 2627 | 2627 | 2628 | 2688 | int-pad | int-b94 |
| `com-nulos` | 240 | 232 | 241 | 247 | int-pad | int-pad |
| `gigante-64bit` | 82 | 26 | 83 | 27 | int-offpad | int-offpad |
| `misto-int-float` | 2899 | 2899 | 2900 | 3107 | int-pad | int-b94 |

`int+spec*` é **simulado**: `nature=` recusa entrada tipada nas três rotas (as recusas literais estão em `../intermediates/<regime>.matriz.json`). O número é o custo do corpo transformado + header tipado + tag, com o round-trip verificado à mão comparando TIPO.
