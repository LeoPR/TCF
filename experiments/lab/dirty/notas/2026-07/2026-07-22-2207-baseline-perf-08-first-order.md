# Baseline de performance do #TCF.8 — leitura first-order [probatório]

**Data**: 2026-07-22 22:07. **Sequência**: fecha a linha aberta em
[`2026-07-22-0156-baseline-perf-parecer.md`](2026-07-22-0156-baseline-perf-parecer.md)
(parecer do owner) → Fase 3 do `bench_perf` (commits `2f587e8`/`da4544a`) → esta execução.
**Evidência versionada**:
[`experiments/results/evidencia-0.8/perf-baseline/`](../../../../results/evidencia-0.8/perf-baseline/).
**Processo**: `scripts/bench_perf/` (plano `nucleo`).

## Propósito (calibragem de rigor — decisão do owner)

O `.8` é protótipo não-lapidado ("com fita adesiva"). Pedir precisão estatística
aqui é injusto e prematuro — o `.9` é que vai mexer na **escala**
(linear→quadrático→melhor), não em 3%. Então o alvo é **noção de grandeza +
pontos quentes + números aproximados**. Extremos absolutos, cross-tech e
precisão → `.9`/`1.0`.

## Metodologia (literatura, sem inventar moda)

- **Georges, Buytaert & Eeckhout, OOPSLA 2007** — múltiplas invocações
  independentes; reportar variação/CI, não número solto.
- **Kalibera & Jones, ISMM 2013** — quantas repetições em cada nível.
- **Limite de medição**: ENTRADA(dataset materializado) → SAÍDA(wire). Carregar do
  disco (jsonl etc.) é formalismo, medido à parte, fora do número de encode.
- **Ambiente**: processo pinado (afinidade) a cores ociosos + prioridade High —
  ataca a variação de escalonamento (não "cair num core ocupado"), o que reduz o
  nº de repetições necessárias pro mesmo CI.

## Reprodutibilidade — a máquina como instrumento

Piloto: bloco B1 (9 caminhos, base scale) × **7 invocações** independentes,
pinadas. Variação **entre-runs**:

- **CV mediano 3.0%, máx 5.0%**; CI-95% (t, df=6) ≤ 4.6% em todas as 9 células.
- Calibradores C1/C2/C3: CV entre-runs 4–8%.

→ A variação residual é **ruído de processador de single-digit %**, exatamente o
esperado de um algoritmo determinístico em cores ociosos. Máquina validada como
instrumento pra medida de grandeza. (O gate binário `termicamente-reprovado` do
runner, que olha drift intra-run, marcou "suspeito" com drift 1.15 — mas a
reprodutibilidade real entre-runs, o que importa, é 3%. O gate é conservador
demais pra protótipo; foi **ignorado** por decisão metodológica.)

## Baseline — núcleo (106 células, 103 ok; ±~5%)

**Ordem de grandeza (encode)**: 2 μs · 53 ms · 36 (100ms) · 12 segundos.

**Pontos quentes (top)**: `cantoRC-both`=44.6s · free-text 100k=15s ·
flat-mixed 100k=4.8s · C128=3.2s · L512=2.4s.

**Escala — corte limpo (R-scan puro, C/L/K fixos no base)** — este é o número que
ancora o `.9`:

| caminho · forma | 100 → 1k → 10k → 100k linhas | slope log-log |
|---|---|---|
| tcf-flat · flat-mixed | 5.4ms · 57ms · 595ms · 4.84s | **~0.99 LINEAR O(n)** |
| json-ref-str · flat-mixed | 175μs · 1.9ms · 20ms · 218ms | ~1.03 LINEAR |
| tcf-8h · nested-object | — · 43ms · 476ms · — | ~1.04 LINEAR |

> **Correção da própria análise**: o 1º corte deu "super-linear ~1.5" pra
> tcf-flat — era **artefato** de agrupar C-scan/cantos junto do R-scan. Isolando
> o R-scan puro, o crescimento por linhas é **linear**.

**Onde está a super-linearidade**: NÃO no crescimento por linhas — no **canto R×C
extremo**. `cantoRC-both` = 44.6s vs base(10k) 595ms = **~75×**. É o **penhasco do
OBAT**: degeneração do índice de trigramas quando há muitos prefixos parecidos
(o mesmo O(n²/B) diagnosticado antes nos IPs).

> ### ⚠ REFUTADO em 2026-08-20 — o canto R×C não é penhasco
>
> A rodada probatória repetiu a medida e a leitura acima **não se sustenta**. `base` tem
> **40 000 células**; `cantoRC-both` tem **3 200 000** — **80×**. Comparar 44,6 s com 595 ms
> é comparar tempo absoluto de casos com **volumes diferentes**.
>
> | | 22/07 | 20/08 |
> |---|---:|---:|
> | tempo canto ÷ base | 74,9× | 76,7× |
> | células canto ÷ base | 80,0× | 80,0× |
> | **ns/célula do canto ÷ mediana dos demais** | **1,02×** | **1,00×** |
> | resíduo no modelo `t = a·células + b·bytes + c·únicos` (R²=0,9996) | **+0,3%** | **+0,2%** |
>
> 80× de trabalho em 75× de tempo é *sub*-linear, e o canto é o caso **mais bem previsto**
> do conjunto. O **mecanismo** apontado aqui (índice do OBAT) continua de pé — o que estava
> errado era o **gatilho**: o coeficiente por **valor ÚNICO** é ~3,7× o coeficiente por
> célula, e domina quando a cardinalidade é alta. O eixo quente é **cardinalidade e
> comprimento de valor** (`L512` ≈3,8× a mediana por célula, `K1` ≈2,9×, `K0001` ≈0,42×),
> e a super-linearidade reproduzível em R está no **`free-text`** (slope 1,21–1,23 nas duas
> rodadas), não no `flat-mixed`.
>
> Consequência para o item 2 da "Leitura pro `.9`" logo abaixo: o alvo não é o canto R×C —
> é o **termo por valor único**. A escada de prefixo adaptativa (P1) continua sendo a
> resposta plausível, mas o caso a bater é `K1`/`free-text`, não `cantoRC-both`.
>
> Lab: [`2026-08-20-2330`](../../2026-08/2026-08-20/2026-08-20-2330-baseline-perf-08-probatoria/).

## Leitura pro `.9`

1. **Row-scaling já é O(n)** — o `.9` não precisa "consertar" crescimento por linhas.
2. **Alvo claro = o penhasco R×C** (`cantoRC-*`, high-card/free-text): 44s deveria
   ser sub-segundo. É onde a **escada de prefixo adaptativa (P1)** ataca.
3. Método pronto: `bench_perf.compare` compara `.9` vs este snapshot com
   normalização por calibrador → o `.9` dirá se o penhasco virou linear.
