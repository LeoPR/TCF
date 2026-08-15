# INDEX — date: o processo de compressão

Cada `<regime>.<transformacao>.tcf` é o wire daquele candidato **isolado**.
`<regime>.spec-welded.tcf` é o que o TCF emite hoje.

| regime | n | k | hoje | min(todos) | vencedor | ganho |
|---|---|---|---|---|---|---|
| [`diaria`](./diaria.spec-welded.tcf) | 600 | 600 | 26 | 22 | **ordinal** | 15.4% |
| [`semanal`](./semanal.spec-welded.tcf) | 600 | 600 | 26 | 22 | **ordinal** | 15.4% |
| [`quinzenal`](./quinzenal.spec-welded.tcf) | 600 | 600 | 27 | 23 | **ordinal** | 14.8% |
| [`mensal-dia1`](./mensal-dia1.spec-welded.tcf) | 600 | 600 | 673 | 337 | **delta** | 49.9% |
| [`mensal-faltas`](./mensal-faltas.spec-welded.tcf) | 600 | 600 | 2186 | 453 | **delta** | 79.3% |
| [`uteis`](./uteis.spec-welded.tcf) | 600 | 600 | 34 | 30 | **ordinal** | 11.8% |
| [`uteis-feriado`](./uteis-feriado.spec-welded.tcf) | 600 | 600 | 323 | 292 | **ordinal-rel** | 9.6% |
| [`trimestral`](./trimestral.spec-welded.tcf) | 600 | 600 | 133 | 129 | **ordinal** | 3.0% |
| [`descendente`](./descendente.spec-welded.tcf) | 600 | 600 | 26 | 22 | **ordinal** | 15.4% |
| [`agrupada`](./agrupada.spec-welded.tcf) | 600 | 30 | 64 | 41 | **componentes** | 35.9% |
| [`ciclica`](./ciclica.spec-welded.tcf) | 600 | 84 | 1350 | 351 | **delta** | 74.0% |
| [`esparsa-ordenada`](./esparsa-ordenada.spec-welded.tcf) | 600 | 600 | 4156 | 605 | **delta2** | 85.4% |
| [`esparsa-desordenada`](./esparsa-desordenada.spec-welded.tcf) | 600 | 600 | 4770 | 2434 | **componentes** | 49.0% |
| [`suja`](./suja.spec-welded.tcf) | 600 | 600 | 26 | 22 | **ordinal** | 15.4% |
