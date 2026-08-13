# INDEX — o que cada arquivo e'

| caso | ideia | input | wire | bytes (core) | quem venceu | RT |
|---|---|---|---|---:|---|:--:|
| `a1-diaria-600` | passo constante +1: o ordinal colapsa no seq-RLE aritmetico `*N+1|ancora` | [entrada](../inputs/a1-diaria-600.entrada.json) | [.tcf](./a1-diaria-600.tcf) | 26 (414) | spec `:dt` | ok |
| `a2-mensal-600` | passo constante +30: pro seq-RLE da' o MESMO trabalho que +1 (o passo nao importa) | [entrada](../inputs/a2-mensal-600.entrada.json) | [.tcf](./a2-mensal-600.tcf) | 27 (6338) | spec `:dt` | ok |
| `a3-uteis-600` | dias UTEIS: delta cicla 1,1,1,1,3 -> so' o marcador PERIODICO pega (ADR-0040) | [entrada](../inputs/a3-uteis-600.entrada.json) | [.tcf](./a3-uteis-600.tcf) | 34 (2454) | spec `:dt` | ok |
| `a4-quinzenal-400` | quinzenal: outro passo constante, p/ ver que a grafia nao muda | [entrada](../inputs/a4-quinzenal-400.entrada.json) | [.tcf](./a4-quinzenal-400.tcf) | 27 (4265) | spec `:dt` | ok |
| `a5-primeiro-do-mes-240` | dia 1 de cada mes: passo IRREGULAR (31,28,31,30…) — o LIMITE dos dois marcadores | [entrada](../inputs/a5-primeiro-do-mes-240.entrada.json) | [.tcf](./a5-primeiro-do-mes-240.tcf) | 323 (455) | spec `:dt` | ok |
| `b1-diaria-n10` | N=10: a nature PERDE o FLOOR -> o encoder emite o CORE (sem `:dt`) | [entrada](../inputs/b1-diaria-n10.entrada.json) | [.tcf](./b1-diaria-n10.tcf) | 42 (42) | core | ok |
| `b2-diaria-n11` | N=11: a nature VENCE — o flip que o id curto comprou (com `:data-iso` perdia) | [entrada](../inputs/b2-diaria-n11.entrada.json) | [.tcf](./b2-diaria-n11.tcf) | 43 (47) | spec `:dt` | ok |
| `b3-diaria-n12` | N=12: ja' consolidado do lado da nature | [entrada](../inputs/b3-diaria-n12.entrada.json) | [.tcf](./b3-diaria-n12.tcf) | 43 (47) | spec `:dt` | ok |
| `c1-agrupada-400` | datas repetidas em blocos: o RLE do nucleo ja' resolve -> o FLOOR RECUSA a nature | [entrada](../inputs/c1-agrupada-400.entrada.json) | [.tcf](./c1-agrupada-400.tcf) | 64 (64) | core | ok |
| `c2-aleatoria-300` | sem estrutura temporal: nao ha' progressao p/ o seq-RLE morder | [entrada](../inputs/c2-aleatoria-300.entrada.json) | [.tcf](./c2-aleatoria-300.tcf) | 2292 (2767) | spec `:dt` | ok |
| `c3-suja-30pct-300` | 30% de grafias nao-canonicas: cada uma vira LITERAL (`_`), RT byte-exato | [entrada](../inputs/c3-suja-30pct-300.entrada.json) | [.tcf](./c3-suja-30pct-300.tcf) | 1309 (1486) | spec `:dt` | ok |
| `c4-com-nulos-300` | slots NULOS no meio da progressao (o None do core, nao string vazia) | [entrada](../inputs/c4-com-nulos-300.entrada.json) | [.tcf](./c4-com-nulos-300.tcf) | 461 (571) | spec `:dt` | ok |
| `c5-n1` | N=1: nao ha' delta nenhum p/ observar | [entrada](../inputs/c5-n1.entrada.json) | [.tcf](./c5-n1.tcf) | 19 (20) | spec `:dt` | ok |
| `c6-descendente-300` | progressao DESCENDENTE: o passo e' -1 (o sinal viaja no marcador) | [entrada](../inputs/c6-descendente-300.entrada.json) | [.tcf](./c6-descendente-300.tcf) | 26 (1061) | spec `:dt` | ok |
| `f1-tpch-orderdate` | TPC-H orderdate como vem do banco (nao ordenado): o caso comum de coluna de data | [entrada](../inputs/f1-tpch-orderdate.entrada.json) | [.tcf](./f1-tpch-orderdate.tcf) | 19871 (22961) | spec `:dt` | ok |
| `f2-tpch-orderdate-ord` | a MESMA coluna ordenada: o que a ordem sozinha muda | [entrada](../inputs/f2-tpch-orderdate-ord.entrada.json) | [.tcf](./f2-tpch-orderdate-ord.tcf) | 13515 (18641) | spec `:dt` | ok |
| `f3-tpch-shipdate` | TPC-H shipdate | [entrada](../inputs/f3-tpch-shipdate.entrada.json) | [.tcf](./f3-tpch-shipdate.tcf) | 19230 (23004) | spec `:dt` | ok |
| `f4-tpch-commitdate` | TPC-H commitdate | [entrada](../inputs/f4-tpch-commitdate.entrada.json) | [.tcf](./f4-tpch-commitdate.tcf) | 18935 (22446) | spec `:dt` | ok |
| `f5-tpch-receiptdate` | TPC-H receiptdate | [entrada](../inputs/f5-tpch-receiptdate.entrada.json) | [.tcf](./f5-tpch-receiptdate.tcf) | 19117 (22876) | spec `:dt` | ok |
| `f6-tpch-sf01-orderdate` | TPC-H sf01 (escala maior) | [entrada](../inputs/f6-tpch-sf01-orderdate.entrada.json) | [.tcf](./f6-tpch-sf01-orderdate.tcf) | 19833 (22820) | spec `:dt` | ok |
| `f7-br-cadastro` | br-identidades: data de cadastro | [entrada](../inputs/f7-br-cadastro.entrada.json) | [.tcf](./f7-br-cadastro.tcf) | 21360 (28771) | spec `:dt` | ok |
| `f8-br-abertura` | br-identidades: data de abertura | [entrada](../inputs/f8-br-abertura.entrada.json) | [.tcf](./f8-br-abertura.tcf) | 21901 (31038) | spec `:dt` | ok |
| `f9-receita-inicio` | Receita: data de inicio de atividade (CNPJ real) | [entrada](../inputs/f9-receita-inicio.entrada.json) | [.tcf](./f9-receita-inicio.tcf) | 4145 (4145) | core | ok |
| `f10-retail-invoicedate` | retail: data de fatura (muitas repeticoes por dia) | [entrada](../inputs/f10-retail-invoicedate.entrada.json) | [.tcf](./f10-retail-invoicedate.tcf) | 1666 (1666) | core | ok |
| `f11-football-date` | football: data de partida | [entrada](../inputs/f11-football-date.entrada.json) | [.tcf](./f11-football-date.tcf) | 16235 (33380) | spec `:dt` | ok |
| `f12-receita-inicio-ord` | Receita ordenada: onde a progressao aparece | [entrada](../inputs/f12-receita-inicio-ord.entrada.json) | [.tcf](./f12-receita-inicio-ord.tcf) | 850 (850) | core | ok |
| `d1-multicol` | data em multi-col + o view lazy respondendo por VALOR | [entrada](../inputs/d1-multicol.entrada.json) | [.tcf](./d1-multicol.tcf) | 875 | estrutura | ok |
| `d2-hierarquico` | data como folha de dataset (.8H) | [entrada](../inputs/d2-hierarquico.entrada.json) | [.tcf](./d2-hierarquico.tcf) | 76 | estrutura | ok |
| `e1-wire-historico` | wire gravado com `:data-iso` — falha alto e le' pela valvula | [entrada](../inputs/e1-wire-historico.entrada.json) | [.tcf](./e1-wire-historico.tcf) | 40 | migracao | ok |

A anatomia de cada wire (header e marcadores explicados) esta' em `../intermediates/<caso>.anatomia.txt`; a telemetria do encode em `<caso>.trace.txt`.

**Contra-prova**: `outputs/<c>.roundtrip.json` e `inputs/<c>.entrada.json` sao gravados com a MESMA formatacao — `diff` entre os dois tem de dar VAZIO.
