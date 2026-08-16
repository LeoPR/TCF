# INDEX — verificação vermelho→verde dos welds C1/C2/C3

O código PRÉ-weld vem do git (`git archive <sha>^ src`) e o MESMO repro roda em
subprocesso contra as duas versões. Não há afirmação minha no meio.

| weld | ticket | commit | antes | depois | confirmado |
|---|---|---|---|---|---|
| C2 | `T-META-COLISAO-NOME-POSICIONAL` | `0dec1a06` | [antes](./C2-antes.json) | [depois](./C2-depois.json) | ✓ |
| C3 | `T-NATURE-IGNORADA-CALADA` | `ec08634c` | [antes](./C3-antes.json) | [depois](./C3-depois.json) | ✓ |
| C1 | `T-POLARIDADE-COME-NOME` | `2464f561` | [antes](./C1-antes.json) | [depois](./C1-depois.json) | ✓ |
