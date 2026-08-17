# INDEX — avaliação do `.8H`

As capacidades gravadas com entrada, wire e roundtrip.

| capacidade | bytes | RT | header |
|---|---:|:--:|---|
| plano 1 campo | 20 | ✓ | `#TCF.8Hnome` |
| plano 3 campos | 35 | ✓ | `#TCF.8Ha:6,b:6,c` |
| TIPOS (s/n/b) | 54 | ✓ | `#TCF.8Hs:5,n:6n,f:9n,b:8b` |
| objeto aninhado | 31 | ✓ | `#TCF.8Ho{rua:7,n` |
| objeto 2 níveis | 18 | ✓ | `#TCF.8Ha{b{c` |
| array de escalares | 29 | ✓ | `#TCF.8Htel#:6[` |
| array de objetos | 26 | ✓ | `#TCF.8Ht#:6[n` |
| array de arrays | 51 | ✓ | `#TCF.8Hm#:6[#:12[` |
| NULL | 19 | ✓ | `#TCF.8Ha?:5` |
| ragged (campo falta) | 26 | ✓ | `#TCF.8Ha:4,b?:4` |
| dict escalar (raiz O) | 13 | ✓ | `#TCF.8H#Oa` |
| escalar solto (raiz V) | 16 | ✓ | `#TCF.8H#V\z` |
| lista vazia | 7 | ✓ | `#TCF.8` |
| dict vazio | 10 | ✓ | `#TCF.8H#E` |
