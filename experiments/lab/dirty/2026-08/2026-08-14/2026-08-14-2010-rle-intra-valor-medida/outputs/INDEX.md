# INDEX — RLE intra-valor, primeira medição

Wires em `<caso>.tcf`; contra-prova em `<caso>.roundtrip.json`; procedência em
`<caso>.meta.json`. **Bloco 3 inverte o fluxo**: o wire é a ENTRADA
(`inputs/<caso>.wire-de-entrada.tcf`) e o JSON é a saída.

| bloco | caso | ideia | resultado |
|---|---|---|---|
| 1 | [`b1-com-run`](./b1-com-run.tcf) | par de contra-prova | 29 B |
| 1 | [`b1-sem-run`](./b1-sem-run.tcf) | par de contra-prova | 29 B |
| 2 | `b2-*-n004` | curva | 1 valor 15 B · 20 distintos 149 B |
| 2 | `b2-*-n008` | curva | 1 valor 19 B · 20 distintos 229 B |
| 2 | `b2-*-n016` | curva | 1 valor 27 B · 20 distintos 389 B |
| 2 | `b2-*-n032` | curva | 1 valor 43 B · 20 distintos 709 B |
| 2 | `b2-*-n064` | curva | 1 valor 75 B · 20 distintos 1349 B |
| 2 | `b2-*-n128` | curva | 1 valor 139 B · 20 distintos 2629 B |
| 2 | `b2-*-n256` | curva | 1 valor 267 B · 20 distintos 5189 B |
| 3 | [`f1-declara-e-referencia`](./f1-declara-e-referencia.decodificado.json) | declara `abc` sem emitir, e depois referencia por ^1 | aceito=True → `['def', 'abc']` |
| 3 | [`f2-so-fantasma`](./f2-so-fantasma.decodificado.json) | 1 linha no corpo, 0 elementos | aceito=True → `[]` |
| 3 | [`f3-count-negativo`](./f3-count-negativo.decodificado.json) | count NEGATIVO | aceito=True → `['def']` |
| 3 | [`f4-fantasma-ignorado`](./f4-fantasma-ignorado.decodificado.json) | fantasma nunca referenciado | aceito=True → `['x', 'y']` |
| 4 | [`r1-wine-alcohol`](./r1-wine-alcohol.tcf) | run em 0.62% | hoje 8676 B · teto(5ch) -1.89% |
| 4 | [`r2-tpch-o-clerk`](./r2-tpch-o-clerk.tcf) | run em 100.0% | hoje 75522 B · teto(5ch) -1.7% |
| 4 | [`r3-tpch-c-name`](./r3-tpch-c-name.tcf) | run em 100.0% | hoje 87 B · teto(5ch) +6.9% |
