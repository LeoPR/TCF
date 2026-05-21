---
title: T-REVAL-H-DA-01-06-10 — Revalidacao categoria B (Pacote 1 hipoteses confirmada-empirica nao testadas em real-world)
status: closed
resolution: completed-with-surprises
priority: P1
created: 2026-05-21
updated: 2026-05-21
closed: 2026-05-21
blocked-by: []
related:
  - experiments/lab/dirty/notas/revisao-conceitual-2026-05-21.md
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - experiments/lab/dirty/2026-05-17-OBAT-delta-aware/
  - experiments/lab/dirty/2026-05-21-revalidacao-categoria-B/
  - docs/adr/0008-detect-cadence-numeric-high-cardinality.md
---

# T-REVAL-H-DA-01-06-10 — Revalidacao Categoria B (Pacote 1)

## Contexto / motivacao

Revisao conceitual de 2026-05-21 (apos fechamento Pacote 2 como
CLOSED-INSUFFICIENT-GAIN) classificou hipoteses `confirmada-empirica`
em 3 categorias:
- **A**: generaliza real-world (Adult/TPC-H/lineitem testado)
- **B**: nao testada em real-world (risco generalizacao)
- **C**: refutada real-world (Pacote 2 H-ED-01..04)

Esta revalidacao foca **categoria B** — 3 hipoteses do Pacote 1
(delta-aware) que foram validadas APENAS em datasets sinteticos
(D11a-h ou D16a-c) que foram construidos pra testar a hipotese
(vies de selecao).

Risco identificado: incidente Pacote 2 mostrou que ganho sintetico
15.7% colapsou pra 0.13-1.13% em real-world (10-130x reducao).
Mesmo padrao pode estar latente em H-DA-01/06/10.

## Hipoteses sob revalidacao

### H-DA-06 — IDs numericos delta (-61% em D16a-c sinteticos)

**Suspeita**: Pode ja' estar **subsumida** em H-DA-09b-v2 (numeric
high-cardinality welded ADR-0008). Se o hint auto-detect ja' captura
colunas tipo D16 em real-world (Adult `fnlwgt`, TPC-H `*key`), H-DA-06
e' redundante.

**Acao**: inspecao isolada — rodar Adult Census + TPC-H pelo pipeline
EXP-010 e verificar quais colunas disparam hint via regra 2 (numeric
high-cardinality). Se cobertura suficiente → marcar H-DA-06 como
`subsumida` em H-DA-09b-v2.

### H-DA-01 — HCC seq-RLE near-identical (-22.2% em D11a-h sinteticos)

**Suspeita**: Datasets D11a-h sao **construidos** com cadencia
explicita (datetime regular). Real-world tem timestamps irregulares,
IDs nao-sequenciais, etc. Ganho pode cair drasticamente.

**Acao**: medir bytes em pipeline TCF (sem fork) vs pipeline + HCC
fork seq-RLE explicito em Adult Census + TPC-H. Quantificar ganho
adicional REAL-WORLD weighted.

### H-DA-10 — min_len trade-off (-33B em D9 sintetico, N=3)

**Suspeita**: Amostra muito pequena (3 datasets, 4 valores de min_len).
Sem teoria. Provavel ruido.

**Acao**: rodar min_len ∈ {3,4,5,6} em Adult Census + TPC-H. Avaliar
se min_len otimo difere de default (3) com ganho >=2%.

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-21-revalidacao-categoria-B/`

3 sub-exps:
1. `01-h-da-06-subsumida-em-09b-v2/` — inspecao isolada (rapido)
2. `02-h-da-01-hcc-seqrle-realworld/` — medicao isolamento real-world
3. `03-h-da-10-min-len-realworld/` — varredura min_len real-world

Cada sub-exp segue template do Pacote 2 (caracterizacao quantitativa
em D1-D9 + Adult-1k/5k + TPC-H region/customer/lineitem-5k).

## Criterio de aceite (KR-style)

### Por hipotese

| H | Acao no roadmap se |
|---|---|
| **H-DA-06** | Subsumida em H-DA-09b-v2: cobertura real-world >= 80% das colunas-alvo  |
| **H-DA-06** | A-revalidar: cobertura < 80%, ortogonal — manter como hipotese separada |
| **H-DA-01** | Confirmada real-world: ganho weighted >= 5% bytes |
| **H-DA-01** | Refutada-real-world: ganho < 1% (mesmo padrao Pacote 2) |
| **H-DA-01** | A-revalidar com ressalva: 1-5% (marginal) |
| **H-DA-10** | Confirmada real-world: pelo menos 1 min_len != 3 da >=2% em >=3 colunas |
| **H-DA-10** | Refutada: nenhum min_len bate o default em >=2% |

### Globais

- [ ] 3 sub-exps com result.md
- [ ] Roadmap atualizado com status final (incluindo 3 campos:
  evidencia_realworld, n_datasets_diversos, confianca)
- [ ] revisao-conceitual-2026-05-21.md atualizado (categoria B → A
  ou C)
- [ ] Commit unico por sub-exp ou consolidado

## Riscos

1. **H-DA-06 nao subsumida**: se Adult `fnlwgt` ou TPC-H keys nao
   disparam regra 2 (cardinalidade baixa, ou prefix nao-numerico),
   H-DA-06 ainda e' real. Manter aberta.
2. **H-DA-01 ganho real-world baixo**: confirma padrao Pacote 2 —
   sinteticos D11a-h enviesados. Fechar como refutada-real-world.
3. **H-DA-10 sem ganho**: confirma intuicao "amostra muito pequena
   pra confiar"; min_len=3 e' default razoavel.

## Conexoes

- [Revisao conceitual 2026-05-21](../experiments/lab/dirty/notas/revisao-conceitual-2026-05-21.md)
  — origem da categorizacao A/B/C
- [Pacote 1 lab](../experiments/lab/dirty/2026-05-17-OBAT-delta-aware/)
  — sub-exps 02, 05, 08 originais
- [ADR-0008](../docs/adr/0008-detect-cadence-numeric-high-cardinality.md)
  — H-DA-09b-v2 welded (possivelmente subsume H-DA-06)
- [META-ESCAPE-DEDUCTION](META-ESCAPE-DEDUCTION.md) — incidente
  Pacote 2 que motivou esta revalidacao

## Updates datados

### 2026-05-21 — abertura

Ticket criado seguindo convencao YAML frontmatter (validada em
META-ESCAPE-DEDUCTION). Priority P1 — desbloqueia confianca em
hipoteses Categoria B antes de novos pacotes. blocked-by: vazio
(nao depende de outro ticket; e' anterior a qualquer novo pacote).

### 2026-05-21 — execucao + fechamento

Lab dirty `2026-05-21-revalidacao-categoria-B/` executado integralmente
no mesmo dia. 3 sub-exps com result.md.

**Resultados (com surpresas)**:

| H | Predicao apriori | Resultado real-world |
|---|---|---|
| H-DA-06 | "Possivelmente subsumida" | **SUBSUMIDA confirmada** (cobertura 87.5%) |
| H-DA-01 | "Provavel ganho menor" | **MARGINAL** (1.36% weighted, 16.3x reducao vs sintetico) |
| H-DA-10 | "Risco alto de nao generalizar" | **CONFIRMADA inesperadamente** (9.92% weighted!!) |

**Surpresa principal**: H-DA-10 era a hipotese mais suspeita (N=3
datasets, N=4 valores, sem teoria) e foi a unica que cresceu em
real-world. Padrao reverso de Pacote 2 (que era hipotese mais "obvia"
e refutou).

**Licao meta**: amostra pequena erra em AMBAS as direcoes — nao
podemos predizer direcao do erro sem teste empirico. Anti-incidente
checklist do CLAUDE.md aplica tanto pra ganhos "muito altos" (suspeita
overfitting) quanto pra "marginais" (suspeita subutilizacao).

**Outputs**:
- 3 result.md em sub-exps
- roadmap-hipoteses.md atualizado (H-DA-01/06/10 status final + nova H-DA-11)
- revisao-conceitual-2026-05-21.md atualizada com secao "Resultados
  revalidacao"
- Nova hipotese decorrente: **H-DA-11** auto-detect min_len por coluna
  (candidata sub-exp ~10% ganho potencial)

**Resolution**: completed-with-surprises (todos KRs satisfeitos +
direcao final diferente do esperado pra 2 das 3 hipoteses).
