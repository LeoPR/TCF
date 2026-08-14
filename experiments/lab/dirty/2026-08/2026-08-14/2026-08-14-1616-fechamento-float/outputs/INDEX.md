# INDEX — fechamento do float

| borda | ideia | resultado |
|---|---|---|
| [`float-exato`](./borda-float-exato.tcf) | int em roupa de float — o `1.` do owner | RT ok |
| [`zero-negativo`](./borda-zero-negativo.tcf) | `-0.0` != `0.0` no sinal; `==` NAO detecta | RT ok |
| [`cientifica-pequena`](./borda-cientifica-pequena.tcf) | grafia `1e-05` vem do proprio Python | RT ok |
| [`cientifica-grande`](./borda-cientifica-grande.tcf) | grafia `1e+20` | RT ok |
| [`max-float`](./borda-max-float.tcf) | o maior float representavel | RT ok |
| [`subnormal`](./borda-subnormal.tcf) | o menor subnormal — borda inferior do IEEE-754 | RT ok |
| [`precisao-suja`](./borda-precisao-suja.tcf) | 0.30000000000000004 — 17 digitos | RT ok |
| [`misto-int-float`](./borda-misto-int-float.tcf) | a UNIAO `int|float` na mesma tag `n` | RT ok |
| [`com-nulo`](./borda-com-nulo.tcf) | o slot 0 atravessa qualquer tag | RT ok |
| [`nan`](./borda-nan.tcf) | fora do JSON (RFC 8259) -> FAIL-LOUD | RECUSA HierarchicalError |
| [`infinito`](./borda-infinito.tcf) | idem | RECUSA HierarchicalError |
| [`menos-infinito`](./borda-menos-infinito.tcf) | idem | RECUSA HierarchicalError |

Colunas reais em `real-*.tcf` com contra-prova `.roundtrip.json`.
Eixos 1-4 medidos em `../intermediates/eixos-reais.json`.
