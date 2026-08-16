# INDEX — cadastro popular: o header do `.8M` com specs, pra inspeção

n=500, seed=20260815. Todos os wires com RT validado (falhas: 0).

| wire | B | linha 1 |
|---|---|---|
| [`cadastro-sem-spec.tcf`](./cadastro-sem-spec.tcf) | 25497 | `#TCF.8Mf=id,a56=nome,%1d1c=cpf,1c11=email,%15ba=telefone,%7fb=nascimento` |
| [`cadastro-com-spec.tcf`](./cadastro-com-spec.tcf) | 21047 | `#TCF.8Mf=id,a56=nome,!bb7=cpf:cpf,1c11=email,%15ba=telefone,%7fb=nascime` |
| [`cadastro-header-cheio.tcf`](./cadastro-header-cheio.tcf) | 21051 | `#TCF.8Mf=id,a56=nome,!bb7=cpf:cpf,1c11=email,%15ba=telefone,%7fb=nascime` |
| [`cadastro-sem-nomes.tcf`](./cadastro-sem-nomes.tcf) | 21004 | `#TCF.8Mf,a56,!bb7:cpf,1c11,%15ba,%7fb,@` |
| [`cadastro-flag-bool.tcf`](./cadastro-flag-bool.tcf) | 33996 | `#TCF.8H#Oid#:5[]:15,nome#:5[]:2646,cpf#:5[]:9485,email#:5[]:7185,telefon` |

## A anatomia do header COM specs (fronteiras de coluna)

| coluna | modo | nat | size hex | bytes | [ini:fim) |
|---|---|---|---|---|---|
| id | `tcf` | — | `f` | 15 | [0:15) |
| nome | `tcf` | — | `a56` | 2646 | [15:2661) |
| cpf | `raw` | cpf | `bb7` | 2999 | [2661:5660) |
| email | `tcf` | — | `1c11` | 7185 | [5660:12845) |
| telefone | `split` | — | `15ba` | 5562 | [12845:18407) |
| nascimento | `split` | — | `7fb` | 2043 | [18407:20450) |
| ativo | `dict` | — | `(EOF)` | 514 | [20450:20964) |
