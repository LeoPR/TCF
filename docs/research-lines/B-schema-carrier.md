---
title: Linha B — TCF como schema carrier para geração de SQL
date: 2026-04-23
type: research-line
status: ATIVO — M8 (modelos comerciais) e safe-sql flags pendentes
---

# Linha B — TCF como schema carrier + LLM gera SQL + SQLite executa

## Tese (H-TCF2)

Em vez de pedir ao LLM que **calcule** a resposta lendo os dados, pedir que ele
**descreva a operação** via SQL. TCF fornece o schema compacto (tabelas, colunas,
FK, cardinalidades), o LLM gera SQL, e o SQLite executa com precisão exata.

Isso **inverte o problema**: TCF não precisa ser legível linha a linha; precisa
ser um schema carrier eficiente.

## Paradigma de avaliação

```
Pergunta NL + schema TCF → LLM → SQL string
                                   ↓
                           SQLite.execute(SQL)
                                   ↓
                  comparar resultado com ground-truth
```

O LLM gera apenas a operação. O cálculo é feito pelo SQLite, que não erra
aritmética.

## Experimentos nesta linha

| Experimento | Objetivo | N combos | Manifest |
|-------------|---------|---------|----------|
| M1 | Baseline H-TCF2 — schema carrier vs full data | 189 | `m1_codegen` |
| M2 | Ablação few-shot + scale invariance | 945 | `m2_codegen` |
| M3 | Generalização cross-domain (retail, medical, financial) | 189 | `m3_crossdomain` |
| M4 | TCF vs JSON vs CSV como schema carrier | 567 | `m4_baseline` |
| M5 | SQL vs Pandas vs Polars vs CoT-SQL | 1260 | `m5_intermediate` |
| M6 | Perguntas L2 (WHERE/HAVING/GROUP-BY) | 108 | `m6_filter` |
| M6b | Fix HAVING via subquery fewshot | 27 | `m6b_having_fix` |
| M7 | Perguntas L3 (subquery/CTE/COUNT DISTINCT) | 81 | `m7_complex` |
| M_inv | Análise post-hoc de invariantes sobre falhas | — | (análise) |
| M8 | Safe-SQL flags isolados (ablação de style hints) | 405 | `m8_safe_sql` |
| M8b | Safe-SQL flags combinados (test de composicionalidade) | 405 | `m8b_safe_sql_combos` |
| M9 | Pipeline B: protocolo M3 em TPC-H canonical | 63 | `m9_canonical` |

## Achados canônicos desta linha

| F-Q | Conclusão |
|-----|-----------|
| F-Q13 | Schema-only prompt supera data-full para code generation |
| F-Q14 | SQL gerado é scale-invariant por construção (SQLite não depende do contexto) |
| F-Q15 | Few-shot elimina alucinação de schema |
| F-Q16 | SQL generation generaliza across unrelated domains (retail, medical, financial) |
| F-Q17 | TCF ≈ JSON > CSV para schema carrier; FK explícito é o diferencial |
| F-Q18 | SQL supera Pandas e Polars; CoT-SQL não adiciona accuracy |
| F-Q19 | HAVING com agregação aninhada falha universalmente em modelos 7-14B (fix via subquery fewshot) |
| F-Q20 | Queries L3 (CTE/subquery) atingem 86% com fewshot adequado |
| F-Q21 | Falhas SQL se dividem em detectáveis (21%) e silenciosas (79%) |
| F-Q22 | Style hints recuperam falhas zero-shot (+70pp em q_having); flags têm interferência off-target |
| F-Q23 | Style hints SQL não são composicionais; 11 de 12 combinações ficam abaixo do modelo aditivo |
| F-Q24 | Canonical TPC-H e synthetic produzem accuracy equivalente (100% tie-aware vs 96% synthetic) |

## Níveis de complexidade SQL testados

| Nível | Padrão | Accuracy global |
|-------|--------|----------------|
| L1 | COUNT/SUM/AVG/MAX, simple JOIN | ~95% |
| L2 | WHERE filter, GROUP BY + HAVING | 100% (exceto HAVING sem fix) |
| L3 | CTE + subquery, COUNT DISTINCT GROUP BY, nested subquery | 86% |

## Padrões de falha identificados

1. **HAVING scope confusion (F-Q19):** modelo gera `COUNT(DISTINCT fk) GROUP BY fk HAVING ...` (retorna 1 por grupo). Fix: fewshot de subquery (7%→89%)
2. **Coluna errada em subquery (F-Q20):** qwen2.5-coder usa `SELECT id FROM t` quando deveria ser `SELECT id_paciente FROM t`
3. **ID vs nome (F-Q17, F-Q20):** retorna FK numérico quando deveria fazer JOIN para nome da entidade
4. **FK naming collision (F-Q17):** label da entidade = nome de coluna em dim table → `t.titular` erro

## Hipóteses ativas para Linha B

| ID | Hipótese | Status |
|----|----------|--------|
| `--safe-sql-*` | Style hints recuperam zero-shot (M8 validou); flags têm interferência | F-Q22 |
| M_inv + invariant check | Detectar falhas via invariantes matemáticos embutidos | [nota](../research-notes/2026-04-23-embedded-query-invariants.md) |
| M8 | Modelos comerciais (Claude, GPT-4o) — quebrar teto de L3? | Pendente |
| M9 | Mais domínios (healthcare, logistics) para CI estreito | Pendente |

## Ver também

- [A-direct-reasoning.md](A-direct-reasoning.md) — linha antecessora (motivação)
- [../methodology/F-findings.md](../methodology/F-findings.md) — achados com tag `{B}`
- [../methodology/model-ranking.md](../methodology/model-ranking.md) — ranking dos modelos nesta linha
- [../FINDINGS_SUMMARY.md](../FINDINGS_SUMMARY.md) — achados principais A1-A6
- `experiments/results/sql_samples/` — padrões SQL gerados (apêndice de prova)
