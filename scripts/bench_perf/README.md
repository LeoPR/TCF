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

# COMPARAÇÃO: os dois lados na mesma máquina e na mesma sessão térmica
python -m bench_perf.compare <baseline>.jsonl <candidato>.jsonl
#   veredito pela razão caso ÷ referência dentro de cada rodada (a máquina cancela);
#   caso sem referência de mesma cauda sai `sem-referencia`; rodada sem referência
#   usa o fator dos calibradores. Cada delta vira MELHOR/PIOR/IGUAL/RUIDO pelo maior
#   entre os MDEs do caso e da referência e os pisos de ruído das duas rodadas.
#   BLOQUEIA por: matriz/plano/intenção divergentes OU validade != completo.
#   Térmico só avisa (--strict-thermal bloqueia). --dev rebaixa tudo p/ aviso.
python -m bench_perf.compare --self <run>.jsonl    # auto-teste: tudo IGUAL, fator 1.0
```

## Fluxo `.8` → `.9` (a razão do processo existir)

1. **Os dois lados no mesmo pino.** Rodar `--plan nucleo --probative` sobre a tag `v0.8.4`, num
   worktree, e sobre o candidato, na mesma máquina e na mesma sessão térmica. O snapshot da `0.8.4`
   fica versionado em [`evidencia-0.8/perf-baseline/`](../../experiments/results/evidencia-0.8/perf-baseline/)
   (`perf-nucleo-2026-09-01.jsonl`) como referência de ordem de grandeza.
2. `compare.py <v0.8.4>.jsonl <candidato>.jsonl` dá o veredito por célula, com **mesmo `plano_sha`
   e `intencao`**: o comparador recusa cadências diferentes.
3. O que bater do `.8`: **o coeficiente por valor único** (~23 µs por único contra ~6 µs por
   célula) e o `free-text` em R≥1e5. O canto R×C é linear: 80× as células da base, custo unitário
   de 1,00 a 1,02× a mediana (lab `2026-08-20-2330`).

### Higiene pendente do comparador (não toca `src/tcf`)

- **`_adj` vs adjudicação**: `compare.py` interpreta só `runner_thermal_status`; consumir a
  adjudicação vigente é pendência antiga (ver README do snapshot).

### Por que a normalização é pela referência

Os calibradores C1/C2/C3 são laços apertados de aritmética, hash e alocação, e o trabalho real é
construção de string e dicionário: os dois não escalam juntos. Entre 22/07 e 20/08 os calibradores
disseram que a máquina fez 0,830 do trabalho, e os caminhos de referência da stdlib, com código
idêntico nas duas rodadas, disseram 0,968. O fator do calibrador fabricava +16,6% de regressão em
todo caso. A razão caso ÷ referência tirada dentro de cada rodada não tem fator a estimar, e foi
validada no lab `2026-09-01-1937`.

## Componentes

| módulo | papel |
|---|---|
| `runner.py` | orquestra: manifest → calibradores → casos → resumo (`run.json`). `avaliar_rodada()` = decisão de status PURA (testável). |
| `compare.py` | join por `case_id` + razão caso ÷ referência dentro da rodada (calibrador só sem referência) + veredito sinal-vs-ruído. `_adj()` lê validade/térmico robusto ao schema. |
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

## O pin da matriz

Cada plano carrega `pin_cases_sha256`, o SHA-256 dos **bytes** de `cases.json`, e o `--probative`
aborta quando o arquivo não bate com o pin. Qualquer mudança de bytes, inclusive formatação, pede
re-pin dos três planos no mesmo commit. O teste de contrato confere o pin contra o próprio arquivo,
e roda na suíte principal por `tests/test_bench_perf_contrato.py`.

Hashear o conteúdo canonizado da matriz (parse, `sort_keys`, separadores fixos) é a evolução
prevista, e entra junto com uma baseline nova, para não invalidar a comparação com as existentes.
