---
title: 2026-05-20 — OBAT perf phase 2 — trigrama de meio (H-PERF-04) [ADIADO]
type: dirty-lab
status: closed-adiado
tags: [obat, performance, datetime, trigram, h-perf-04, adiado]
created: 2026-05-20
closed: 2026-05-20
related:
  - tickets/META-PERF-PHASE2.md
  - experiments/lab/dirty/2026-05-19-obat-perf-optimization/
  - docs/adr/0009-obat-trigram-index-optimization.md
  - experiments/lab/dirty/2026-05-20-hcc-perf-optimization/
---

# 2026-05-20 — OBAT perf phase 2 (H-PERF-04) — **ADIADO**

**Conclusao 2026-05-20**: hash tradicional **NAO PRESERVA byte-canonical**
em datas com prefix popular + LCP longo. Decidido opcao A: pausar e
focar em H-PERF-05 (HCC opt). Patricia trie fica como fallback futuro
se ganho de HCC nao for suficiente.

Sub-exp 01 (profile bucket sizes) executado e documentado — util como
caracterizacao do problema. Sub-exp 02 (prototipo) abortado apos analise
teorica mostrar inviabilidade.

Ver lab sucessor: [`2026-05-20-hcc-perf-optimization/`](../2026-05-20-hcc-perf-optimization/)

**Predecessor**: [Pacote 4 sub-pacote 1](../2026-05-19-obat-perf-optimization/) +
[ADR-0009](../../../../docs/adr/0009-obat-trigram-index-optimization.md)
(hash trigrama prefix/suffix, alpha 1.75→1.42).

## Pergunta cientifica

Hash trigrama atual reduziu encode 5.4x em colunas categoricas/numericas
mas **so' 2x em colunas datetime** (l_shipdate/commitdate/receiptdate).
Causa: trigrama inicial `199`/`200`/`202` gera buckets enormes.

**E' possivel dispersar melhor as datas via trigrama adicional
(middle ou combined key) preservando byte-canonical?**

## Plano (3 sub-experimentos)

```
01-profile-bucket-sizes/    ← caracterizar problema (distribuicao buckets)
02-prototipos-discriminative/ ← v4 candidates (middle / combined / multi-hash)
03-welding-decision/         ← validar + integrar se ganho >= 3x em datas
```

## Hipoteses

- **H-PERF-04a**: trigrama de meio `s[len(s)//2-1:len(s)//2+2]` dispersa
  buckets em datas. **Risco**: pra `2026-05-19`, `2026-05-20` o middle
  pode tambem ser identico — precisa profilar pra confirmar.
- **H-PERF-04b** (alternativa): combined key `s[:3] + s[-3:]` (6-char)
  reduz colisao mantendo lookup O(1).
- **H-PERF-04c** (alternativa): multi-hash (prefix AND middle AND suffix,
  intersecao de candidatos). Risco: overhead de intersecao Python.

## Restricoes (NUNCA quebrar)

1. **D1-D9 = 1615B** (M9 baseline)
2. **RT 100%** em EXP-007/010/011/012/013/014
3. **Bytes IDENTICOS** em lineitem 1k/5k/10k/20k (regressao caso contrario)
4. **NAO degradar outras colunas** (categoricas devem manter ~100x speedup)

## Aceite

- Pelo menos 1 variante: speedup datetime 3x+ adicional SEM degradar outras cols
- Bytes IDENTICOS em todos testes
- ADR-0010 se welded

## See also

- [META-PERF-PHASE2](../../../../tickets/META-PERF-PHASE2.md)
- [Sub-pacote 1 (welded ADR-0009)](../2026-05-19-obat-perf-optimization/)
- [src/tcf/core/online.py](../../../../src/tcf/core/online.py) — alvo se welding
