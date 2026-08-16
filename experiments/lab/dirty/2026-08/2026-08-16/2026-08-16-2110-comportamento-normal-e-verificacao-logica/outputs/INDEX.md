# INDEX — comportamento normal + verificação lógica

Todo caso tem entrada, wire, roundtrip e meta; o `diff` é assert no `run.py`.

| caso | operação | bytes | RT |
|---|---|---:|:--:|
| [`01-tabela.tcf`](./01-tabela.tcf) | tabela .8M, 6 colunas | 9336 | ✓ |
| [`02-tabela-com-spec.tcf`](./02-tabela-com-spec.tcf) | a mesma, com specs | 6826 | ✓ |
| [`03-tabela-sem-nomes.tcf`](./03-tabela-sem-nomes.tcf) | a mesma, sem nomes | 9302 | ✓ |
| [`04-tabela-todos-com-size.tcf`](./04-tabela-todos-com-size.tcf) | a mesma, todos com size | 9340 | ✓ |
| [`05-uma-coluna.tcf`](./05-uma-coluna.tcf) | uma coluna só | 683 | ✓ |
| [`06-registros.tcf`](./06-registros.tcf) | registros (.8H) | 13834 | ✓ |
| [`07-datas.tcf`](./07-datas.tcf) | coluna única de datas | 1432 | ✓ |
