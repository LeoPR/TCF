# Sub-exp 14 — Cross-subnet investigation (report)

**Data**: 2026-05-24
**Status**: completed — **2 bugs reais identificados em src/tcf canonical**

## Objetivo

Owner pediu investigacao do problema cross-subnet (sub-exp 11 refutou
hipotese gating, achado real eh issue arquitetural). Antes de propor
"detector multi-segmento", **diagnosticar empiricamente** por que M10
so' detecta 2 seq-RLE runs em D-IP-subnet 1000 (esperado ate' 20).

## Metodologia

1. Carregar D-IP-subnet em N=50/100/200/500/1000
2. Encode via M8A puro (sem seq-RLE post-process)
3. Inspecionar body lines apos M8A
4. Aplicar `detect_seq_runs` manualmente
5. Verificar pares cruzando subnet boundary com `compare_for_seq`

## Achados estruturais

| N | body_lines | unique_lengths | seq_runs | M10 ratio |
|---:|---:|---:|---:|---:|
| 50 | 50 | 3 | 2 | 5.78% |
| 100 | 100 | 3 | 2 | 2.87% |
| 200 | 200 | 4 | 2 | 68.17% |
| 500 | 500 | 6 | 2 | 105.30% |
| 1000 | 1000 | 7 | 2 | 117.51% |

`seq_runs` constante em 2 independente de N. Confirma que algo
bloqueia detecao alem da primeira subnet.

## BUG #1 — M8A nao cria atom para subnet 2

Body M8A do n=200 (transicao subnet 1 -> subnet 2):

```
   99: 1\98              <- ref atom 1 + literal "98"
  100: 1\99
  101: \125.\114.\71.\0  <- subnet 2 IP 0 (LITERAL completo!)
  102: \125.\114.\71.\1  <- ainda literal — atom NAO criado
  103: \125.\114.\71.\2
  ...
```

M8A criou atom 1 = `\57.\12.\140.` (prefix subnet 1) — funcionou. Mas
para subnet 2 prefix `\125.\114.\71.` (que repete 100x), atom NAO foi
criado. Cada linha repete o prefix completo.

Causa provavel: HCC composition detector tem heuristica greedy iterativa
que pode parar antes de criar atom secundario, OU criterio net > 0
nao foi satisfeito (criar atom custa N bytes, ganhos 99 ocorrencias).

## BUG #2 — `compare_for_seq` rejeita multi-run delta `{0,0,0,1}`

Test direto:
```
line_a = '\125.\114.\71.\1' (subnet 2 IP 1)
line_b = '\125.\114.\71.\2' (subnet 2 IP 2)
len OK (16 = 16), structure OK
runs_a = [(1,4), (6,9), (11,13), (15,16)]
runs_b = [(1,4), (6,9), (11,13), (15,16)]  -- same
diffs = [15]  -- only position 15 differs
```

Computar deltas:
- run (1,4): "125" -> "125" = delta 0
- run (6,9): "114" -> "114" = delta 0
- run (11,13): "71" -> "71" = delta 0
- run (15,16): "1" -> "2" = **delta 1**

deltas = [0, 0, 0, 1]. set = {0, 1}. **len != 1 -> retorna None!**

Codigo culpado em `hcc_seqrle.py:88`:
```python
if len(set(deltas)) != 1:
    return None
```

Esta heuristica **requer delta uniforme entre TODOS os runs**. Quando
linhas tem prefix invariante (runs com delta=0) + sufixo cadenced
(run com delta=1), rejeicao falsa.

## Diagnostico consolidado

Bugs sao **INDEPENDENTES e em CAMADAS DIFERENTES**:

| Bug | Camada | Impacto isolado |
|---|---|---|
| #1: M8A nao cria atom secundario | HCC composition detector | Linhas subnet 2 viram literais completos |
| #2: compare_for_seq rejeita multi-delta | HCC seq-RLE | Pares com prefix invariante + sufixo cadenced nao compactam |

**Se BUG #1 fosse fixado** (atom 2 criado): body subnet 2 viraria
`2\1, 2\2, ..., 2\99` — single run, single delta. seq-RLE funcionaria.
Bug #2 nao seria exercitado.

**Se BUG #2 fosse fixado** (multi-delta com 0+1): subnet 2 (sem atom)
ainda compactaria como `*99+1|\125.\114.\71.\0` — single marker
cobrindo 99 IPs.

## Fix proposals — modular separation

### Fix #1 (M8A — atom limit)

Investigar HCC composition detector — por que parou em atom 1?
- Hipotese A: net <= 0 pra atom 2 (literal short, ocorrencias=100,
  threshold rejeicao)
- Hipotese B: greedy iterativo limita iteracoes
- Hipotese C: prefix-detection coverage budget

Fix invasivo em src/tcf/composicional/syntax.py. ALTO risco quebrar
M9/M10 byte-canonical em D1-D9.

### Fix #2 (seq-RLE — multi-delta)

Trivial conceitual, marker format change:
```python
# Hoje (M10): single delta
*N+delta|template

# Proposta: per-run delta vector
*N+deltas|template   # deltas = "0,0,0,1" CSV
```

OU: marker indica posicao do run incremental:
```
*N+delta@runIdx|template  # delta no run especifico (idx 3 = run "1" no exemplo)
```

OU: simplificar — encode so' delta_nonzero, decoder identifica posicao
da diff entre template e template+delta (heuristica).

Todas opcoes requerem mudanca de marker format -> break M9/M10
backward compat. **NAO trivial pra welding.**

## Avaliacao "investigar se modular ajuda" (owner)

**Resposta: NAO, modular nao ajuda diretamente neste caso.**

Razoes:
1. Bug #1 nao eh detector-de-segmento; eh HCC composition. Multi-segment
   detector externo nao acessa decisao de criar atom.
2. Bug #2 eh seq-RLE local; multi-segment detector externo nao
   reescreve algoritmo compare_for_seq.

**Verdadeiro fix exige tocar src/tcf canonical** (M8A OU seq-RLE).
Risco alto, ganho potencial alto (cross-subnet pode atingir ratios
proximos a 5-10% em vez de 117%).

## Veredito

Investigacao bem-sucedida — bugs reais identificados. **NAO implementar
fix nesta sessao** (alto risco canonical). Registrar como:

- `T-CODE-HCC-MULTI-DELTA-FIX` — Bug #2 (seq-RLE multi-delta)
- `T-CODE-HCC-ATOM-DETECTION-REFINE` — Bug #1 (atom secundario)

Owner pode priorizar quando aparecer use case com cross-subnet
significativo em real-world.

## Lesson methodological

Sub-exp 14 reforca lesson sub-exp 11/13: **diagnosticar antes de
generalizar**. Hipoteses iniciais ("multi-segment detector") eram
direcao errada; investigacao revelou problemas mais especificos
e tratables individualmente.

Filosofia "viavel agora > otimo eventual" se aplica: M10 atual
funciona bem em casos single-subnet (5.78% em n=100). Cross-subnet
eh limite conhecido com workaround disponivel (variant C decimal
padded do sub-exp 09: 1.71% em todos N).

## Conexao

- [Sub-exp 08](../08-IP-tcu-delta/report.md): origem do achado cross-subnet
- [Sub-exp 11](../11-gating-refinement/report.md): refutou hipotese gating
- [Sub-exp 13](../13-base-aware-seq-rle/report.md): refutou hex generalization
- 3 sub-exps convergem: **fixes downstream sao limitados; investigar fonte
  do problema antes de generalizar**

## Outputs (auditoria)

- `n50/`, `n100/`, ..., `n1000/` cada com:
  - `input.txt` — IPs raw
  - `body-pos-M8A.txt` — body apos M8A puro
  - `body-pos-M10.txt` — TCF final
  - `seq_runs.json` — runs detectados
- `manifest.jsonl` — metricas
