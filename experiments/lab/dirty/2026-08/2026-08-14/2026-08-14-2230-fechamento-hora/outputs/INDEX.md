# INDEX — fechamento da HORA

| caso | ideia | bytes | disc | RT |
|---|---|---|---|---|
| [`regime-batimento-15min`](./regime-batimento-15min.tcf) | telemetria: 1 dia inteiro a cada 15 min (96 pontos). O regime onde | 751 | `(vazio — string default)` | True |
| [`regime-batimento-15min-2dias`](./regime-batimento-15min-2dias.tcf) | CONTRA-PROVA: o MESMO batimento por 2 dias — passa pela meia-noite | 980 | `B7c0` | True |
| [`regime-batimento-1min`](./regime-batimento-1min.tcf) | batimento de 1 min, 600 pontos (10 h) — não passa da meia-noite. | 199 | `!!` | True |
| [`regime-batimento-1s`](./regime-batimento-1s.tcf) | batimento de 1 s — o caso mais regular possível. | 215 | `!!` | True |
| [`regime-expediente`](./regime-expediente.tcf) | 200 horários espalhados em 08:00–18:00 — irregular mas com faixa e | 1807 | `!!` | True |
| [`regime-constante`](./regime-constante.tcf) | tudo meia-noite. É o regime do `InvoiceDate` quando a hora não é u | 23 | `!` | True |
| [`regime-so-hora-e-minuto`](./regime-so-hora-e-minuto.tcf) | a MESMA sequência em `HH:MM` — a grafia mais curta. Contra-prova d | 831 | `(vazio — string default)` | True |
| [`borda-meia-noite`](./borda-meia-noite.tcf) | os extremos do dia | 33 | `!` | True |
| [`borda-24h`](./borda-24h.tcf) | `24:00:00` é VÁLIDO em ISO 8601 (fim do dia) e o Python RECUSA — g | 27 | `!!` | True |
| [`borda-leap-second`](./borda-leap-second.tcf) | segundo bissexto: existe em UTC, não existe em `datetime.time` | 24 | `!` | True |
| [`borda-fracao`](./borda-fracao.tcf) | frações: `.5` e `.500000` são o MESMO instante com grafias distint | 40 | `!` | True |
| [`borda-hhmm-x-hhmmss`](./borda-hhmm-x-hhmmss.tcf) | duas grafias do mesmo instante — se um spec normalizasse, o RT que | 22 | `(vazio — string default)` | True |
| [`borda-12h`](./borda-12h.tcf) | 12h com sufixo — grafia comum em relatório, não é ISO | 24 | `!!` | True |
| [`borda-compacta`](./borda-compacta.tcf) | `HHMMSS` sem separador (forma básica da ISO) — indistinguível de u | 23 | `(vazio — string default)` | True |
| [`borda-com-nulo`](./borda-com-nulo.tcf) | o slot nulo atravessa | 28 | `(vazio — string default)` | True |
| [`borda-timezone`](./borda-timezone.tcf) | com offset — e o `-00:00` tem semântica própria na RFC 3339 | 39 | `!` | True |
| [`real-retail-hora`](./real-retail-hora.tcf) | a parte de hora do `online-retail.InvoiceDate` | 10619 | `(vazio — string default)` | True |

Ciclicidade em `ciclicidade-*dias.{ciclico,absoluto}.tcf`;
ordinal em `ordinal-*dias.tcf`.
