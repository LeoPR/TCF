# 2026-08-20-2330 — baseline PROBATÓRIO do `.8`, e a revisão do que 22/07 afirmou

## O que foi feito

A rodada probatória de `bench_perf --plan nucleo` — a que faltava desde 22/07
([memória do checkpoint](../../../notas/2026-07/)) — rodou com **árvore limpa**, Cython
presente e `--probative` (fail-closed). Resultado gravado em
[`evidencia-0.8/perf-baseline/`](../../../../../results/evidencia-0.8/perf-baseline/):

```
status=completo  termico=termicamente-suspeito  comparaveis(ok)=103  envelope=0
registro=106/106  {'ok': 103, 'pendente': 3}  ·  obrigatorio-falhou=0
```

Idêntico ao perfil de 22/07 (103/106, 0 obrigatório-falhou). O `pendente=3` é opcional
declarado, não falha.

Depois disso, este lab **lê** as duas rodadas e testa o que se pode afirmar delas.

> **O que o owner pediu, e a obrigação que fica** — *"faz sentido fazer mesmo com as
> otimizações que tem agora, elas serviriam como base para as otimizações futuras. **só
> precisamos lembrar de que temos que repeti-las.** independente disso, já saberíamos como o
> ver .8 está."*
>
> ⚠ **Esta rodada é BASELINE PINADO do `.8` em `6f04f3ae`.** Ela **tem de ser repetida**
> depois das otimizações do `.9`, com os calibradores rodando de novo.

## A ressalva que precede tudo

Entre `58f893eb` (22/07) e `6f04f3ae` (hoje) o `src/tcf` mudou: **258 commits, 34 tocando o
core, +2 576 linhas**. Isto **não é** repetir a mesma medida — é a **mesma versão de wire**
(`.8`/0.8.0) com o core evoluído. E o `tcf-8h` **mudou de rota** (`e855f1c0`:
`encode_hierarchical` → API única `encode`), então aquele caminho nem mede o mesmo código.

O harness é neutro: o único parâmetro removido de `probes.py` (`probe=`) nunca foi usado por
chamador nenhum, e o warmup segue idêntico. Matriz, plano e **dado gerado** batem (workload
idêntico em 106/106; RT íntegro em 106/106).

---

## 1. O calibrador super-corrige em +16,6% — e a stdlib é quem prova

Os caminhos `json-ref-*` e `csv-ref` chamam a **stdlib**. Esse código **não mudou** entre as
rodadas (mesmo CPython 3.13.13). Logo o delta bruto deles mede a **máquina, e nada mais**.

| | o que diz |
|---|---|
| calibradores C1/C2/C3 | máquina fez **0,830** do trabalho de 22/07 (17% mais rápida) |
| **stdlib (39 células)** | máquina fez **0,968** — apenas **3,2% mais rápida** |
| discrepância | **1,166** |

O calibrador **fabrica +16,6% de "regressão"** em cima de todo caso. Motivo plausível: C1/C2/C3
são laços apertados de aritmética/hash/alloc; o workload real é construção de string e
dicionário. Não escalam juntos na mesma máquina.

**Consequência prática**: o veredito bruto do `compare.py` (37 PIOR × 8 MELHOR) é lido
errado se tomado ao pé da letra. Normalizando pela referência em vez do calibrador:

| grupo | via calibrador | via referência |
|---|---:|---:|
| `column` | +42,3% | **+22,1%** |
| `layer` | +2,8% | −11,8% |
| `call` | −5,2% | −18,7% |
| **TCF (tudo)** | +0,2% | **−14,0%** |

Isto é **melhoria do instrumento**, e vale para a comparação `.8`→`.9`: os caminhos de
referência **já estão no plano** e são melhor normalizador que os calibradores.

## 2. O byte mudou em 8 casos — e o tempo a mais comprou byte a menos

95 casos **byte-idênticos**. Os 8 que mudaram são exatamente os 8 de granularidade `column`:

```
 -36,4% a -36,6% de BYTE   ·   +36,8% a +106,5% de tempo (bruto)
```

Verificado direto no wire, não inferido:

```
C8-col0 (R=2000, 200 únicos)   22/07: 14.646 B   →   hoje: 9.313 B
cabeçalho hoje: '#TCF.8B87d0'   ← discriminador `B`, o denso bN de domínio
```

O `B` (ADR-0036/37/38/39) **não existia em 22/07**. É troca declarada — o vértice tríplice
da [ADR-0002](../../../../../../docs/adr/) em ação — e não regressão.

## 3. O `cantoRC-both` **não é penhasco**. A afirmação vigente está errada.

A `STATUS.md` diz hoje:

> *"a super-linearidade está só no canto R×C extremo — `cantoRC-both`=44.6s vs base 595ms =
> **~75×**, o penhasco do OBAT... Alvo do `.9` = esse penhasco"*

Mas `base` tem **40 000 células** e `cantoRC-both` tem **3 200 000** — 80×. Custo unitário:

| rodada | tempo | células | ns/célula do canto | mediana dos demais | razão |
|---|---:|---:|---:|---:|---:|
| 22/07 | 74,9× | 80,0× | 13 929 | 13 684 | **1,02×** |
| 20/08 | 76,7× | 80,0× | 10 819 | 10 873 | **1,00×** |

**80× de trabalho em 75× de tempo é sub-linear.** E o modelo de custo confirma: o resíduo do
`cantoRC-both` é **+0,3% / +0,2%** — é o caso **mais bem previsto** do conjunto inteiro.

O erro de origem é comparar **tempo absoluto de casos com volumes diferentes**. É a mesma
classe já registrada em memória (*"escolho o que é fácil de contar em vez do que decide"*).

### O slope agregado do relatório também é artefato — o que 22/07 já sabia, e a ferramenta não

**Crédito onde é devido**: a nota de 22/07 já registra isto — *"o 1º corte deu 'super-linear
~1.5' pra tcf-flat — era **artefato** de agrupar C-scan/cantos junto do R-scan"*. O que ficou
por fazer é que **`baseline_report.py` continua imprimindo o artefato**: §3 dá
`tcf-flat flat-mixed slope~1,47 [super-linear]`, e dá **1,47 para `json-ref-str` também**, que
é `json.dumps` e é O(n) por construção. Com `C/L/K` **fixos** e só `R` variando:

```
tcf-flat  flat-mixed  0,93 – 1,00   LINEAR (C=1, 4, 32, 128 — nas duas rodadas)
json-ref  flat-mixed  1,02 – 1,07   LINEAR
tcf-flat  free-text   1,21 – 1,23   SUPER-LINEAR  ← e este é REAL, reproduzido 2/2
```

A super-linearidade reproduzível está em **`free-text`**, não em `flat-mixed`, e só na última
década (1k→10k é linear; 10k→100k custa 28× para 10× de dado).

## 4. Onde o custo realmente está: `t = a·células + b·bytes + c·únicos`

R² = **0,9996** nas duas rodadas, independentemente:

| coeficiente | 22/07 | 20/08 |
|---|---:|---:|
| `a` por célula | 7 698 ns | 6 322 ns |
| `b` por byte de entrada | 97,5 ns | 66,9 ns |
| **`c` por valor ÚNICO** | **30 717 ns** | **23 289 ns** |

O termo por **único** é ~3,7× o termo por célula. Com `K=1` (tudo único) ele responde por
~4/5 do tempo; com `K=0,001`, por quase nada.

**O eixo quente do `.8` é CARDINALIDADE (e comprimento de valor), não R×C.** Isso *mantém* o
mecanismo que a `STATUS.md` nomeia — o índice do OBAT — e **corrige o gatilho**. O custo
unitário confirma: `L512` ≈ 3,8× a mediana, `K1` ≈ 2,9×, `K0001` ≈ 0,42×.

## 5. A única afirmação de ganho que não depende de normalizador

Comparar `tcf-flat` com `json-ref-str` no **mesmo workload e na mesma rodada**: a máquina, o
térmico e o dia **cancelam por construção**. Não há fator para estimar nem para errar.

```
n=26 workloads · a razão TCF/json.dumps CAIU em 25 · mediana -17,5%
```

**Posição do `.8` hoje**: o encode custa **10× a 59×** o tempo do `json.dumps` e emite **12%
dos bytes dele** (mediana). O pior dos dois lados é o mesmo caso — `K=1,0` (tudo único):
**59× de tempo por apenas 24% de byte economizado**. Cardinalidade alta é ruim nos dois eixos.

---

## O que isto muda

1. **`STATUS.md`**: a frase do penhasco R×C precisa ser corrigida — o alvo do `.9` é o
   **termo por valor único** (índice do OBAT sob cardinalidade alta) e o **`free-text` em
   R≥1e5**, não o canto R×C.
2. **`bench_perf`**: os calibradores não representam o workload. Higiene para o `.9` —
   normalizar pelos caminhos de referência (que já estão no plano). Segunda pendência do
   comparador, junto da que o README já registra (ele lê só `runner_thermal_status`).
3. **`baseline_report.py` §3**: o slope agregado mistura `C` no eixo `R`. Como está, ensina
   errado — a própria stdlib sai "super-linear".

## Não medido (declarado)

- **Decode**: este lab olhou só `encode`. Os registros têm `decode` e não foram analisados.
- **Memória/RSS**: registrada pelo harness, não lida aqui.
- O coeficiente `c` não está identificado com precisão (n=20, preditores correlacionados:
  `bytes = células × L`, `únicos = células × K`). O que sustenta a leitura é a
  **reprodução independente** nas duas rodadas, não o ajuste isolado.
- **Térmico**: as duas rodadas são `termicamente-suspeito`. Vale a adjudicação
  `accepted-first-order` de 22/07 (piloto B1×7, CV entre-runs 3%).

## Evidência

[`outputs/`](outputs/) — `relatorio.txt` (a corrida inteira), `p1-calibrador.json`,
`p2-bytes.json`, `p3-penhasco.json`, `p3b-modelo-de-custo.json`, `p4-razao-interna.json`,
e o wire verificado `c8-col0.tcf` + entrada + roundtrip. Portão anti-órfão: conjuntos iguais.

## Conexões

- Rodada: [`evidencia-0.8/perf-baseline/`](../../../../../results/evidencia-0.8/perf-baseline/)
  (`perf-nucleo-2026-08-20.jsonl` · `.run.json` · `first-order-report-2026-08-20.txt`)
- Estudo de 22/07: [`2026-07-22-2207-baseline-perf-08-first-order`](../../../notas/2026-07/2026-07-22-2207-baseline-perf-08-first-order.md)
- Ferramenta: [`scripts/bench_perf/`](../../../../../../scripts/bench_perf/)
