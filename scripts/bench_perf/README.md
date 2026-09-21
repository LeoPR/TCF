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
>
> O comparador bloqueia pelo primeiro campo, avisa no segundo e imprime a
> `nota_adjudicacao` da rodada, em vez de reinterpretar o gate térmico.

## Como rodar

```
# BASELINE (.8): cadência recorrente. Afinidade e prioridade são passo manual (feito em 22/07); o runner não aplica nem registra
python -m bench_perf.runner --plan nucleo --out <run>.jsonl
#   --probative     : fail-closed (aborta se árvore suja / cython ausente; exit≠0 se dados != completo)
#   --strict-thermal: com --probative, exige também estabilidade térmica
#   --plan {nucleo,campanha,smoke} : cadência (núcleo=barato recorrente; campanha=caro 1x; smoke=instrumento)
#   --smoke         : escala mínima (R<=100; B4 em R=200); o plano smoke sem --smoke roda os 132 casos em escala cheia
#   --only B1,B2    : sub-conjunto por bloco (sem plano)
#   --resume        : continua um JSONL parcial (mesmo git+matriz)

# COMPARAÇÃO: os dois lados na mesma máquina e na mesma sessão térmica
python -m bench_perf.compare <baseline>.jsonl <candidato>.jsonl
#   veredito pela razão caso ÷ referência dentro de cada rodada (a máquina cancela);
#   pareia primeiro pela cauda idêntica, depois recua para fonte/forma/escala/compressão
#   (`pareamento` em cada linha, `pareamento_por_dados` no resumo); rodada sem referência
#   usa o fator dos calibradores. Cada delta vira MELHOR/PIOR/IGUAL/RUIDO pelo maior
#   entre os MDEs do caso e da referência e os pisos de ruído das duas rodadas.
#   BLOQUEIA por: matriz/plano/intenção divergentes OU validade != completo.
#   Térmico só avisa (--strict-thermal bloqueia). --dev rebaixa tudo p/ aviso.
python -m bench_perf.compare --self <run>.jsonl    # auto-teste: toda célula com veredito sai IGUAL, fator 1.0
```

## Fluxo `.8` → `.9` (a razão do processo existir)

1. **Os dois lados no mesmo pino.** Rodar `--plan nucleo --probative` sobre o commit `e46ef37a`,
   num worktree com o `.pyd` copiado, e sobre o candidato, na mesma máquina e na mesma sessão
   térmica. É o `src/tcf` da `v0.8.4` com o pin consertado: na tag o runner aborta pelo pin. Os
   comandos estão em "Como comparar com o `.9`", no README do snapshot. O snapshot da `0.8.4`
   fica versionado em [`evidencia-0.8/perf-baseline/`](../../experiments/results/evidencia-0.8/perf-baseline/)
   (`perf-nucleo-2026-09-01.jsonl`) como referência de ordem de grandeza.
2. `compare.py <v0.8.4>.jsonl <candidato>.jsonl` dá o veredito por célula, com **mesmo `plano_sha`
   e `intencao`**: o comparador recusa cadências diferentes.
3. O que bater do `.8`: **o coeficiente por valor único** (~23 µs por único contra ~6 µs por
   célula) e o `free-text` em R≥1e5. O canto R×C é linear: 80× as células da base, custo unitário
   de 1,00 a 1,02× a mediana (lab `2026-08-20-2330`).

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
| `cases.py` + `cases.json` | matriz-mestra congelada (142 células; regra R2, não editar por cadência). |
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

Cada plano carrega `pin_cases_sha256`, o SHA-256 do **conteúdo canonizado** de `cases.json`
(parse, `sort_keys`, separadores fixos), e o runner com `--plan` aborta com código 4 quando o
arquivo não bate com o pin, com ou sem `--probative`. Mudar um **caso** pede re-pin dos três
planos no mesmo commit; reindentar ou reordenar chave, não. O teste de contrato confere o pin do
`nucleo` contra o próprio arquivo, e roda na suíte principal por
`tests/test_bench_perf_contrato.py`.

O pin era dos **bytes** até 2026-09-20, e o `manifest` grava os dois: `cases_sha256` é o do
conteúdo, e `cases_sha256_bytes` fica para rastrear as rodadas anteriores à troca. Rodada velha
não compara com nova pelo `--plan`, porque a matriz mudou de verdade: ela ganhou as células do
regime alvo.

## A ordem da rodada (2026-09-21)

O runner ordena os casos com `ordenar_vizinho`, que **põe cada caso ao lado da referência que
vai pareá-lo**, agrupando pela mesma chave que o comparador usa (fonte, forma, escala por
parâmetros, compressão), com as referências na frente de cada grupo.

O motivo é medido. A razão `caso ÷ referência` só cancela a máquina se os dois forem medidos
perto no tempo. Na ordem do arquivo a referência pareada ficava a **17 posições de mediana**,
109 no pior caso, e 57 das 72 células de dado do `nucleo` ficavam a mais de 5. Com a ordem
nova a mediana é **1**, o pior caso é 13, e sobram 12 acima de 5. O lab
`2026-09-21-0300-quatro-celulas` mostrou o tamanho do efeito: medindo o par adjacente, as
razões de quatro células ficaram abaixo de **todas** as cinco rodadas históricas.

A ordenação é determinística, não mede nada a mais e não tira nem duplica caso. O `run.json`
grava `ordem: por-chave-de-dado-v1`; **rodada sem esse campo é da ordem antiga**, e tem outra
estrutura de deriva. Comparar uma de cada lado é comparar uma razão limpa com uma suja, então
a baseline nova mede os dois lados com a ordem nova, que é o que a condição do owner (mesma
máquina, mesma sessão térmica) já exigia.

## O que mudou em 2026-09-20, e por quê

Quatro mudanças num commit, todas do lote de decisões do owner registrado no
[`T-PERF-BORDAS-E-MODOS-09`](../../tickets/T-PERF-BORDAS-E-MODOS-09.md):

1. **Células reais.** `build_pivot` passou a montar `adult-real` e `lineitem-real` do hub, pelo
   `dataset_reader`, com as primeiras R linhas e tudo em string, e a matriz ganhou quatro
   células: TCF e régua sobre o mesmo dado real, em cada fonte. Hub ausente vira **pendente**,
   não erro: o instrumento continua rodando em máquina sem os dados. Todo pivô materializado
   grava `dado_sha256`, o pin do dado por conteúdo, porque uma célula de amostra real não é
   reproduzível se o hub puder mudar embaixo dela. O `C` declarado é conferido contra o dataset.

   **Cuidado com o nome:** `adult-20k` e `lineitem-20k` são presets **sintéticos** que aproximam
   a forma daqueles datasets (`_MC_PRESETS`, bloco B4). Amostra real usa o sufixo `-real`, e os
   dois conjuntos não se misturam.
2. **Referências pareadas.** A cauda estrita deixava 31 das 106 células do `nucleo` sem
   veredito, todas `tcf-flat`. A cauda carrega `knobs`, `granularidade` e `accel`, que só
   existem na rota TCF, então exigi-la pediria referências JSON com `min_len=3` e granularidade
   `layer`, que não querem dizer nada. O comparador passou a **recuar** para fonte, forma,
   escala e compressão quando não há cauda idêntica, com a escala lida dos parâmetros
   (`R`, `C`, `L`, `K`) e não do rótulo do ponto, porque `C8` e `C8-col0` a `C8-col7` são o
   mesmo pivô. O estrito tem precedência, então nenhum veredito existente muda. Faltavam ainda
   duas referências de verdade, `free-text` em `R1e3` e `R1e5`, e elas entraram na matriz.
   O `nucleo` foi de 31 células sem referência para **zero**.
3. **`bytes_identicos` como gate.** Ele era gravado e ignorado. Agora a célula sai
   `bytes-divergentes`, que conta junto com `rt-quebrado`: derruba o `completo` e faz o runner
   sair com código diferente de zero. Vale nos dois pontos onde existe: perfil por camada
   (instrumentado contra limpo) e aceleração (cython contra puro, ADR-0020).
4. **Pin por conteúdo**, descrito acima.

As células do regime alvo entraram junto, porque a menor escala da matriz era `R=100` e o
regime declarado no ticket é payload de API: `R2e1` (R=20) no eixo R com a referência de mesma
cauda, e a rota de registro (`.8R`) em `R2e1` e `R1e2`, que antes só existia em `R=10000`.
