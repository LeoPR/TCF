---
title: Revisao conceitual de hipoteses confirmada-empirica (2026-05-21)
type: meta-analise
status: published
tags: [methodology, hipoteses, generalizacao, real-world, anti-incidente]
created: 2026-05-21
updated: 2026-05-21
related:
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - experiments/lab/dirty/2026-05-21-escape-deduction/
  - experiments/lab/dirty/2026-05-21-revalidacao-categoria-B/
  - tickets/META-ESCAPE-DEDUCTION.md
  - tickets/T-REVAL-H-DA-01-06-10.md
---

# Revisao conceitual — hipoteses confirmada-empirica (2026-05-21)

**Motivacao**: Pacote 2 (escape deduction) foi fechado como
CLOSED-INSUFFICIENT-GAIN em 2026-05-21 com aprendizado critico:
sub-exp 11 antigo (T01) deu 15.7% ganho em D11a-h **mas em real-world
o ganho cai pra 0.13-1.13%** — uma reducao de **10-15x**.

Esse incidente expoe risco generalizado: **muitas hipoteses
`confirmada-empirica` no roadmap foram testadas APENAS em datasets
sinteticos** (D1-D9, D11a-h, D16a-c, etc.) que podem ter perfil
enviesado pro teste.

Esta revisao audita TODAS as hipoteses confirmadas-empiricas
classificando por evidencia de generalizacao real-world.

## Categorias

**A — GENERALIZA real-world** (testada em Adult Census, TPC-H, ou
lineitem com escala ≥1k rows)

**B — NAO TESTADA em real-world** (risco: pode nao generalizar; pode
ter mesmo destino do Pacote 2)

**C — TESTADA E NAO GENERALIZA** (refutada-real-world, ja' documentada)

## Tabela completa

### Categoria A — GENERALIZA real-world ✓

| ID | Hipotese | Evidencia real-world | Confianca |
|---|---|---|---|
| H-DA-09b-v2 | Heuristica numeric+high-card | Adult 1k/5k + TPC-H 8 tabelas (-135,638B, RT 12/12) | **Alta** — welded ADR-0008 |
| H-RW-05 | Encode O(N²) | lineitem 1k-20k extrapolacao + full 60175 real (21.3min) | **Alta** — mitigado ADR-0009 |
| H-PERF-01 | pref+suf = 74% tempo | profile real lineitem 5k | **Alta** — confirmado direto |
| H-PERF-01b | HCC = 24% tempo | mesmo profile | **Alta** |
| H-PERF-02 | Hash trigrama -> O(N) amortizado | lineitem 1k/5k/10k/20k + full 60k, 2.70x em 20k | **Alta** — welded ADR-0009 |
| H-PERF-03 | len-elim 1.3x | benchmark em D1-D9 + lineitem | **Alta** (absorvida) |
| H-PERF-05b/c | counting direto / skip trace | benchmark real lineitem 5k | **Alta** (marginal confirmado) |

### Categoria B — NAO TESTADA real-world ⚠ (risco) — REVALIDADA 2026-05-21

**Status**: 3 hipoteses-foco revalidadas em
`2026-05-21-revalidacao-categoria-B/` (ticket T-REVAL-H-DA-01-06-10).
Resultados moveram cada uma pra categoria definitiva — ver
[seção "Resultados revalidacao 2026-05-21"](#resultados-revalidacao-2026-05-21).

| ID | Hipotese | Datasets testados | Resultado revalidacao |
|---|---|---|---|
| **H-DA-01** | OBAT+HCC quase pronto (-22.2%) | D11a-h construidos | **MARGINAL** real-world (1.36%, 16.3x reducao); seletivamente potente em colunas com cadencia (-92% c_custkey) |
| **H-DA-06** | Numericos delta IDs (-61%) | D16a-c criados | **SUBSUMIDA** em H-DA-09b-v2 (cobertura 87.5% real-world) — confirmacao do palpite |
| **H-DA-07** | OBAT shape-preserve | D11+D16 sinteticos; +17% em D1-D9 (regressao!) | NAO revalidado nesta rodada — condicional ja' documentada via auto-pre detect_cadence |
| **H-DA-10** | min_len trade-off | **N=3 datasets, N=4 valores** | **CONFIRMADA REAL-WORLD inesperadamente** — 9.92% weighted, ate -36.78% em fnlwgt. Mais robusto que predito |
| H-PT-02 | Pre-tx tz-aware | D11j/k/m sinteticos | Histórico — pre-tx multi-pass foi superseded pelo Pacote 1. Sem acao necessaria |
| H-PT-03 | Pre-tx unit normalization | D11f/g/h sinteticos | Idem H-PT-02 — historico |

### Categoria C — TESTADA E NAO GENERALIZA ✗

| ID | Hipotese | Datasets sinteticos | Real-world | Reducao |
|---|---|---:|---:|---:|
| H-ED-01 | Linha 1 escape redundante | 15.7% (D11a-h) | 0.01% | 1500x |
| H-ED-02 | Apos `*` separador | 15.7% | 0.12% | 130x |
| H-ED-03 | Operators escape | (parte do 15.7%) | 0% (zero ops em real-world) | refutada |
| H-ED-original | Valor > count | (assumido alto) | 1.13% lower bound | confirmado baixo |

## Padroes de nao-generalizacao identificados

### 1. Datasets construidos pra testar a hipotese

D11a-h foram **construidos** com cadencia explicita pra testar Pacote 1
delta-aware. Funcionou bem ali. D16a-c **criados pelo autor** pra
testar numericos. Esses datasets sao **enviesados** — TCF pode estar
otimizando pro perfil exato do dataset.

**Sintoma**: ganho "muito alto" (>20%) em sintetico.
**Diagnostico real-world**: tipicamente <5%.

### 2. Amostras pequenas (N < 10 datasets diversos)

H-DA-10 testou N=3 datasets, N=4 valores de min_len. Estatistica
nao-confiavel.

**Sintoma**: confianca "X funciona em D9 com min_len=5".
**Diagnostico**: pode ser ruido. Real-world precisa N>=20 datasets
de FONTES diferentes.

### 3. Cumulativo em sintetico vs disperso em real-world

Datasets D11a-h tem 22-60 bytes cada. Salvar 7 bytes vira "13.6%".
Em real-world (200kB-500kB), os mesmos 7 bytes viram <0.01%.

**Sintoma**: percentual alto em datasets pequenos.
**Diagnostico**: medir tambem em **bytes absolutos** comparados ao
overhead total. Se ganho/total <5%, marginal.

### 4. Falta comparacao contra ortogonal externa

TCF nao foi comparado contra gzip/brotli em maioria dos sub-exps.
Algumas otimizacoes podem ser ortogonais a TCF mas DUPLICADAS por
compressao externa.

**Sintoma**: ganho "real" mas sem contexto se complementa ou substitui
brotli na cadeia.

## Recomendacoes concretas

### Prioridade ALTA — re-teste real-world urgente

| ID | Acao | Justificativa |
|---|---|---|
| H-DA-01 | Medir bytes em pipeline TCF puro VS pipeline + H-DA-01 (HCC seq-RLE isolado) em Adult/TPC-H | Se ganho <5% real-world, marcar como `absorvida em pipeline` (sem credito proprio) |
| H-DA-06 | Verificar se H-DA-09b-v2 (numeric+high-card) ja' captura os mesmos casos. Se sim, marcar `subsumida` | Pacote 1 refino pode ja' ter coberto |
| H-DA-10 | Medir min_len ∈ {3,4,5,6} em Adult+TPC-H, escolher por dataset | N=3 sintetico nao basta pra confiar |

### Prioridade MEDIA — re-testes condicionais

| ID | Acao | Justificativa |
|---|---|---|
| H-DA-09b (sem v2) | Verificar isoladamente se sub-exp 09 (sintetico) ainda agrega valor sobre v2 (real-world) | Pode ser que v2 absorva v1 |
| H-DA-07 | Documentar matriz "quando usar / quando nao" (ja' feito parcialmente via auto-pre) | Comportamento ja' gerenciado |

### Prioridade BAIXA — historico, sem acao

| ID | Acao |
|---|---|
| H-PT-02/03 | Manter status historico (superseded pelo Pacote 1) |

## Lições gerais (metodologia)

### Anti-incidente checklist (pra sub-exps futuros)

Antes de declarar `confirmada-empirica`:

1. [ ] Testado em datasets **REAIS** (Adult/TPC-H/etc), nao so' sinteticos?
2. [ ] N >= 5 datasets de fontes diferentes?
3. [ ] Comparado com sintetico mostrando ganho similar OU explicado por que difere?
4. [ ] Datasets sinteticos **explicitam** que foram "construidos pra
   testar" (vies declarado)?
5. [ ] Bytes absolutos relevantes (>= 5% real-world weighted)?

### Convencao sugerida pra roadmap-hipoteses.md

Adicionar **3 colunas** novas:
- `evidencia_realworld`: "Adult-1k, TPC-H-customer-5k" | "(none)" | "(via pipeline EXP-XXX)"
- `n_datasets_diversos`: numero (sinteticos contam separado)
- `confianca`: Alta | Media | Baixa | A-revalidar

### Convencao pra novos tickets (META-*)

No criterio de aceite, exigir:
- Datasets sinteticos **mais** datasets reais (≥1 cada)
- Threshold em % real-world weighted, nao sintetico isolado

Ja' aplicado em **META-ESCAPE-DEDUCTION** (que evitou welding desnecessario).

## Conexao com convencao YAML frontmatter (2026-05-21)

Nova convencao tickets `YAML frontmatter` (tickets/README.md §
recomendacao 2026-05-21) tem campos:
- `priority: P0..P3` — pra **priorizar re-testes urgentes (H-DA-01/06/10)**
  acima de novos pacotes
- `blocked-by: [TICKET-XYZ]` — pra **bloquear novos pacotes ate'
  re-validar hipoteses dependentes**

Recomendacao: usar `blocked-by` em qualquer novo ticket que depende de
H-DA-01/06/10 — forca re-teste ate' decisao final.

## Resultados revalidacao 2026-05-21

**Lab**: `2026-05-21-revalidacao-categoria-B/` (ticket T-REVAL-H-DA-01-06-10)

**Sub-exps executados**:

### Sub-exp 01 — H-DA-06: SUBSUMIDA confirmada

`01-h-da-06-subsumida-em-09b-v2/`

Inspecao de detect_cadence (welded EXP-010) em Adult Census + TPC-H:
- 26 colunas numericas total
- 7 disparam regra 2 (numeric high-cardinality) = H-DA-09b-v2
- **Cobertura sobre numeric+high-card: 7/8 (87.5%)**
- Unica nao-coberta: `tpch.lineitem-5k/l_partkey` (card=0.366 < 0.5 threshold)
- Numericas que nao disparam sao low-card (age, education-num) — NAO eram alvo de H-DA-06

**Veredito**: H-DA-06 (numeric IDs delta) ja' e' capturada por
H-DA-09b-v2 em real-world. Marcar como `subsumida em H-DA-09b-v2 (ADR-0008)`.

### Sub-exp 02 — H-DA-01: MARGINAL real-world

`02-h-da-01-hcc-seqrle-realworld/`

Medicao isolada (M8AVirtualRefsSyntax baseline vs HCCSeqRLE tratamento):
- Sintetico D11a-h: **-22.23%** (reproduz original)
- Real-world (Adult + TPC-H): **-1.36% weighted**
- **Reducao sintetico → real-world: 16.3x**

MAS comportamento heterogeneo:
- `tpch.customer-5k/c_custkey`: **-91.94%** (7,257 bytes salvos!)
- `tpch.customer-5k/c_name`: **-44.18%** (6,237 bytes)
- `tpch.lineitem-5k/l_orderkey`: -4.14%
- Resto: ~0% ou regressao marginal

**Veredito**: Mesmo padrao do Pacote 2 (sintetico nao generaliza), MAS
nao e' refutada total — funciona dramaticamente em colunas com cadencia
estrutural (IDs sequenciais com prefixo, nomes formatados). Real-world
weighted 1.36% < 5% threshold, mas o detector ja' esta welded e ativacao
e' condicional ao auto-detect (gated por H-DA-09b-v2).

Marcar como `confirmada-empirica-marginal`. Confianca: A-revalidar
(se for ortogonal vs gating do auto-detect).

### Sub-exp 03 — H-DA-10: CONFIRMADA REAL-WORLD (inesperado)

`03-h-da-10-min-len-realworld/`

Varredura min_len ∈ {2,3,4,5,6} em D9 + Adult + TPC-H:
- **58 colunas testadas**
- **14 colunas com ganho >= 2%** se min_len != 3 (default)
- **9.92% bytes weighted economizados** (100,024 / 1,008,161)
- Top wins:
  - `adult-5000/fnlwgt`: ml=6, **-36.78%**
  - `tpch.lineitem-5k/l_extendedprice`: ml=6, **-28.05%**
  - `tpch.lineitem-5k/l_comment`: ml=6, **-18.18%**
  - `tpch.customer-5k/c_acctbal`: ml=5, **-15.79%**
  - `adult-1000/fnlwgt`: ml=5, **-14.28%**

Padrao identificado:
- Strings longas (comments, fnlwgt): ml=6 otimo
- Medias (phone, acctbal): ml=5 otimo
- IDs (orderkey, partkey): ml=4 otimo

**Veredito**: H-DA-10 NAO refutou — pelo contrario, generalizou MELHOR
que sintetico. Lição: amostra pequena pode tanto subestimar quanto
superestimar; nao podemos predizer direcao do erro sem teste empirico.

Marcar como `confirmada-empirica real-world`. Confianca: Alta.

Hipotese decorrente: **H-DA-11 — auto-detect min_len por coluna**
(candidata a sub-exp futuro; ~10% ganho potencial weighted real-world).

## Lições adicionais (apos revalidacao)

### 1. Amostra pequena erra em AMBAS as direcoes

Pacote 2 (escape deduction): sintetico SUPERESTIMOU real-world (15.7% → 1.13%).
H-DA-10 (min_len): sintetico SUBESTIMOU real-world (D9=-33B → 9.92% weighted).

**Implicacao**: nao podemos predizer direcao do erro sem teste. Anti-incidente
checklist do CLAUDE.md (5 perguntas) deve ser aplicado tanto pra ganhos
"muito altos" (suspeita de overfitting) quanto pra ganhos "marginais"
(suspeita de subutilizacao).

### 2. Subsumir antes de welding e' bom

H-DA-06 subsumida em H-DA-09b-v2 mostra que **regras mais gerais
(numeric+cardinality) podem absorver casos especificos** (IDs
sequenciais) sem perda de cobertura. Antes de welding nova feature,
verificar se feature ja' existente generaliza pra cobrir o novo caso.

### 3. Real-world weighted dilui ganhos seletivos

H-DA-01 mostrou que ganhos dramaticos em colunas especificas (c_custkey
-92%) podem ficar invisiveis em metrica weighted (1.36%). Reportar
ambos:
- Weighted (decisao economica: "vale a pena ativar always-on?")
- Por coluna (decisao tecnica: "em quais cenarios vale a pena ativar?")

Solucao: gating condicional via auto-detect (ja' feito em EXP-010).

## Status final categorizacao 2026-05-21 (pos-revalidacao)

| ID | Status final | Confianca |
|---|---|---|
| H-DA-01 | confirmada-empirica-marginal | A-revalidar (gating auto-detect) |
| H-DA-06 | subsumida em H-DA-09b-v2 | Alta |
| H-DA-10 | confirmada-empirica real-world | **Alta** |
| H-DA-11 | aberta (decorrente) | — |

## Proximos passos

1. ✅ Ticket T-REVAL-H-DA-01-06-10 criado (YAML frontmatter)
2. ✅ Sub-exps 01-03 executados
3. ✅ Roadmap-hipoteses.md atualizado com status final
4. ✅ Esta revisao atualizada com resultados
5. ✅ **H-DA-11 executada (2026-05-22, ticket T-EXP-H-DA-11)**:
   heuristica v3 (decision tree shallow) captura **9.87% weighted =
   99.5% do oracle**. Candidato welding ADR-0010.
6. **Pendente**: ADR-0010 + welding H-DA-11 em src/tcf/encoder.py
7. **Pendente**: avaliar H-DA-07 (categoria B nao revalidada)

## See also

- [Roadmap hipoteses](roadmap-hipoteses.md)
- [Pacote 2 closed (incidente motivador)](../2026-05-21-escape-deduction/)
- [META-ESCAPE-DEDUCTION ticket](../../../../tickets/META-ESCAPE-DEDUCTION.md)
- [CLAUDE.md raiz](../../../../CLAUDE.md) (anti-incidente checklist)
