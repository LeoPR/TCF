# INDEX — view x colunas tipadas

| forma | rota | view abre? | bytes |
|---|---|---|---|
| single string (bN/OBAT) | single '\n' | **nao** | 1133 |
| single + spec `:dt` | single ' ' | **nao** | 1547 |
| tipado n (int) | single 'n' | **nao** | 1384 |
| tipado n (float) | single 'n' | **nao** | 50 |
| tipado b (bool) | single 'b' | **nao** | 47 |
| tipado n denso (nB) | single 'n' | **nao** | 55 |
| stamp / vazio | single '\n' | **nao** | 7 |
| MULTI .8M (todo string) | multi .8M | sim | 2022 |
| MULTI .8M + spec | multi .8M | sim | 2022 |
| HIER .8H | hier .8H | **nao** | 3155 |
