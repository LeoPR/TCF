# perf-baseline — snapshot de performance do #TCF.8 (first-order)

Referência de performance do `.8` pra comparar com o `.9`. **Não** é medida de
precisão — é um protótipo não-lapidado; o objetivo é **ordem de grandeza +
pontos quentes**, não ±2%. Extremos/cross-tech/precisão estatística → `.9`/`1.0`.

Produzido por `scripts/bench_perf/` (plano `nucleo`). Metodologia de medição:
Georges, Buytaert & Eeckhout, *Statistically Rigorous Java Performance Evaluation*
(OOPSLA 2007) — múltiplas invocações → reportar variação, não número solto — e
Kalibera & Jones, *Rigorous Benchmarking in Reasonable Time* (ISMM 2013).

Estudo/leitura completa:
[`../../../lab/dirty/notas/2026-07/2026-07-22-2207-baseline-perf-08-first-order.md`](../../../lab/dirty/notas/2026-07/2026-07-22-2207-baseline-perf-08-first-order.md).

## Arquivos

| arquivo | o que é |
|---|---|
| `perf-nucleo-2026-07-22.jsonl` | snapshot: 106 células do plano `nucleo` (103 ok, 3 opcionais pendentes). 1 registro/linha. |
| `perf-nucleo-2026-07-22.run.json` | manifesto (git, cython, plataforma) + calibradores C1/C2/C3 + drift da run. |
| `reproducibilidade-piloto.txt` | 7 invocações do bloco B1 (9 caminhos) → CV entre-runs mediano 3% (máx 5%). Prova a máquina como instrumento. |
| `first-order-report.txt` | ordem de grandeza + pontos quentes + escala. |
| `pilot_stats.py` | agrega K runs → CV + CI-95% t-Student por célula. |
| `baseline_report.py` | grandeza + hot-spots + slope log-log (encode vs linhas). |

## Como comparar com o `.9`

```
python -m bench_perf.runner --plan nucleo --out <run-09>.jsonl   # na máquina do .9
python -m bench_perf.compare perf-nucleo-2026-07-22.jsonl <run-09>.jsonl
```
`compare.py` normaliza pela razão dos calibradores (máquina) antes de comparar, e
classifica cada delta como RUÍDO vs real pelo maior entre MDE-do-tier e o piso de
ruído — coerente com o ±~5% run-a-run medido aqui.

## Achado que ancora o `.9`

- **Row-scaling (encode vs nº de linhas) já é LINEAR O(n)** (slope ~1.0) pra
  tcf-flat, json-ref e tcf-8h aninhado. Não há dívida de crescimento por linhas.
- **O penhasco é o canto R×C extremo**: `cantoRC-both` = 44.6s vs base(10k) 595ms
  = **~75×**. É a degeneração do índice de trigramas do OBAT (muitos prefixos
  parecidos → O(n²/B)). Alvo do `.9` (ex.: escada de prefixo adaptativa).
