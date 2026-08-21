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

### Rodada PROBATÓRIA — 2026-08-20 (`6f04f3ae`)

A que faltava desde 22/07: `--probative` (fail-closed), árvore limpa, Cython presente.
`status=completo`, 103/106 comparáveis, **0 obrigatório-falhou**, 0 envelope. Térmico:
`termicamente-suspeito` (aviso, não bloqueia — vale a adjudicação acima).

> **⚠ Esta rodada é BASELINE PINADO do `.8`, e TEM DE SER REPETIDA depois das otimizações
> do `.9`** — condição do owner ao autorizá-la: *"faz sentido fazer mesmo com as otimizações
> que tem agora, elas serviriam como base para as otimizações futuras. só precisamos lembrar
> de que temos que repeti-las."* Ao repetir: rodar os calibradores de novo e normalizar
> antes de declarar qualquer ganho (mas ver a ressalva sobre o calibrador, adiante).

## Arquivos

| arquivo | o que é |
|---|---|
| `perf-nucleo-2026-07-22.jsonl` | snapshot: 106 células do plano `nucleo` (103 ok, 3 opcionais pendentes). 1 registro/linha. |
| `perf-nucleo-2026-07-22.run.json` | manifesto (git, cython, plataforma) + calibradores C1/C2/C3 + drift da run. |
| **`perf-nucleo-2026-08-20.jsonl`** | **rodada PROBATÓRIA** (`--probative`, árvore limpa, `6f04f3ae`). Mesmo perfil: 106 registros, 103 ok, 0 obrigatório-falhou. |
| **`perf-nucleo-2026-08-20.run.json`** | idem, schema `run-v3` (`status` e `runner_thermal_status` ortogonais). |
| **`first-order-report-2026-08-20.txt`** | relatório da probatória. **§3 (slope) lê errado — ver ressalva abaixo.** |
| `reproducibilidade-piloto.txt` | 7 invocações do bloco B1 (9 caminhos) → CV entre-runs mediano 3% (máx 5%). Prova a máquina como instrumento. |
| `first-order-report.txt` | ordem de grandeza + pontos quentes + escala (rodada de 22/07). |
| `pilot_stats.py` | agrega K runs → CV + CI-95% t-Student por célula. |
| `baseline_report.py` | grandeza + hot-spots + slope log-log (encode vs linhas). |

## Como comparar com o `.9`

```
python -m bench_perf.runner --plan nucleo --out <run-09>.jsonl   # na máquina do .9
python -m bench_perf.compare perf-nucleo-2026-08-20.jsonl <run-09>.jsonl
```
> Use **`perf-nucleo-2026-08-20`** como baseline: é a rodada probatória e é a que
> corresponde ao core welded do `.8`. A de 22/07 fica como referência histórica —
> entre as duas o `src/tcf` mudou (258 commits, 34 no core).
`compare.py` normaliza pela razão dos calibradores (máquina) antes de comparar, e
classifica cada delta como RUÍDO vs real pelo maior entre MDE-do-tier e o piso de
ruído — coerente com o ±~5% run-a-run medido aqui.

## Achado que ancora o `.9`

- **Row-scaling (encode vs nº de linhas) já é LINEAR O(n)** (slope ~1.0) pra
  tcf-flat, json-ref e tcf-8h aninhado. Não há dívida de crescimento por linhas.
  **Confirmado** na probatória com `C/L/K` fixos: 0,93–1,00 em C=1/4/32/128.
- ~~**O penhasco é o canto R×C extremo**: `cantoRC-both` = 44.6s vs base(10k) 595ms
  = **~75×**~~ — **REVISADO 2026-08-20, ver abaixo.**

### ⚠ Revisão de 2026-08-20 (lab [`2330`](../../../lab/dirty/2026-08/2026-08-20/2026-08-20-2330-baseline-perf-08-probatoria/))

Três leituras acima precisam de correção, e as três se verificam nas **duas** rodadas:

1. **O canto R×C não é penhasco.** `base` tem 40 000 células e `cantoRC-both` tem
   3 200 000 — **80×**. Custo por célula: canto **1,00–1,02×** a mediana dos demais.
   Fazer 80× de trabalho em 75× de tempo é *sub*-linear. O modelo
   `t = a·células + b·bytes + c·únicos` (R²=0,9996) prevê o canto com resíduo **+0,2%**
   — é o caso mais bem previsto do conjunto.
2. **O eixo quente é CARDINALIDADE, não R×C.** O coeficiente por **valor único** é
   ~3,7× o coeficiente por célula (23 289 vs 6 322 ns); com `K=1` responde por ~4/5 do
   tempo. `L512` custa ~3,8× a mediana por célula, `K1` ~2,9×, `K0001` ~0,42×. O
   **mecanismo** nomeado acima (índice do OBAT) continua de pé; o **gatilho** era outro.
   A super-linearidade reproduzível está no **`free-text`** (slope 1,21–1,23 nas duas
   rodadas), e só de 1e4 para 1e5.
3. **O §3 de `baseline_report.py` é artefato.** Ele mistura `C` no eixo `R` e por isso
   dá `slope~1,47 [super-linear]` — inclusive para `json-ref-str`, que **é `json.dumps`**
   e é O(n) por construção. Com `C/L/K` fixos, tudo volta a ~1,0.

**E o calibrador super-corrige.** Os caminhos de referência são stdlib — código idêntico
nas duas rodadas — e dizem que a máquina fez **0,968** do trabalho de 22/07; os
calibradores dizem **0,830**. Discrepância de **+16,6%**, fabricada em cima de todo caso.
Higiene pendente do comparador (a segunda, junto do `runner_thermal_status`): normalizar
pelos caminhos de referência, que já estão no plano.

**Comparação sem normalizador nenhum** — `tcf-flat` ÷ `json-ref-str` no mesmo workload e
na mesma rodada (a máquina cancela por construção): a razão **caiu em 25 de 26**
workloads, mediana **−17,5%**. Posição do `.8`: encode custa **10× a 59×** o `json.dumps`
e emite **12% dos bytes** dele (mediana).
