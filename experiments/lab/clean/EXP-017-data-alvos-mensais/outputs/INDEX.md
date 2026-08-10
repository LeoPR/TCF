# Índice de inspeção — EXP-017

**Gerado por `run.py`.** Uma linha por artefato: o que ele é, o que o gerou, e onde está
a prova. Cada `.tcf` desta pasta tem aqui a sua origem completa.

## Como conferir um caso, sem ler código

```
1. o que entrou:            inputs/<caso>.entrada.json
2. como se decidiu:         intermediates/<caso>.candidatos.json   (todos os candidatos,
                                  bytes, e o que ficou CONSTANTE na comparação)
3. o payload de cada alvo:  intermediates/<caso>.payloads.json
4. o wire emitido:          outputs/<caso>.tcf
5. a CONTRA-PROVA:          diff inputs/<caso>.entrada.json outputs/<caso>.roundtrip.json
                                  -> tem de sair VAZIO
```

O `run.py` já faz esse `diff` como assert (prova 3) e **falha** se divergir.

### sintetico-mensal

| wire | a ideia do caso | entrada | candidato vencedor | contra-prova | pin |
|---|---|---|---|---|---|
| [`sint-mensal-dia1.tcf`](sint-mensal-dia1.tcf) | o regime canônico do alvo mensal: dia constante, delta 28-31 no eixo do dia | [`sint-mensal-dia1.entrada.json`](../inputs/sint-mensal-dia1.entrada.json) (n=600, k=600) | `mes31dia` · 33 B | [`.roundtrip.json`](sint-mensal-dia1.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`sint-mensal-dia15.tcf`](sint-mensal-dia15.tcf) | dia constante != 1: só o A4 (sem convenção) cobre | [`sint-mensal-dia15.entrada.json`](../inputs/sint-mensal-dia15.entrada.json) (n=600, k=600) | `mes31dia` · 33 B | [`.roundtrip.json`](sint-mensal-dia15.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`sint-mensal-fim.tcf`](sint-mensal-fim.tcf) | fecho contábil: o dia VARIA e é dedutível — o único caso do A2f | [`sint-mensal-fim.entrada.json`](../inputs/sint-mensal-fim.entrada.json) (n=600, k=600) | `fimdemes` · 35 B | [`.roundtrip.json`](sint-mensal-fim.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`sint-mensal-faltas.tcf`](sint-mensal-faltas.tcf) | competência sem fato: mês pulado. No eixo do dia o spec recusa a coluna | [`sint-mensal-faltas.entrada.json`](../inputs/sint-mensal-faltas.entrada.json) (n=600, k=600) | `mes31dia` · 48 B | [`.roundtrip.json`](sint-mensal-faltas.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`sint-trimestral.tcf`](sint-trimestral.tcf) | passo de 3 meses: delta uniforme no eixo do mês | [`sint-trimestral.entrada.json`](../inputs/sint-trimestral.entrada.json) (n=400, k=400) | `mes31dia` · 33 B | [`.roundtrip.json`](sint-trimestral.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`sint-ano-mes.tcf`](sint-ano-mes.tcf) | grafia YYYY-MM pura: o spec ISO recusa (não é data completa) | [`sint-ano-mes.entrada.json`](../inputs/sint-ano-mes.entrada.json) (n=600, k=600) | `anomes` · 30 B | [`.roundtrip.json`](sint-ano-mes.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`sint-misto-d01-d15.tcf`](sint-misto-d01-d15.tcf) | dois dias alternando: vira período 2 no eixo do mês | [`sint-misto-d01-d15.entrada.json`](../inputs/sint-misto-d01-d15.entrada.json) (n=600, k=600) | `mes31dia` · 36 B | [`.roundtrip.json`](sint-misto-d01-d15.roundtrip.json) ✓ | ✓ (`mensal`) |
### controle

| wire | a ideia do caso | entrada | candidato vencedor | contra-prova | pin |
|---|---|---|---|---|---|
| [`ctrl-diario.tcf`](ctrl-diario.tcf) | o ordinal-dia é ótimo aqui; se o mensal ganhar, algo está errado | [`ctrl-diario.entrada.json`](../inputs/ctrl-diario.entrada.json) (n=600, k=600) | `ordinal-soldado` · 32 B | [`.roundtrip.json`](ctrl-diario.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`ctrl-uteis.tcf`](ctrl-uteis.tcf) | cadência de dias úteis: território do periódico no eixo do DIA | [`ctrl-uteis.entrada.json`](../inputs/ctrl-uteis.entrada.json) (n=600, k=600) | `ordinal-soldado` · 40 B | [`.roundtrip.json`](ctrl-uteis.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`ctrl-espalhado.tcf`](ctrl-espalhado.tcf) | passo irregular de 1-40 dias: nenhum eixo uniformiza | [`ctrl-espalhado.entrada.json`](../inputs/ctrl-espalhado.entrada.json) (n=600, k=600) | `ordinal-rota-plena` · 3770 B | [`.roundtrip.json`](ctrl-espalhado.roundtrip.json) ✓ | ✓ (`ordinal`) |
### valvula

| wire | a ideia do caso | entrada | candidato vencedor | contra-prova | pin |
|---|---|---|---|---|---|
| [`valv-mensal-sujo-5pct.tcf`](valv-mensal-sujo-5pct.tcf) | 5% de 's/d': a válvula segura. ATENÇÃO (caçada adversarial): o resultado é BIMODAL por semente — em 12 sementes o core vence 8; esta semente é do lado favorável. O pin fixa ESTA semente; a bimodalidade é o T-PENHASCO-INICIO | [`valv-mensal-sujo-5pct.entrada.json`](../inputs/valv-mensal-sujo-5pct.entrada.json) (n=600, k=572) | `mes31dia` · 511 B | [`.roundtrip.json`](valv-mensal-sujo-5pct.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`valv-sujeira-no-inicio.tcf`](valv-sujeira-no-inicio.tcf) | UMA sujeira no índice 3 (<20): o penhasco do pre-pass (analyze_column sample_size=20 + Regra 2 do auto_cadence) — 95x decidido pela POSIÇÃO da primeira exceção; atinge o ordinal soldado igual | [`valv-sujeira-no-inicio.entrada.json`](../inputs/valv-sujeira-no-inicio.entrada.json) (n=600, k=600) | `anomes` · 3820 B | [`.roundtrip.json`](valv-sujeira-no-inicio.roundtrip.json) ✓ | ✓ (`qualquer`) |
| [`valv-ym-unicode.tcf`](valv-ym-unicode.tcf) | dígitos Unicode (fullwidth/árabe): `isdigit()`/`int()` os ACEITAM — sem o guard de re-emissão o payload colapsava grafias distintas (caçada adversarial, 4ª ocorrência da classe). Com o guard: viram literal e o RT fecha | [`valv-ym-unicode.entrada.json`](../inputs/valv-ym-unicode.entrada.json) (n=600, k=599) | `anomes` · 70 B | [`.roundtrip.json`](valv-ym-unicode.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`valv-mensal-null.tcf`](valv-mensal-null.tcf) | None no meio: passa pelo slot 0, fora do alvo | [`valv-mensal-null.entrada.json`](../inputs/valv-mensal-null.entrada.json) (n=600, k=596) | `mes31dia` · 86 B | [`.roundtrip.json`](valv-mensal-null.roundtrip.json) ✓ | ✓ (`mensal`) |
### real-tpch

| wire | a ideia do caso | entrada | candidato vencedor | contra-prova | pin |
|---|---|---|---|---|---|
| [`real-tpch-orderdate-nat.tcf`](real-tpch-orderdate-nat.tcf) | TPC-H orders na ordem de armazenamento: data comercial, k alto | [`real-tpch-orderdate-nat.entrada.json`](../inputs/real-tpch-orderdate-nat.entrada.json) (n=3000, k=1738) | `ordinal-rota-plena` · 18817 B | [`.roundtrip.json`](real-tpch-orderdate-nat.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`real-tpch-orderdate-ord.tcf`](real-tpch-orderdate-ord.tcf) | a MESMA coluna ordenada: isola o efeito da ordem | [`real-tpch-orderdate-ord.entrada.json`](../inputs/real-tpch-orderdate-ord.entrada.json) (n=3000, k=1738) | `mes31dia` · 12579 B | [`.roundtrip.json`](real-tpch-orderdate-ord.roundtrip.json) ✓ | ✓ (`mensal`) |
| [`real-tpch-shipdate-nat.tcf`](real-tpch-shipdate-nat.tcf) | lineitem embarque: a coluna de data mais medida do projeto | [`real-tpch-shipdate-nat.entrada.json`](../inputs/real-tpch-shipdate-nat.entrada.json) (n=3000, k=1762) | `ordinal-rota-plena` · 18140 B | [`.roundtrip.json`](real-tpch-shipdate-nat.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`real-tpch-shipdate-ord.tcf`](real-tpch-shipdate-ord.tcf) | idem ordenada | [`real-tpch-shipdate-ord.entrada.json`](../inputs/real-tpch-shipdate-ord.entrada.json) (n=3000, k=1762) | `ordinal-rota-plena` · 12583 B | [`.roundtrip.json`](real-tpch-shipdate-ord.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`real-tpch-commitdate-ord.tcf`](real-tpch-commitdate-ord.tcf) | coluna irmã (H7 da triagem morreu, mas a coluna sozinha vale medir) | [`real-tpch-commitdate-ord.entrada.json`](../inputs/real-tpch-commitdate-ord.entrada.json) (n=3000, k=1668) | `ordinal-rota-plena` · 12371 B | [`.roundtrip.json`](real-tpch-commitdate-ord.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`real-tpch-receiptdate-ord.tcf`](real-tpch-receiptdate-ord.tcf) | terceira irmã | [`real-tpch-receiptdate-ord.entrada.json`](../inputs/real-tpch-receiptdate-ord.entrada.json) (n=3000, k=1725) | `ordinal-rota-plena` · 12618 B | [`.roundtrip.json`](real-tpch-receiptdate-ord.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`real-tpch-sf01-orderdate-ord.tcf`](real-tpch-sf01-orderdate-ord.tcf) | amostra DISTINTA da mesma fonte (OFFSET 90000 — a cacada pegou que LIMIT puro duplicava o sf001 byte a byte: dbgen deterministico). O A4 vence por 14 B em 12.612 (0,1%): acidente estrutural do payload, NAO regime mensal — a coluna tem 31 dias-do-mes uniformes | [`real-tpch-sf01-orderdate-ord.entrada.json`](../inputs/real-tpch-sf01-orderdate-ord.entrada.json) (n=3000, k=1724) | `mes31dia` · 12598 B | [`.roundtrip.json`](real-tpch-sf01-orderdate-ord.roundtrip.json) ✓ | ✓ (`mensal`) |
### real-br

| wire | a ideia do caso | entrada | candidato vencedor | contra-prova | pin |
|---|---|---|---|---|---|
| [`real-br-cadastro-nat.tcf`](real-br-cadastro-nat.tcf) | cadastro BR na ordem natural: k alto, span curto | [`real-br-cadastro-nat.entrada.json`](../inputs/real-br-cadastro-nat.entrada.json) (n=3000, k=2184) | `ordinal-rota-plena` · 20101 B | [`.roundtrip.json`](real-br-cadastro-nat.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`real-br-cadastro-ord.tcf`](real-br-cadastro-ord.tcf) | idem ordenada | [`real-br-cadastro-ord.entrada.json`](../inputs/real-br-cadastro-ord.entrada.json) (n=3000, k=2184) | `ordinal-rota-plena` · 14375 B | [`.roundtrip.json`](real-br-cadastro-ord.roundtrip.json) ✓ | ✓ (`ordinal`) |
| [`real-br-abertura-ord.tcf`](real-br-abertura-ord.tcf) | abertura de empresas: span longo | [`real-br-abertura-ord.entrada.json`](../inputs/real-br-abertura-ord.entrada.json) (n=3000, k=2366) | `ordinal-rota-plena` · 15026 B | [`.roundtrip.json`](real-br-abertura-ord.roundtrip.json) ✓ | ✓ (`ordinal`) |
### real-grafia

| wire | a ideia do caso | entrada | candidato vencedor | contra-prova | pin |
|---|---|---|---|---|---|
| [`real-receita-yyyymmdd.tcf`](real-receita-yyyymmdd.tcf) | YYYYMMDD COMPACTO: o spec ISO recusa por design (guard de re-emissão) | [`real-receita-yyyymmdd.entrada.json`](../inputs/real-receita-yyyymmdd.entrada.json) (n=3000, k=97) | `core` · 4145 B | [`.roundtrip.json`](real-receita-yyyymmdd.roundtrip.json) ✓ | ✓ (`nenhum`) |
| [`real-retail-datetime.tcf`](real-retail-datetime.tcf) | DATETIME com hora: não é date puro — a válvula tem de segurar tudo | [`real-retail-datetime.entrada.json`](../inputs/real-retail-datetime.entrada.json) (n=3000, k=117) | `core` · 1666 B | [`.roundtrip.json`](real-retail-datetime.roundtrip.json) ✓ | ✓ (`nenhum`) |
### real-span

| wire | a ideia do caso | entrada | candidato vencedor | contra-prova | pin |
|---|---|---|---|---|---|
| [`real-football.tcf`](real-football.tcf) | 1872..hoje: o maior span do corpus; ja' ordenado na origem (a variante .ordenado e' byte-identica — cacada adversarial, md5) | [`real-football.entrada.json`](../inputs/real-football.entrada.json) (n=3000, k=2297) | `ordinal-rota-plena` · 15021 B | [`.roundtrip.json`](real-football.roundtrip.json) ✓ | ✓ (`ordinal`) |

## Legenda

- **candidato vencedor** — quem ganhou o `min()`: `core` (só o núcleo), `ordinal-soldado`
  (o `SPEC_DATA_ISO` como o encoder o emite hoje), `ordinal-rota-plena` (mesmo payload
  pela rota flat inteira), ou um dos alvos-protótipo (`mes31dia`/`fimdemes`/`anomes`).
- **pin** — o que `casos.py` declarava que deveria vencer. Divergir **quebra o lab**.
- **contra-prova** — `roundtrip.json` byte-idêntico à `entrada.json`.
