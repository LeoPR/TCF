# INDEX — a perda por cinco lentes

**Aviso**: os `.tcf` deste lab contêm valores **arredondados de propósito**. O
`roundtrip.json` prova que o FORMATO é lossless sobre eles — não que o valor é o
original. O original está em `inputs/retail-preco.entrada.json`.

| caso | d | método | bytes | soma exata | erro/valor | erro receita |
|---|---|---|---|---|---|---|
| [`d4-ingenuo`](./d4-ingenuo.tcf) | 4 | ingenuo | 5053 | True | 0.0% | 0.0% |
| [`d4-maior-resto`](./d4-maior-resto.tcf) | 4 | maior-resto | 5053 | True | 0.0% | 0.0% |
| [`d3-ingenuo`](./d3-ingenuo.tcf) | 3 | ingenuo | 5053 | True | 0.0% | 0.0% |
| [`d3-maior-resto`](./d3-maior-resto.tcf) | 3 | maior-resto | 5053 | True | 0.0% | 0.0% |
| [`d2-ingenuo`](./d2-ingenuo.tcf) | 2 | ingenuo | 5053 | True | 0.0% | 0.0% |
| [`d2-maior-resto`](./d2-maior-resto.tcf) | 2 | maior-resto | 5053 | True | 0.0% | 0.0% |
| [`d1-ingenuo`](./d1-ingenuo.tcf) | 1 | ingenuo | 4090 | False | 66.6667% | 0.250236% |
| [`d1-maior-resto`](./d1-maior-resto.tcf) | 1 | maior-resto | 4156 | True | 66.6667% | 0.166065% |
| [`d0-ingenuo`](./d0-ingenuo.tcf) | 0 | ingenuo | 2710 | False | 100.0% | 2.46778% |
| [`d0-maior-resto`](./d0-maior-resto.tcf) | 0 | maior-resto | 2710 | True | 100.0% | 2.052571% |

Cancelamento catastrófico em `margem-d*.derivada.json`.
