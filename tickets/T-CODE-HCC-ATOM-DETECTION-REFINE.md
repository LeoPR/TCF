---
title: T-CODE-HCC-ATOM-DETECTION-REFINE — Bug #1 sub-exp 14 (atom secundario nao criado)
status: open
priority: P2
created: 2026-05-24
updated: 2026-05-24
blocked-by: []
related:
  - experiments/lab/dirty/2026-05-24-cpf-templated-checked/14-cross-subnet-investigation/report.md
  - src/tcf/composicional/syntax.py
  - docs/algorithms/HCC.md
  - tickets/T-CODE-HCC-MULTI-DELTA-FIX.md
---

# T-CODE-HCC-ATOM-DETECTION-REFINE — Bug #1: atom secundario nao criado

## Contexto

Sub-exp 14 (2026-05-24) identificou que HCC M8A composition detector
nao cria atom secundario para prefixes que aparecem >= 100x apos
detector ter criado atom primario.

Body M8A de D-IP-subnet n=200 (transicao subnet1 → subnet2):
```
   99: 1\98                  ← ref atom 1 = "\57.\12.\140."
  100: 1\99
  101: \125.\114.\71.\0      ← LITERAL completo (atom NAO criado)
  102: \125.\114.\71.\1
  ...
  200: \125.\114.\71.\99
```

Subnet 1 prefix (`\57.\12.\140.`) virou atom 1, usado 100x. Subnet 2
prefix (`\125.\114.\71.`) tambem aparece 100x mas atom 2 NAO foi
criado. Cada linha repete o prefix completo (~14 chars).

## Causa provavel

HCC composition detector eh **greedy iterativo** com criterio `net > 0`
por iteracao. Hipoteses:
- H-A: net <= 0 pra atom 2 (rejeitado por threshold)
- H-B: budget de iteracoes esgotado apos atom 1
- H-C: detector greedy nao revisa, atom 2 perdido em primeira passada

Confirmar empiricamente inspecionando hcc-trace.txt do sub-exp 14.

## Impacto

D-IP-subnet n=200:
- Body M8A: 100 linhas com prefix literal `\125.\114.\71.` (~14 chars)
  + 100 linhas com ref atom 1 (~4 chars)
- Total body: ~14*100 + 4*100 = 1800B
- M10 final: 1827B (ratio 68%)

Se atom 2 fosse criado, body subnet2 viraria `2\X` (3-4 chars), mesmo
perfil de subnet 1. Esperado: ~37B (similar a subnet 1 single em n=100).
**Speedup: ~50x.**

## Hipotese / Plano

### Fase 1 — Investigacao

Inspecionar hcc-trace.txt do sub-exp 14 n=200/500/1000:
- Quantas iteracoes detector rodou?
- Atom 2 foi considerado e rejeitado, ou nao considerado?
- Net calculado pra atom 2 era negativo?

### Fase 2 — Fix proposals

Dependendo da causa:
- **H-A (net rejeitado)**: revisar formula de net. Pra prefix curto +
  alta repeticao, fixed-cost de atom (`<N>=<template>` declaracao + refs)
  pode estar overestimado.
- **H-B (budget)**: aumentar iteracoes maximas do detector.
- **H-C (greedy miss)**: adicionar segunda passada ou backtrack.

### Fase 3 — Validacao

- Real-world Adult+TPC-H: zero regressao
- D-IP-subnet: ratio melhora <10% (esperado)
- D1-D9 byte-canonical preservado

## Riscos

1. **Quebra M10 invariant** — qualquer mudanca em composition detector
   pode produzir diferentes atoms em D1-D9. Validar primeiro.
2. **Performance impact** — segunda passada ou backtrack pode aumentar
   tempo de encode (alpha vai pra mais que 1.42 atual).
3. **Cumulative com T-CODE-HCC-MULTI-DELTA-FIX** — se ambos fixed,
   ganho composto. Mas combinados aumentam risco.

## Relacao com T-CODE-HCC-MULTI-DELTA-FIX

Bugs **independentes mas com impacto similar**:
- Bug #1 (atom): cria atom secundario → subnet 2 vira `2\X` (4 chars)
- Bug #2 (multi-delta): aceita `[0,0,0,1]` → subnet 2 sem atom funciona
  como `*99+1|\125.\114.\71.\0`

**Cada fix isoladamente resolveria cross-subnet.** Fixar ambos eh
desnecessario; escolher o mais barato/seguro.

Comparacao:
- Bug #1 fix: mais invasivo (composition detector), risco maior canonical
- Bug #2 fix: mais localizado (compare_for_seq + shift), risco menor

**Recomendacao: priorizar T-CODE-HCC-MULTI-DELTA-FIX** sobre este.

## Criterio de aceite

- [ ] Causa identificada (H-A/B/C) via inspecao trace
- [ ] Fix com ADR
- [ ] D-IP-subnet ratio melhora
- [ ] RT byte-canonical D1-D9 preservado
- [ ] Tests + validacao real-world

## Conexao

- Sub-exp 14: [report.md](../experiments/lab/dirty/2026-05-24-cpf-templated-checked/14-cross-subnet-investigation/report.md)
- T-CODE-HCC-MULTI-DELTA-FIX (Bug #2 complementar)
- HCC.md, ADR-0011

## Updates datados

### 2026-05-24 — abertura

Ticket criado pos-sub-exp 14. Recomendacao: deferir vs
T-CODE-HCC-MULTI-DELTA-FIX que tem mesmo impacto com risco menor.
