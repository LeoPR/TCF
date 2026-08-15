# INDEX — `agg=soma` e streaming

**Aviso**: os `.tcf` que não são `.baseline` contêm valores **ajustados de propósito**.
O `roundtrip.json` prova que o formato os preserva — não que são os originais.

| caso | forma | bytes | soma exata | lidos p/ 1º | prefixo decode |
|---|---|---|---|---|---|
| [`rateio`](./rateio.maior-resto.tcf) | maior-resto | 35 | True | 10 | 19 B |
| [`rateio`](./rateio.difusao-erro.tcf) | difusao-erro | 47 | True | 1 | 21 B |
| [`rateio`](./rateio.ancora.tcf) | ancora | 29 | False | 1 | 19 B |
| [`retail-d1`](./retail-d1.maior-resto.tcf) | maior-resto | 3028 | True | 2000 | 19 B |
| [`retail-d1`](./retail-d1.difusao-erro.tcf) | difusao-erro | 3090 | True | 1 | 19 B |
| [`retail-d1`](./retail-d1.ancora.tcf) | ancora | 2955 | False | 1 | 19 B |
| [`retail-d0`](./retail-d0.maior-resto.tcf) | maior-resto | 1900 | True | 2000 | 19 B |
| [`retail-d0`](./retail-d0.difusao-erro.tcf) | difusao-erro | 2240 | True | 1 | 19 B |
| [`retail-d0`](./retail-d0.ancora.tcf) | ancora | 1900 | False | 1 | 19 B |
