# INDEX — grafia fracional e escala com excecoes

Wires em `<caso>.<mecanismo>.tcf`; contra-prova em `<caso>.*.roundtrip.json`;
procedencia em `<caso>.meta.json`; a decisao aberta em `../intermediates/`.

| caso | ideia | hoje | M1 fração | M2 escala | M3 exc-grafia | M3b exc-`_` | FLOOR |
|---|---|---|---|---|---|---|---|
| [`owner-sujo-no-meio`](./owner-sujo-no-meio.baseline.tcf) | O CASO DO OWNER, literal: coluna de 1 casa com um sujo de 9 casas no m | 53 | 52 | 79 | 51 | 52 | **M3** -2 B |
| [`owner-sem-o-sujo`](./owner-sem-o-sujo.baseline.tcf) | CONTRA-PROVA do anterior: a MESMA coluna com o sujo trocado por um lim | 37 | — | 35 | 35 | 35 | **M2** -2 B |
| [`dizima-uniforme`](./dizima-uniforme.baseline.tcf) | 10x a MESMA dizima. O RLE de linha identica ja' resolve — aqui o mecan | 29 | 26 | 32 | 32 | 32 | **M1** -3 B |
| [`dizima-variada`](./dizima-variada.baseline.tcf) | 10 dizimas DIFERENTES. O nucleo nao tem repeticao de linha para comer; | 160 | 94 | 145 | 145 | 145 | **M1** -66 B |
| [`rateio-terco`](./rateio-terco.baseline.tcf) | O PARCELAMENTO do owner: 100 dividido em 3. Liga M1 (grafia) com M4 (s | 48 | 36 | 51 | 51 | 51 | **M1** -12 B |
| [`money-2casas`](./money-2casas.baseline.tcf) | Dinheiro limpo, 2 casas, valores NAO em progressao (de proposito: uma  | 114 | — | 111 | 107 | 111 | **M3** -7 B |
| [`money-com-terco`](./money-com-terco.baseline.tcf) | CONTRA-PROVA de money-2casas: a mesma coluna com UMA dizima no fim. E' | 124 | 124 | 188 | 118 | 127 | **M3** -6 B |
| [`borda-cientifica`](./borda-cientifica.baseline.tcf) | grafia sem 'casas' — M1 deve recusar | 27 | — | — | — | — | **nucleo-hoje** +0 B |
| [`borda-subnormal`](./borda-subnormal.baseline.tcf) | limit_denominator(5e-324) devolve 0 — M1 deve recusar ANTES disso | 24 | — | — | — | — | **nucleo-hoje** +0 B |
| [`borda-zero-negativo`](./borda-zero-negativo.baseline.tcf) | `==` nao distingue; M1 nao pode mexer | 23 | — | — | 24 | 25 | **nucleo-hoje** +0 B |
| [`borda-max-float`](./borda-max-float.baseline.tcf) | escala estoura 2^53 | 40 | — | — | — | — | **nucleo-hoje** +0 B |
| [`borda-precisao-suja`](./borda-precisao-suja.baseline.tcf) | 0.30000000000000004 NAO e' dizima: M1 deve recusar, M3 deve tratar com | 69 | 48 | — | — | — | **M1** -21 B |
| [`borda-com-nulo`](./borda-com-nulo.baseline.tcf) | o slot nulo atravessa | 43 | 31 | 44 | 44 | 44 | **M1** -12 B |
| [`borda-inteiro-em-float`](./borda-inteiro-em-float.baseline.tcf) | sem casas uteis — M1 recusa, M2 vence | 21 | — | 21 | 21 | 21 | **nucleo-hoje** +0 B |
| [`borda-uniao-int-float`](./borda-uniao-int-float.baseline.tcf) | a tag-UNIAO `n`: M1 so' pode tocar no elemento float | 29 | 26 | — | — | — | **M1** -3 B |
| [`real-wine-quality-alcohol`](./real-wine-quality-alcohol.baseline.tcf) | O CASO QUE QUEBROU A ESCALA no fechamento do float: 6 valores de 13-14 | 2881 | 2853 | — | 2772 | 2783 | **M3** -109 B |
| [`real-wine-quality-density`](./real-wine-quality-density.baseline.tcf) | 3-5 casas, entre 0.99 e 1.04. A coluna do PoC de junho (M4). | 10137 | — | 9757 | 9757 | 9757 | **M2** -380 B |
| [`real-online-retail-UnitPrice`](./real-online-retail-UnitPrice.baseline.tcf) | Money-like real: preco unitario. Onde uma SOMA tem sentido semantico ( | 3662 | — | 3378 | 3378 | 3378 | **M2** -284 B |
| [`real-tpch-sf001-l_discount`](./real-tpch-sf001-l_discount.baseline.tcf) | 2 casas, entre 0.00 e 0.10 — escala pura facil. | 1406 | — | 1389 | 1389 | 1389 | **M2** -17 B |
| [`real-tpch-sf001-l_extendedprice`](./real-tpch-sf001-l_extendedprice.baseline.tcf) | Money-like de maior magnitude. | 17018 | — | 15591 | 15591 | 15591 | **M2** -1427 B |
