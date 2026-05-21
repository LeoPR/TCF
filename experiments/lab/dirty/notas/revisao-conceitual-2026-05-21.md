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
  - tickets/META-ESCAPE-DEDUCTION.md
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

### Categoria B — NAO TESTADA real-world ⚠ (risco)

| ID | Hipotese | Datasets testados | Suspeita real-world |
|---|---|---|---|
| **H-DA-01** | OBAT+HCC quase pronto (-22.2%) | D11a-h **construidos digit-dominant** | Provavel ganho menor real-world. **Possivelmente ja' coberto** pela aplicacao no pipeline EXP-010 validado real-world |
| **H-DA-06** | Numericos delta IDs (-61%) | D16a-c **criados** pelo autor, N=3 | **Possivelmente coberto por H-DA-09b-v2** (numeric+high-card capturou `fnlwgt`/`*key` em Adult+TPC-H). Re-teste isolado pode mostrar redundancia |
| **H-DA-07** | OBAT shape-preserve | D11+D16 sinteticos; +17% em D1-D9 (regressao!) | **Condicional ja' documentada**. Gerenciada via auto-pre detect_cadence. Generalizacao adequada |
| **H-DA-10** | min_len trade-off | **N=3 datasets, N=4 valores** | Amostra muito pequena. Sem teoria. **Risco alto de nao generalizar** |
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

## Proximos passos sugeridos

1. **Criar ticket `T-REVAL-H-DA-01-06-10`** com nova convencao YAML,
   priority P1
2. **Sub-exp** medindo isoladamente em Adult+TPC-H
3. Atualizar roadmap-hipoteses.md com colunas `evidencia_realworld`,
   `n_datasets_diversos`, `confianca`
4. Atualizar CLAUDE.md "Antes de declarar confirmada-empirica" checklist
5. Considerar fechamento explicito de H-DA-06 como `subsumida-em-H-DA-09b-v2`
   se inspecao mostrar redundancia

## See also

- [Roadmap hipoteses](roadmap-hipoteses.md)
- [Pacote 2 closed (incidente motivador)](../2026-05-21-escape-deduction/)
- [META-ESCAPE-DEDUCTION ticket](../../../../tickets/META-ESCAPE-DEDUCTION.md)
- [CLAUDE.md raiz](../../../../CLAUDE.md) (anti-incidente checklist)
