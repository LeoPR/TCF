---
title: Testes combinatoriais do shaper (pairwise + edge cases)
type: task
status: OPEN
priority: 21
parent: 12-M-dataset-shaper
---

# Combined Tests

## Objetivo

Validar que combinacoes de dimensoes funcionam juntas sem conflitos.
Usar pairwise testing (cada par de dimensoes testado pelo menos uma vez).

## Dimensoes a combinar

1. volume (None, 0, 10, 0.01, 0.5, 1.0)
2. schema (minimal, core, chain, full, custom)
3. join_level (normalized, flat)
4. order (natural, random, sorted:col, reverse:col)
5. stratify_by (None, categorica)
6. compressibility_range (None, (0,0.3), (0.7,1.0))

## Pairwise coverage

Nao testar todas as 6^6 combinacoes (46K+). Usar pairwise:
cada par de valores de qualquer 2 dimensoes aparece pelo menos 1 vez.
Tipicamente ~20-30 test cases cobrem tudo.

Ferramenta: gerar manualmente ou usar `allpairspy` (pip).

## Edge cases criticos

- volume=0 + stratify → vazio (nao da pra estratificar)
- flat + schema=minimal → flat sem efeito
- compressibility=(0.99, 1.0) + volume=0.01 → pode retornar 0 rows
- stratify + compressibility → filter primeiro, depois estratifica
- sorted:col_inexistente → warning, nao crash

## Invariantes em TODOS os testes

1. Resultado nunca tem mais rows que pedido
2. Trace nao esta vazio
3. Mesma request + seed → mesma saida (determinismo)
4. stats.rows_after <= stats.rows_before

## Tarefas

- [ ] Gerar matriz pairwise (~25 combinacoes)
- [ ] Implementar cada combinacao como test case
- [ ] Testar edge cases criticos (listados acima)
- [ ] Verificar invariantes em todos os testes
- [ ] Rodar contra Adult e TPC-H
