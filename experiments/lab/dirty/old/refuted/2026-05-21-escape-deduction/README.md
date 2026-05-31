---
title: 2026-05-21 — Escape deduction (Pacote 2 / H-ED-01..04) [CLOSED-INSUFFICIENT-GAIN]
type: dirty-lab
status: closed-insufficient-gain
priority: P2
tags: [hcc, escape-deduction, h-ed, pacote-2, suppressao, closed]
created: 2026-05-21
updated: 2026-05-21
closed: 2026-05-21
related:
  - tickets/META-ESCAPE-DEDUCTION.md
  - experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/11-escape-dedutivel/
  - docs/algorithms/HCC.md
---

# 2026-05-21 — Escape deduction (Pacote 2) — **CLOSED-INSUFFICIENT-GAIN**

**Conclusao 2026-05-21**: caracterizacao em real-world (Adult 1k/5k +
TPC-H region/customer/lineitem 5k, total 942kB body) mostrou ganho
maximo (H-ED-original lower bound) de **1.13%** — bem abaixo do
criterio de aceite 5%. Pacote 2 fechado sem prototipos de implementacao.

Aprendizado: sub-exp 11 antigo (T01) deu 15.7% em D11a-h porque
datasets eram "digit-dominant" construidos. **Nao generaliza pra
real-world**. Reforça importancia da revisao conceitual de hipoteses
`confirmada-empirica` em sinteticos.

Ver [ticket META-ESCAPE-DEDUCTION](../../../../tickets/META-ESCAPE-DEDUCTION.md)
pra updates datados + decisao.

**Ticket pai**: [META-ESCAPE-DEDUCTION](../../../../tickets/META-ESCAPE-DEDUCTION.md)
**Predecessor antigo**: [sub-exp 11 T01](../2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/11-escape-dedutivel/)
(prova de conceito em D11a-h, 15.7% ganho mas SOMENTE com 1 lit/linha)

## Pergunta cientifica

Em **datasets reais**, quanto da emit HCC final e' escape redundante
(deduzivel pelo decoder)? E qual variante (H-ED-01/02/03) captura
mais com menor complexidade?

## Sub-experimentos planejados

```
01-caracterizacao-escapes/   ← contar escapes deduziveis em D1-D9 + reais
02-prototipo-H-ED-01/        ← linha 1 sem escape (caso trivial)
03-prototipo-H-ED-02/        ← + apos *separator
04-prototipo-H-ED-03/        ← + escape de */~/\ contextual
05-decisao-welding/          ← se ganho >= 5% real-world
```

## Restricoes (NUNCA quebrar)

1. **D1-D9 = 1615B com decoder canonical** (M9 baseline). Smart
   encoder + smart decoder pareados podem ter bytes menores, MAS
   decoder canonical NAO PODE quebrar (= compat-break controlado).
2. **RT byte-canonical** end-to-end com smart encoder + smart decoder
3. **src/tcf intocado** ate' welding decidido em sub-exp 05

## Aceite

- Caracterizacao em 5 datasets reais (Adult Census 1k/5k + 3 TPC-H)
- Pelo menos 1 prototipo: byte loss reduzido em >= 5% real-world
- RT 100% encoder+decoder smart pareados
- Decisao welding com ADR

## See also

- [Ticket META-ESCAPE-DEDUCTION](../../../../tickets/META-ESCAPE-DEDUCTION.md)
- [Prova de conceito antiga](../2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/11-escape-dedutivel/)
- [HCC `_escape_lit`](../../../../src/tcf/composicional/syntax.py) (linha 52)
