---
title: Sub-exp 01 — Reproducao minima do bug `,` em literais
type: sub-experiment
status: active
tags: [tcf, bug, hcc, canonical, parser, comma, reproduction]
created: 2026-05-19
updated: 2026-05-19
parent: 2026-05-18-canonical-parser-robustness
hypothesis: pre-requisito pra H-FIX-01/02/03 (precisa mapear o bug primeiro)
---

# Sub-exp 01 — Reproducao minima

## Objetivo

Identificar EXATAMENTE quais conjuntos de strings reproduzem o bug
`,` em literais com **OBAT + HCC canonical** (src/tcf intocado).

Saber o caso minimo permite:
- Validar que opcoes A/B/etc. corrigem
- Adicionar regression test
- Documentar conditions especificas no ADR-0007

## Casos a testar

Progressao do mais simples ao mais complexo:

| # | Caso | Strings | Hipotese |
|---|---|---|---|
| 1 | Comma sozinho | `["a,b"]` | Caso minimo absoluto |
| 2 | Comma no inicio | `[",abc"]` | Lit comeca com `,` |
| 3 | Comma no fim | `["abc,"]` | Lit termina com `,` |
| 4 | Multiplas commas | `["a,b,c"]` | Varios commas |
| 5 | Prefixo + comma | `["abc", "abc,def"]` | HCC cria ref prefix |
| 6 | Sufixo + comma | `["xyz", "abc,xyz"]` | HCC cria ref suf |
| 7 | Pref+lit+suf | `["abc...xyz", "abc,def,xyz"]` | Triplo split |
| 8 | TPC-H pathological | extraido da p_comment row 328 | Caso real |

Pra cada: encoda via canonical, decoda, compara, documenta body.

## Execucao

`python run.py` produz:
- Tabela summary (caso, RT pass/fail, body line)
- `result.md` com analise

## Aceite

- Pelo menos 1 caso falha (caso contrario o bug nao existe como descrito)
- Body line do caso falho documentado
- Conditions especificas identificadas (qual sequencia de pieces gera o bug)

## See also

- [ADR-0007 DRAFT](../../../../docs/adr/0007-comma-in-literals-bug.md)
- [EXP-013](../../../clean/EXP-013-real-world-tpch/) onde bug apareceu
