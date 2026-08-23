# bench_perf: processo de medição de performance do TCF

Instrumento reprodutível de performance. Criado como **baseline first-order do `.8`** e desenhado
pra ser **reusado pelo `.9`** comparar (o `.9` roda a mesma cadência e o comparador diz se a
performance melhorou, linear, super-linear, etc.). **Não** é medida de precisão, o alvo é ordem
de grandeza + pontos quentes + números aproximados.

Metodologia: Georges, Buytaert & Eeckhout, *Statistically Rigorous Java Performance Evaluation*
(OOPSLA 2007), múltiplas invocações → variação, não número solto, e Kalibera & Jones,
*Rigorous Benchmarking in Reasonable Time* (ISMM 2013). Limite de medição: **ENTRADA (dataset
materializado) → SAÍDA (wire)**; carregar do disco é formalismo, medido à parte.

## Dois eixos ORTOGONAIS (não confundir)

| campo do `run.json` | o que é | quem bloqueia |
|---|---|---|
| **`status`** | **validade de dados**: `completo` (tudo registrado, zero rt-quebrado/erro, zero obrigatório-falho) ou `parcial` | **bloqueia** a comparação (evidência inválida) |
| **`runner_thermal_status`** | **estabilidade do ambiente**: `estavel` ou `termicamente-suspeito` (gate intra-run) | **só avisa**, first-order tolera; `--strict-thermal` bloqueia |

> Decisão (parecer 2340 §1): o térmico é AVISO, não veredito. Um run `completo` +
> `termicamente-suspeito` é **comparável** (a análise ENTRE-runs, piloto, é que adjudica a
> reprodutibilidade, não o gate intra-run). Ver `experiments/results/evidencia-0.8/perf-baseline/`.

## Como rodar

```
# BASELINE (.8) — cadência recorrente, pinada em cores ociosos p/ estabilidade
python -m bench_perf.runner --plan nucleo --out <run>.jsonl
#   --probative     : fail-closed (aborta se árvore suja / cython ausente; exit≠0 se dados != completo)
#   --strict-thermal: com --probative, exige também estabilidade térmica
#   --plan {nucleo,campanha,smoke} : cadência (núcleo=barato recorrente; campanha=caro 1x; smoke=instrumento)
#   --only B1,B2    : sub-conjunto por bloco (sem plano)
#   --resume        : continua um JSONL parcial (mesmo git+matriz)

# COMPARAÇÃO (.9 vs .8) — na máquina do .9
python -m bench_perf.compare <baseline-.8>.jsonl <candidato-.9>.jsonl
#   normaliza pela razão dos calibradores (máquina), classifica cada delta como
#   MELHOR/PIOR/IGUAL/RUIDO pelo maior entre MDE-do-tier e piso-de-ruído.
#   BLOQUEIA por: matriz/plano/intenção divergentes OU validade != completo.
#   Térmico só avisa (--strict-thermal bloqueia). --dev rebaixa tudo p/ aviso.
python -m bench_perf.compare --self <run>.jsonl    # auto-teste: tudo IGUAL, fator 1.0
```

## Fluxo `.8` → `.9` (a razão do processo existir)

1. `.8`: baseline versionado em [`evidencia-0.8/perf-baseline/`](../../experiments/results/evidencia-0.8/perf-baseline/).
   Use **`perf-nucleo-2026-08-20.jsonl`** (rodada PROBATÓRIA, `6f04f3ae`); a de 22/07 é histórica.
2. `.9`: rodar `--plan nucleo` na mesma máquina/estado → `perf-nucleo-<.9>.jsonl`.
3. `compare.py baseline candidato` → veredito por célula. **Mesmo `plano_sha` + `intencao`** obrigatório
   (o comparador recusa cadências diferentes). O achado do `.8` a bater: **o coeficiente por valor
   ÚNICO** (~23 µs/único vs ~6 µs/célula) e o `free-text` em R≥1e5.
   ~~o penhasco `cantoRC` (~75×)~~, **essa leitura foi REFUTADA em 2026-08-20**: o canto tem 80× as
   células da base, custa 1,00–1,02× o custo unitário mediano e o modelo linear o prevê com resíduo
   +0,2%. Não há penhasco ali. Ver [lab `2330`](../../experiments/lab/dirty/2026-08/2026-08-20/2026-08-20-2330-baseline-perf-08-probatoria/).

### ⚠ Higiene pendente do comparador (2 itens, nenhum toca `src/tcf`)

1. **`_adj` vs adjudicação**: `compare.py` interpreta só `runner_thermal_status`; consumir a
   adjudicação vigente é pendência antiga (ver README do snapshot).
2. **Os calibradores não representam o workload** (achado 2026-08-20). C1/C2/C3 são laços
   apertados de aritmética/hash/alloc; o trabalho real é construção de string e dicionário, e
   eles não escalam juntos. Medido entre 22/07 e 20/08: os calibradores dizem que a máquina fez
   **0,830** do trabalho; os caminhos de **referência** (stdlib, código idêntico nas duas rodadas,
   39 células) dizem **0,968**. O fator do calibrador **fabrica +16,6% de "regressão"** em cima de
   todo caso, foi o que produziu um falso `37 PIOR × 8 MELHOR`.
   **Conserto proposto**: normalizar pelos caminhos de referência, que **já estão no plano**,
   ou, melhor ainda, reportar a razão `tcf ÷ referência` *dentro* de cada rodada, em que a máquina
   cancela por construção e não há fator nenhum a estimar.

## Componentes

| módulo | papel |
|---|---|
| `runner.py` | orquestra: manifest → calibradores → casos → resumo (`run.json`). `avaliar_rodada()` = decisão de status PURA (testável). |
| `compare.py` | join por `case_id` + normalização por calibrador + veredito sinal-vs-ruído. `_adj()` lê validade/térmico robusto ao schema. |
| `plans.py` + `plans/*.json` | cadências versionadas (predicado sobre `cases.json`, pinado por `cases_sha256`). Duas rodadas só comparam com mesmo plano+intenção. |
| `cases.py` + `cases.json` | matriz-mestra congelada (132 células; regra R2, não editar por cadência). |
| `calibrators.py` | C1/C2/C3 (aritmética/hash/alloc), normalização cross-máquina + sentinela de drift. |
| `probes.py` | medição (samples_ns, tiers, MDE, CV). `synth.py` = gerador determinístico. |
| `pivot.py` · `layers.py` · `compress.py` · `crosscompat.py` · `manifest.py` · `natures_9.py` | gates (G1/G2/…), atribuição por-camada, níveis de compressão, alertas cross-compat, freeze, naturezas. |
| `tests/test_contrato.py` | testes de contrato (planos, `avaliar_rodada`, comparador, compat de schema). |

## Schema do `run.json` = `perf-baseline-09/run-v3`

`status` · `runner_thermal_status` · `manifest` (git/cython/plataforma/`cases_sha256`) ·
`calibradores` (C1/C2/C3) · `drift` · `plano` (id/sha/intenção) · `contagem` · `nota_adjudicacao`.
Compat: `_adj()` no comparador lê `run-v2` antigo (`status='termicamente-reprovado'` → validade
`completo` + térmico `suspeito`).
