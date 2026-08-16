# INDEX — agrupar tipos comuns no `.8M`

n=2000, seed=20260816. **Todo caso tem entrada, wire, roundtrip e meta**; o `diff` entrada×roundtrip é rodado como assert pelo `run.py`.

| caso | ideia | wire | RT | entrada |
|---|---|---:|:--:|---|
| [`b4-disjunto-k50.tcf`](./b4-disjunto-k50.tcf) | contra-prova do Bloco 4: sobreposicao de dominio | 4550 | ✓ | [entrada](../inputs/b4-disjunto-k50.entrada.json) · [roundtrip](./b4-disjunto-k50.roundtrip.json) |
| [`b4-disjunto-k500.tcf`](./b4-disjunto-k500.tcf) | contra-prova do Bloco 4: sobreposicao de dominio | 13959 | ✓ | [entrada](../inputs/b4-disjunto-k500.entrada.json) · [roundtrip](./b4-disjunto-k500.roundtrip.json) |
| [`b4-same-k50.tcf`](./b4-same-k50.tcf) | contra-prova do Bloco 4: sobreposicao de dominio | 4547 | ✓ | [entrada](../inputs/b4-same-k50.entrada.json) · [roundtrip](./b4-same-k50.roundtrip.json) |
| [`b4-same-k500.tcf`](./b4-same-k500.tcf) | contra-prova do Bloco 4: sobreposicao de dominio | 13940 | ✓ | [entrada](../inputs/b4-same-k500.entrada.json) · [roundtrip](./b4-same-k500.roundtrip.json) |
| [`cadastro-com-flags.tcf`](./cadastro-com-flags.tcf) | a tabela do Bloco 1 e do Bloco 3 | 16200 | ✓ | [entrada](../inputs/cadastro-com-flags.entrada.json) · [roundtrip](./cadastro-com-flags.roundtrip.json) |
| [`same-domain-k2.tcf`](./same-domain-k2.tcf) | a curva do Bloco 2 — k e a UNICA variavel | 4074 | ✓ | [entrada](../inputs/same-domain-k2.entrada.json) · [roundtrip](./same-domain-k2.roundtrip.json) |
| [`same-domain-k2000.tcf`](./same-domain-k2000.tcf) | a curva do Bloco 2 — k e a UNICA variavel | 27960 | ✓ | [entrada](../inputs/same-domain-k2000.entrada.json) · [roundtrip](./same-domain-k2000.roundtrip.json) |
| [`same-domain-k50.tcf`](./same-domain-k50.tcf) | a curva do Bloco 2 — k e a UNICA variavel | 4558 | ✓ | [entrada](../inputs/same-domain-k50.entrada.json) · [roundtrip](./same-domain-k50.roundtrip.json) |
| [`same-domain-k500.tcf`](./same-domain-k500.tcf) | a curva do Bloco 2 — k e a UNICA variavel | 13957 | ✓ | [entrada](../inputs/same-domain-k500.entrada.json) · [roundtrip](./same-domain-k500.roundtrip.json) |
| [`same-domain-k6.tcf`](./same-domain-k6.tcf) | a curva do Bloco 2 — k e a UNICA variavel | 4106 | ✓ | [entrada](../inputs/same-domain-k6.entrada.json) · [roundtrip](./same-domain-k6.roundtrip.json) |
