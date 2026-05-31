# Observacoes (continuamente atualizado)

## 2026-05-17 — Sintese sub-exp 01 (baseline OBAT+HCC em D11a-h)

### Padrao dominante observado em cadencia regular

Em **D11a, D11c, D11d, D11e, D11f, D11g, D11h** (todos com cadencia regular),
OBAT gera um padrao quase-identico repetido em runs longos:

```
P(N, L) + L(small_var) + S(N, K)
```

Onde `small_var` e' o digito/digitos que mudam (1-2 chars apenas), e
`P(N, L)` + `S(N, K)` ja' sao identicos entre linhas.

Exemplo D11d (minute cadence, 9 linhas consecutivas):
```
[ 2] '2026-05-15 09:01:00' -> P(1,15) + L('1') + S(1,3)
[ 3] '2026-05-15 09:02:00' -> P(1,15) + L('2') + S(1,3)
[ 4] '2026-05-15 09:03:00' -> P(1,15) + L('3') + S(1,3)
...
[10] '2026-05-15 09:09:00' -> P(1,15) + L('9') + S(1,3)
```

`P(1,15) + S(1,3)` e' identico em 9 linhas — quase RLE. So' o literal
varia. HCC ate' compactou parcialmente no body (linhas tipo `9\7*6` —
o "9" vira numero do ref, o "7" e' o literal escapado, "*6" e' a parte
sufixa). Mas cada linha tem byte literal diferente → RLE adjacente nao
unifica.

Caso identico em D11h (ns):
```
[ 2..10] padrao P(1,25) + L(digit) + S(1,3) — 9 linhas
```

E D11c (mensal, 9 linhas mes 02..10):
```
[ 2..10] padrao P(1,6) + L(month_digit) + S(1,3) — 9 linhas
```

### Onde a cadencia "quebra"

Quando o literal variavel cresce de 1 pra 2 chars (digit 9 → 10),
LCP recua 1 char e LCS avanca 1 char. OBAT continua funcionando:
```
[11] '2026-05-15 09:10:00' -> P(1,14) + L('1') + S(1,4)
```

Mas o token agora e' diferente. Linhas 12-13 entao referenciam linha 11
(P(11,15)) em vez de linha 1. Mesma logica, mas runs do RLE-padrao
ficam **fragmentados** quando cardinalidade do literal muda.

### Onde NAO ha' padrao dominante

**D11b (bordas)**: cada linha cruza uma borda diferente (fim de mes,
inicio de ano, leap year). LCP/LCS comportamento varia. Token padrao
nao se repete. Delta-aware **tem ganho marginal aqui** — D11b e'
naturalmente caso pior.

### Quantificacao das oportunidades perdidas

| Dataset | Total linhas | Linhas em padrao dominante (consecutivas) | Bytes body atual |
|---|---:|---:|---:|
| D11a | 12 | 4 (linhas 2-5) + 3 (7-9) = 7 isoladas | 87 |
| D11b | 14 | 0 dominante claro | 173 |
| D11c | 13 | 9 (linhas 2-10) | 109 |
| D11d | 13 | 9 (linhas 2-10) | 110 |
| D11e | 13 | 9 (esperado) | 121 |
| D11f | 13 | 9 (esperado) | 115 |
| D11g | 13 | 9 (esperado) | 120 |
| D11h | 13 | 9 (linhas 2-10) | 123 |

D11c/d/h tem o padrao mais "limpo": 9 linhas consecutivas com mesmo
shape de token, so' literal varia.

### Implicacao pra delta-awareness

Se OBAT emitisse, no lugar de `P(N,L) + L(digit) + S(N,K)`, um token
unificado tipo `P(N,L) + Delta(+1,unit) + S(N,K)`:

- 9 linhas D11d se tornariam **identicas** (mesmo token, mesmo delta)
- HCC RLE: `*9|<token_unificado>` → 1 linha de body em vez de 9
- Estimativa byte: 9 linhas × ~10 bytes/linha = 90 bytes → 1 linha × 12-15 bytes ≈ **~75 bytes economizados** so' no run de 9

Mas isto e' **estimativa**, nao garantia. Custos:
- Token delta novo carrega bytes extras (marker)
- HCC precisa reconhecer o novo token pra RLE-agrupar
- Decoder precisa reconstruir o run completo

Validacao via fork sera necessaria pra mensurar.

### Linha cinzenta esclarecida

Pelas observacoes do baseline, divisao natural seria:

| Tarefa | Camada | Razao |
|---|---|---|
| Detectar que strings sao do mesmo tipo | OBAT (com hint do caller) | Hint e' barato; deteccao inline tambem possivel |
| Computar delta semantico entre 2 strings tipadas | OBAT | OBAT ja' compara, semantica e' extensao natural |
| Emitir token com delta inline | OBAT | Decisao por-comparacao (linha a linha) |
| Detectar que runs identicos de tokens-delta existem | HCC (RLE adjacente, ja' faz) | HCC ja' RLE-agrupa linhas identicas |
| Aglutinar em body compacto | HCC | Sua responsabilidade ja' |

Sem ambiguidade real. HCC nao precisa **detectar** delta — so' precisa
RLE-agrupar tokens **iguais** (o que ja' faz). Magic e': OBAT garante
que tokens fiquem iguais quando deveriam.

## 2026-05-17 — Reframing (pos-discussao): tripartite Pre/OBAT/HCC

Discussao subsequente ao baseline revisou o framing original. Pontos
de virada:

### Crítica do proposto inicial (sub-exp 02 com `TokRefDelta`)

A proposta de OBAT emitir `TokRefDelta(string_id, +N, unit)` violava
a separacao: estava fazendo OBAT **nomear** o delta com semantica
(`+N` em unidade especifica). Isso e' peso absoluto — territorio do
HCC.

OBAT trabalha com **pesos relativos abstratos**: decide se cabe ou
nao cabe, qual e' maior, sem saber quantos bytes vai custar no body.
HCC pega esses marcadores abstratos e materializa em bytes concretos.

### Nova hipotese do user (registrada como Q15)

> Se um no e' quebrado onde tem diferenca, talvez o unico esforco
> depois seja verificar se essa diferenca faz parte da estrutura
> anterior e como otimiza-la. OBAT pode estar quase pronto.

Observacao: OBAT ja' isola a variacao automaticamente — `Pref + Lit +
Suf`, o `Lit` e' exatamente a diferenca. Trabalho restante:
1. Pegar o `Lit` isolado (ja' feito)
2. Verificar se faz parte de estrutura observada antes (novo)
3. Decidir representacao mais barata (novo)

Esta hipotese fortalece a tentativa 02 (HCC sozinho): se OBAT ja'
quebra no lugar certo, talvez HCC sozinho reconheca o padrao nos
Lits isolados — **sem fork de OBAT**.

### Tripartite Pre/OBAT/HCC

| Camada | Responsabilidade | Tipo de peso | Conhece tipo? |
|---|---|---|---|
| Pre | Detectar tipo + gerar dica generica | Analise (sem bytes) | Sim |
| OBAT | Comparacoes relativas + decidir se quebra | Relativos (cabe/nao) | Nao (so' modos) |
| HCC | Materializar + juntar inteligentemente | Absolutos (bytes) | Nao |

Dica generica deve evitar nomear tipo. Aceito:
`byte_window`, `enable_relative`, `monotonic_expected`, `max_delta`.
Rejeitado: `type="date"`, `parse_as=datetime`, etc.

### Tentativas planejadas (substituem sub-exp 02 original)

| # | Nome | Escopo | Mexe em |
|---|---|---|---|
| 02 | HCC sozinho | RLE pra tokens near-identical | so' HCC (fork) |
| 03 | OBAT com `byte_window` | Calibrar LCP/LCS via dica | so' OBAT (fork) + Pre |
| 04 | OBAT relativo + HCC RLE | Δ abstrato + agregacao | OBAT + HCC (forks) + Pre |

Ordem: 02 → 03 → 04. Cada uma informa a proxima:
- **02 primeiro** pra testar se OBAT realmente esta pronto (Q15)
- **03 segundo** pra validar se dica generica e' viavel/util
- **04 ultimo** porque depende de saber resultados de 02 e 03

Criterio de "ganho mensuravel" por tentativa:
- Bytes < baseline em pelo menos um dataset D11a-h
- RT byte-canonical 8/8 OK

### Linhas cinzentas que cada tentativa vai clarificar

| Pergunta | Tentativa |
|---|---|
| HCC sozinho consegue agrupar near-identical? | 02 |
| Dica generica e' realmente util sem viciar? | 03 |
| Onde fica o "decidir emitir delta"? | 04 |
| Como o decoder reconstroi sem tipo explicito? | 04 |
| Memoria O(1) sobrevive a comparacao relativa? | 03 + 04 |

### Notas

Detalhes finais em `modelo-conceitual.md` (atualizado) e
`perguntas-abertas.md` (Q1, Q2, Q4, Q5, Q14 resolvidos;
Q15-Q17 novas).

## 2026-05-17 — Resultado tentativa 02 (HCC sozinho)

Executada. **Q15 confirmada empiricamente**.

### Numeros (D11a-h)

| Dataset | canon | fork | Δ bytes | Δ % | runs |
|---|---:|---:|---:|---:|---|
| D11a | 87  | 84  | -3   | -3.4%  | 2 (3+2 lines) |
| D11b | 173 | 173 | 0    | 0.0%   | 0 |
| D11c | 109 | 78  | -31  | -28.4% | 1 (7 lines) |
| D11d | 110 | 73  | -37  | -33.6% | 1 (8 lines) |
| D11e | 121 | 90  | -31  | -25.6% | 1 (7 lines) |
| D11f | 115 | 78  | -37  | -32.2% | 1 (8 lines) |
| D11g | 120 | 83  | -37  | -30.8% | 1 (8 lines) |
| D11h | 123 | 86  | -37  | -30.1% | 1 (8 lines) |

**Total: 958 → 745 bytes (-22.2%). RT 8/8 OK.**

### Mecanismo (concreto, pra registro)

OBAT canonical (intocado) emite 8 linhas D11d com tokens
`P(1,15) + L("N") + S(1,3)` para N=1..9. HCC canonical materializa
em 8 body lines `5\digit*4`. Fork de HCC detecta runs pos-emit e
compacta em `*8+1|5\2*4`.

Sintaxe `*N+delta|<template>`:
- Compativel com `*N|` (RLE puro) pela presenca do `+`
- Decoder shifta escape-digits do template para gerar N variantes
- Limitado a: linhas mesmo length, diffs apenas em escape-digits,
  delta consistente entre pares consecutivos

### O que isto resolve

- **Q15 (OBAT quase pronto)**: confirmada. Quebra de OBAT ja' isola
  a variacao; HCC reconhece o padrao na variacao.
- **Linha cinzenta entre OBAT e HCC**: pelo menos pra estes datasets,
  **nao existe**. HCC pega tudo.
- **Restricao "src/tcf intocado"**: respeitada. Fork dirty completo.

### O que NAO resolve

- D11b (bordas): 0 ganho. Esperado — sem cadencia regular consecutiva.
- Cardinalidade transition (\\9 -> \\10): runs param na transicao.
  Esperado, sintaxe simples nao cobre.
- Datasets com cadencia irregular mas comparativa relativa
  detectavel: nao testado aqui.

### Decisao sobre tentativas 03 e 04

Re-avaliacao em ordem:

- **Tentativa 03 (OBAT com dica `byte_window`)**: ainda faz sentido
  como **exercicio conceitual** (validar Q16/Q17 sobre dicas
  genericas), mas expectativa de ganho de bytes e' baixa — HCC ja'
  extraiu o que da' nestes datasets. Pode revelar coisas para
  datasets diferentes (cadencia irregular).
- **Tentativa 04 (OBAT relativo + HCC integrado)**: re-avaliar apos
  03. Possivelmente cancelar ou reduzir escopo. So' faz sentido se
  houver caso onde HCC sozinho falha mas OBAT relativo ajuda.

Proximo passo: discutir com user se vale rodar 03 ou pular pra
estudo de novos datasets (cadencia irregular).

### Detalhes literais

Arquivos completos:
- Encoder/decoder fork: `02-hcc-sozinho-rle-near-identical/hcc_fork.py`
- Bodies fork por dataset: `02-.../outputs/<ds>/2-body-fork.tcf`
- Diffs lado-a-lado: `02-.../outputs/<ds>/3-diff-canonical-vs-fork.md`
- Analise final: `02-.../result.md`

## 2026-05-17 — Resultado sub-exp 03 (H-DA-04)

Executado audit. **H-DA-04 refutada na forma pura "HCC sozinho"**.

### Numeros

Residual nao-compactado nos 8 datasets:
- Type A (mesmo length, digits): **6 bytes** total (1 caso D11b)
- Type B (lengths diferem, parecidos): **299 bytes**
- Type C (totalmente diferentes): **50 bytes**

Type A: nao implementar (negligible / complexidade alta)
Type B: requer cooperacao de OBAT — fora do escopo H-DA-04
Type C: fora de alcance grammar

### Hipotese nova decorrente — H-DA-07

Pattern observado: D11d/e/f/g/h tem 3 linhas pos-transicao com
estruturas distintas (`R\L*R,R` → `R~R,R,R` → `R,R,R`). Se OBAT
mantivesse shape `P+L+S` atraves da transicao 9→10 (escolha
nao-greedy via dica), as 3 linhas seriam compactaveis pelo seq-RLE
existente.

Quantificacao: ~150 bytes recuperaveis se H-DA-07 funcionar (~50%
do Type B residual). Concentra-se em datasets com cadencia regular.

### Implicacoes

- H-DA-04 fechada como `refutada (com grammar atual)`
- H-DA-05 absorvida (mesma direcao que H-DA-07/02)
- H-DA-07 nova — registrada no roadmap, candidata a sub-exp 04
- H-DA-02 (dica generica) ganha relevancia: era especulativa, agora
  tem alvo mensuravel (150 bytes)

### Detalhes

- Audit script: `03-cadence-break-recovery/audit.py`
- Audit completo: `03-.../audit.md`
- Conclusao: `03-.../result.md`

## 2026-05-17 — Sub-exp 04 (H-DA-07 OBAT shape-consistency)

Executado. **H-DA-07 CONFIRMADA** com magnitude maior que estimada.

### Numeros (D11a-h)

| Pipeline | Total bytes |
|---|---:|
| Baseline (OBAT canon + HCC canon) | 958 |
| Tentativa 02 (OBAT canon + HCC fork) | 745 (-22.2%) |
| **Sub-exp 04** (OBAT fork shape-preserve + HCC fork) | **652 (-32.0%)** |

Ganho 04 vs t02: **-93 bytes (-12.5%)**. RT 8/8 OK.

### Mecanismo

OBAT fork com hint **generica** `prefer_shape_consistency=True`.
Apos cada emissao, memoriza `(p_src, p_len, has_L, s_src, s_len)`.
Pra proxima string, tenta replicar shape (com fallback wider se
exato falhar). Single-pass, O(1) memoria extra.

Para D11d s11-s13 (cadencia transicionou 9 → 10):
- Canonical OBAT: 3 shapes distintos → 24 bytes body
- Fork OBAT: shape (P=14, L=2-char, S=3) uniforme → seq-RLE
  compacta em `*3+1|1\10*4` → 12 bytes body

### Bug-fix decorrente

Detector `compare_for_seq` do `hcc_fork.py` tinha checagem
demasiado estrita (exigia TODAS posicoes dentro de escape-digit
runs em diffs). Quebrava lit multi-digit como "10"→"11" (diff so'
posicao 3, mas run "10" interpretada como int 10 → 11).

Fix aplicado em `02-.../hcc_fork.py`. Impacto t02: 0 bytes (OBAT
canonical nao produz lit multi-digit). Impacto sub-exp 04: dobrou
o ganho (-46B → -93B).

### Surpresa: D11b (bordas) ganhou -20 bytes

Esperado: 0 (sem cadencia clara). Real: -20.

Mecanismo: shape-preserve forca OBAT a usar mesma source string
(s1) em s2-s5. Pattern parallel reusa mais frags. Cleaner refs
no HCC = body menor MESMO sem seq-RLE compactando.

**Beneficio secundario nao previsto**. Hint shape-preserve melhora
bodies mesmo onde o detector seq-RLE nao aciona.

### Implicacoes pras hipoteses

- **Q15** ratificada com nuance: HCC sozinho extrai 22%, mas OBAT
  + HCC integrados extraem 32%. "OBAT quase pronto" precisa de
  pequeno cutucao via dica.
- **H-DA-02** (dica generica viavel) — confirmada via H-DA-07.
  Q16/Q17 respondidos: dica boolean simples e' suficiente.
- **Tripartite Pre/OBAT/HCC** funciona: Pre emite hint, OBAT
  permanece type-agnostic, HCC materializa.

### Novas hipoteses decorrentes

- **H-DA-08**: detector com per-run delta encoding (alguns runs
  delta=0). Quantificado ~6B em D11b lines 3-4.
- **H-DA-09**: Pre-stage infere hint observando primeiras N
  strings. Nao testado.

### Detalhes

- Plano: `04-obat-shape-consistency-hint/README.md`
- Encoder: `04-.../obat_fork.py` (processar_with_hint)
- Executor: `04-.../run.py` (3 pipelines comparativos)
- Resultado: `04-.../result.md`
- Bodies por dataset: `04-.../outputs/<ds>/`

## 2026-05-17 — Sub-exp 05 (H-DA-06 numeric IDs)

Executado. **H-DA-06 CONFIRMADA**. Pipeline generaliza pra IDs
numericos. Tambem **refinou H-DA-04** (era refutacao parcial).

### Numeros (D16a/b/c — datasets novos)

| Dataset | baseline | t02 | sub-exp 05 | Δ vs t02 | Δ vs baseline |
|---|---:|---:|---:|---:|---:|
| D16a (3-digit "100".."112") | 65 | **11** | 11 | 0 | **-83%** |
| D16b (4-digit "1000".."1012") | 62 | 35 | **28** | -7 | -55% |
| D16c (prefixados "USR-100".."USR-112") | 70 | 47 | **38** | -9 | -46% |
| **Total** | **197** | **93** | **77** | **-16** | **-61%** |

RT 3/3 OK.

### Surpresa D16a — refina H-DA-04

D16a: OBAT canonical NAO cria refs (LCP=2 < min_len=3 entre adjacentes).
13 literais puros emitidos. HCC fork seq-RLE captura TUDO em UM
unico run: `*13+1|\100`.

A transicao 109→110 (cardinality change conceitual mas same length)
e' atravessada porque o detector trata escape-digit runs como
**inteiros**: `int("109") + 1 = 110`, formatado com mesmo width.

**Implicacao pra H-DA-04**: era refutada SOMENTE no caso **com refs
ao redor** do varying lit (estrutura `P+L+S` do D11d). **Sem refs
(string inteiro como lit)**, seq-RLE ja' resolve naturalmente.

H-DA-04 status atualizado pra "refutada parcial" no roadmap.

### Generalidade confirmada

Mesmo padrao do D11d para D16b e D16c:
- s2-s10 com OBAT canonical → run de 9
- s11-s13 sem OBAT fork → 3 linhas separadas
- s11-s13 com OBAT fork → 1 run extra

D11d funciona com datetime; D16b/c funcionam com numeric ID. Mesma
mecanica. **Pipeline e' generico**.

### Nova hipotese H-DA-10

Existe trade-off: criar refs longos (reduz overhead inicial) vs.
nao criar refs (deixa seq-RLE livre). Em strings curtas (D16a:
3 chars), nao criar refs e' melhor. Em strings longas (D11d:
19 chars), criar refs e' melhor.

Possivel direcao futura: ajustar min_len por contexto, OU permitir
OBAT escolher refs/no-refs com base em hint.

### Datasets criados

- `datasets/synthetic/D16a-ids-3digits.csv` (13 IDs "100".."112")
- `datasets/synthetic/D16b-ids-4digits.csv` (13 IDs "1000".."1012")
- `datasets/synthetic/D16c-ids-prefixados.csv` (13 IDs "USR-100".."USR-112")

### Detalhes

- Plano: `05-numeric-ids-h-da-06/README.md`
- Run: `05-.../run.py` (reusa obat_fork.py e hcc_fork.py)
- Resultado: `05-.../result.md`
- Bodies: `05-.../outputs/<ds>/`

## 2026-05-17 — Sub-exps 06, 07, 08 (fechamento pacote 1)

Executados em batch pra fechar pacote 1.

### Sub-exp 06 (H-DA-09 auto-hint regression D1-D9) — REFUTADA PARCIAL

Aplicou pipeline sub-exp 04 em D1-D9 (datasets stress).

**Resultado**: 5/9 regressoes, +275B total (+17% sobre baseline).

| Comportamento | Datasets |
|---|---|
| Ganho | D1 (-14B), **D9 (-92B, -58%!)** |
| Empate | D4, D8 |
| Regressao leve | D2 (+3B), D3 (+8B) |
| Regressao moderada | D6 (+67B), D7 (+100B) |
| **Regressao alta** | **D5 (+203B, +72%)** |

Hint NAO pode ser default-on. Precisa Pre stage **inteligente** ou
ser opt-in pelo caller. **H-DA-09 refutada na forma simples.**

**H-DA-09b** registrada: auto-detection sofisticada (heuristica
length uniformity / LCP stability) fica aberta.

**Achados extra**: D9 wrapper pattern e' MUITO favoravel ao hint.
D5 pattern misto e' MUITO desfavoravel. Registradas H-DA-11 (wrapper
pattern) e H-DA-12 (anti-pattern detector).

### Sub-exp 07 (H-DA-08 per-run delta audit) — REFUTADA

Audit dos bodies fork+fork (sub-exp 04+05) procurando pares
qualificaveis para per-run delta encoding (`*N+delta@idx|template`).

**Resultado**: 3 pares total, **9 bytes** potencial em todo D11+D16.

Marker `*N+delta@k|template` custa ~5 bytes extras alem do template
— come quase toda a economia em pares de 2 linhas.

**H-DA-08 refutada**: ganho marginal nao justifica complexidade.

### Sub-exp 08 (H-DA-10 min_len trade-off) — CONFIRMADA

Variou `min_len` ∈ {2, 3, 4, 5} em D16a, D11d, D9.

| Dataset | min_len optimal | Ganho vs default(3) |
|---|---:|---:|
| D16a (3-char) | 3 | 0 (default ja' otimo) |
| D11d (19-char) | 2 ou 3 | 0 (empate) |
| **D9 (wrapper)** | **5** | **-33B (-26% vs default)** |

D9 com min_len=5: refs maiores e uniformes que coincidem com o
wrapper pattern. OBAT nao cria refs micro espalhados.

**H-DA-10 confirmada**. **H-DA-10b** registrada (auto-tune min_len
no Pre stage).

### Hipoteses novas decorrentes

- H-DA-09b: auto-detect cadencia via heuristica
- H-DA-10b: auto-tune min_len no Pre stage
- H-DA-11: H-DA-07 muito eficaz em wrapper+slot patterns
- H-DA-12: detectar shapes diferentes pra desabilitar hint

### Detalhes

- `06-auto-hint-regression-D1-D9/result.md`
- `07-per-run-delta-audit/result.md`
- `08-min-len-trade-off/result.md`

## 2026-05-17 — Sub-exp 09 (H-DA-09b auto-detect cadence)

User pediu **revisao conceitual rigorosa**. Insight chave: mesmo
observadores boas/ruins podem falhar conceitualmente. Reframe
estrutural + sub-exp testando heuristica concreta.

### Resultado

| Pipeline | Total (20 datasets) | vs baseline |
|---|---:|---:|
| Baseline | 2770 B | — |
| Always-on (sub-exps 04+06) | 2619 B | -5.5% |
| **Auto-detect heuristica** | **2272 B** | **-18.0%** |

**3x melhor que always-on**, evita regressoes catastroficas:
- D5 (+203B), D6 (+67B), D7 (+100B) zerados
- D9 (-92B), D11a-h (-49B cada), D16b/c capturados

**18/20 acertos**. Perdas: D1 (-14B) e D11b (-20B) — onde lengths
variam mas always-on ainda ajudaria.

### Mecanismo

`detect_cadence(strings, n_sample=5, threshold=0.7)`:
1. Se lengths nao uniformes → no cadence
2. Se LCP+LCS / length < 0.7 em algum par consecutivo → no cadence
3. Caso contrario → yes cadence

Type-agnostic. Single-pass. Memoria O(5).

### Confirmacao com ressalvas

H-DA-09b **confirmada-empirica**. NAO "confirmada-conceitual"
porque:
- Threshold 0.7 e' arbitrario
- 20 datasets ainda sao sinteticos
- 2 misses sao perdas reais
- Adversarial inputs nao testados

### Hipoteses decorrentes

- H-DA-09c: tunar threshold
- H-DA-09d: heuristica multivariada
- H-DA-09e: re-avaliar a cada N (adaptativo)

### Detalhes

- `09-auto-detect-cadence-heuristic/auto_pre.py`
- `09-.../run.py`
- `09-.../result.md`
