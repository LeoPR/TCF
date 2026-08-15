# INDEX — datetime: grafias × regimes × mecanismos

Cada `<caso>.<mecanismo>.tcf` é o wire daquele candidato **isolado** — o `encode()`
público só mostraria o vencedor.

## Bloco 1 — grafias (regime fixo)

| caso | grafia | k | raw | core | split | multi | vencedor |
|---|---|---|---|---|---|---|---|
| [`b1-g01-sql-espaco`](./b1-g01-sql-espaco.core.tcf) | `YYYY-MM-DD HH:MM:SS` — SQLite/MySQL; **a do | 80 | 39999 | 1229 | 842 | 852 | **campos-6** |
| [`b1-g02-iso-t`](./b1-g02-iso-t.core.tcf) | `...T...` — ISO 8601 / JSON / .NET | 80 | 39999 | 1229 | 842 | 852 | **campos-6** |
| [`b1-g03-rfc3339-z`](./b1-g03-rfc3339-z.core.tcf) | com `Z` — RFC 3339 UTC | 80 | 41999 | 1230 | 843 | 853 | **split** |
| [`b1-g04-rfc3339-offset`](./b1-g04-rfc3339-offset.core.tcf) | com `-03:00` — offset explícito | 80 | 51999 | 1235 | 878 | 888 | **split** |
| [`b1-g05-pg-microssegundo`](./b1-g05-pg-microssegundo.core.tcf) | `.ffffff` — PostgreSQL timestamp | 80 | 53999 | 1236 | 864 | 874 | **split** |
| [`b1-g06-sqlserver-milli`](./b1-g06-sqlserver-milli.core.tcf) | `.fff` — SQL Server datetime2(3) / Java | 80 | 47999 | 1233 | 861 | 871 | **split** |
| [`b1-g07-sem-segundo`](./b1-g07-sem-segundo.core.tcf) | `HH:MM` — formulário, sem segundo | 80 | 33999 | 961 | 822 | 832 | **campos-6** |
| [`b1-g08-compacta`](./b1-g08-compacta.core.tcf) | `YYYYMMDDHHMMSS` — mainframe, sem separador | 80 | 29999 | 1077 | None | 1104 | **campos-6** |
| [`b1-g09-iso-basica`](./b1-g09-iso-basica.core.tcf) | `YYYYMMDDTHHMMSS` — ISO forma básica | 80 | 31999 | 1079 | 974 | 984 | **campos-6** |
| [`b1-g10-br`](./b1-g10-br.core.tcf) | `DD/MM/YYYY HH:MM:SS` — pt-BR | 80 | 39999 | 1207 | 842 | 852 | **campos-6** |
| [`b1-g11-us-ampm`](./b1-g11-us-ampm.core.tcf) | `MM/DD/YYYY hh:mm:ss AM/PM` — US 12h | 80 | 45999 | 1392 | None | 1458 | **core** |
| [`b1-g12-epoch-s`](./b1-g12-epoch-s.core.tcf) | epoch em segundos — Unix | 80 | 21999 | 981 | None | 993 | **core** |
| [`b1-g13-epoch-ms`](./b1-g13-epoch-ms.core.tcf) | epoch em milissegundos — Java/JS | 80 | 27999 | 1025 | None | 1027 | **core** |

## Bloco 2 — regimes (grafia fixa)

| caso | regime | k | raw | core | split | multi | vencedor |
|---|---|---|---|---|---|---|---|
| [`b2-r1-comercial`](./b2-r1-comercial.core.tcf) | transacional: 08–18h, sem sábado, segundo `0 | 80 | 39999 | 1229 | 842 | 852 | **campos-6** |
| [`b2-r2-log-alta-card`](./b2-r2-log-alta-card.core.tcf) | log: todo instante distinto, com microssegun | 2000 | 39999 | 18185 | 3519 | 3529 | **campos-6** |
| [`b2-r3-batimento-5min`](./b2-r3-batimento-5min.core.tcf) | telemetria regular: exatamente 5 em 5 minuto | 2000 | 39999 | 19786 | 3275 | 3285 | **epoch-s** |
| [`b2-r4-batimento-1s`](./b2-r4-batimento-1s.core.tcf) | telemetria de alta taxa: 1/s | 2000 | 39999 | 590 | 2136 | 631 | **separado** |
| [`b2-r5-esparso-multi-ano`](./b2-r5-esparso-multi-ano.core.tcf) | eventos raros por 5 anos — muitas datas dist | 2000 | 39999 | 43957 | 9261 | 9271 | **campos-6** |
| [`b2-r6-um-dia-so`](./b2-r6-um-dia-so.core.tcf) | a data é CONSTANTE, só a hora varia | 1763 | 39999 | 23981 | 6683 | 6693 | **campos-6** |
| [`b2-r7-constante`](./b2-r7-constante.core.tcf) | todos iguais — o degenerado | 1 | 39999 | 35 | None | 41 | **epoch-s** |
| [`b2-r8-comercial-embaralhado`](./b2-r8-comercial-embaralhado.core.tcf) | **CONTRA-PROVA do r1**: os mesmos instantes, | 80 | 39999 | 3207 | 6331 | 2874 | **dict** |
