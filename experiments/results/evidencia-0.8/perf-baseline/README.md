# perf-baseline — snapshot de performance do #TCF.8 (first-order)

Referência de performance do `.8` pra comparar com o `.9`. **Não** é medida de
precisão — é um protótipo não-lapidado; o objetivo é **ordem de grandeza +
pontos quentes**, não ±2%. Extremos/cross-tech/precisão estatística → `.9`/`1.0`.

Produzido por `scripts/bench_perf/` (plano `nucleo`). Metodologia de medição:
Georges, Buytaert & Eeckhout, *Statistically Rigorous Java Performance Evaluation*
(OOPSLA 2007) — múltiplas invocações → reportar variação, não número solto — e
Kalibera & Jones, *Rigorous Benchmarking in Reasonable Time* (ISMM 2013).

## Adjudicação (leia antes de olhar o run.json)

**Veredito: `accepted-first-order`** (owner, 2026-07-22). Critério: a análise ENTRE-runs
(piloto B1×7, CV mediano 3%, máx 5% — `reproducibilidade-piloto.txt`) confirma a máquina como
instrumento pro propósito declarado (ordem de grandeza + pontos quentes).

> O `run.json` tem `status: termicamente-reprovado` — esse é o **`runner_thermal_status`**, um
> gate binário **intra-run** que se mostrou inadequado pra esta pergunta e foi **REFUTADO**. Ele
> fica preservado como proveniência do gate antigo; **não** é o status metodológico final. O
> comparador (`bench_perf.compare`) ainda interpreta só esse campo — corrigi-lo p/ consumir a
> adjudicação vigente é higiene pendente (bench_perf, não core; ver parecer 2340 §1).

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
