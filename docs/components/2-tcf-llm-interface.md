---
title: Componente 2 — TCF-LLM Interface
date: 2026-04-23
type: component
status: ATIVO — M-series em progresso, 23 achados canônicos
---

# 2. TCF-LLM Interface — usando TCF como veículo para LLM

## O que é

A *interface* entre TCF e LLM. Investiga como **pedir** ao LLM que responda
perguntas sobre dados tabulares representados em TCF. Engloba:

- Construção de prompts (schema + dados + pergunta)
- Estratégias de few-shot e style hints
- Formas de resposta (texto direto vs SQL vs código)
- Teoria de queries (o que é expressível e como)

## Duas abordagens (linhas de pesquisa)

O projeto testou duas teses sobre *como* usar TCF com LLM:

### Linha A — LLM como analista direto
```
TCF completo → LLM → resposta numérica/textual
```
LLM faz o cálculo lendo os dados. Teto ~60-70% (F-Q12).
Ver [../research-lines/A-direct-reasoning.md](../research-lines/A-direct-reasoning.md).

### Linha B — TCF como schema carrier + LLM gera SQL
```
Schema TCF + pergunta → LLM → SQL → SQLite → resposta
```
LLM traduz intenção em operação formal. Resultado: 86-100% (F-Q16..F-Q23).
Ver [../research-lines/B-schema-carrier.md](../research-lines/B-schema-carrier.md).

**Ambas são válidas cientificamente** — atacam problemas diferentes. Linha A
mostra o teto de modelos locais como calculadores; Linha B mostra TCF como
habilitador de text-to-SQL confiável.

## Capacidades atuais

| Capacidade | Estado | Exemplo |
|-----------|--------|---------|
| Prompt templates (schema/stats/full) | Estável | `build_payload_stats`, `build_payload_full` |
| Few-shot JOIN example | Estável | `FEWSHOT_BLOCK` (M2) |
| HAVING subquery fewshot | Validado | M6b fix: 7%→89% |
| Complex L3 fewshot (CTE, nested) | Validado | M7 fewshot |
| Style hints individuais (`safe-sql-*`) | Validado isolado | M8: `safe_having` +70pp |
| Combinações de style hints | **Contraindicado por padrão** | M8b: 11/12 combos regridem |
| Cross-domain generalization | Validado | M3: retail/medical/financial |
| Invariant checking post-hoc | Implementado | `run_minv_invariant_check.py` |

## Achados de alto impacto (Linha B)

Ver [../FINDINGS_SUMMARY.md](../FINDINGS_SUMMARY.md) para lista completa A1-A7.
Resumo:

1. **H-TCF2 confirmada** — schema carrier + SQL = 96%+ (F-Q13, F-Q16)
2. **Few-shot obrigatório** — sem exemplo de JOIN, accuracy ~0% (F-Q15)
3. **TCF ≈ JSON > CSV** para schema carrier (F-Q17)
4. **SQL >> Pandas >> Polars** para execução via LLM (F-Q18)
5. **HAVING é falha universal** resolvida por fewshot de subquery (F-Q19)
6. **Queries L3 atingem 86%** com fewshot adequado (F-Q20)
7. **Style hints não são composicionais** — agrupar flags degrada (F-Q22, F-Q23)

## Hipóteses abertas

### Teoria das queries (pré-SQL)

Investigar o que o LLM "pensa" antes de emitir SQL. Hipóteses:
- Perguntas expressáveis em SQL são um subconjunto de perguntas
  de BI; existe classe "não-expressível" detectável?
- Formas intermediárias (álgebra relacional, query algebra) podem
  ser mais robustas que SQL para modelos pequenos?
- Chain-of-thought com **plano estruturado** (não-SQL) antes do SQL
  ajuda, atrapalha ou é neutro? (M5 testou CoT-SQL, resultado: neutro/negativo)

Ver research-note:
[../research-notes/2026-04-23-query-theory.md](../research-notes/2026-04-23-query-theory.md)

### Router-based flag selection

F-Q23 mostrou que style hints não combinam. A hipótese natural é um
*router* que detecta o padrão de query e ativa só o hint alinhado:

```
pergunta → detectar padrão SQL esperado → ativar safe-sql-{específico}
```

Experimento M_router seria: implementar classificador simples de padrão
de query (via rule-based ou LLM auxiliar) e comparar com `all_flags` e com
flag individual correto.

### Modelos comerciais (M8)

Pendente — Claude Haiku/Sonnet, GPT-4o-mini/GPT-4o. Validar teto de Linha B
em modelos state-of-the-art. Crítico para credibilidade do paper.

## Código e experimentos

- Runners: `experiments/eval/run_m{1..8b}_*.py`
- Infra: `experiments/eval/llm_eval/`
- Resultados: `experiments/results/m{1..8b}_*/manifest.jsonl`
- Exemplos SQL: `experiments/results/sql_samples/` (apêndice fora da narrativa)

## Métricas e análise

- Stats: `llm_eval/stats.py` (Wilson CI, bootstrap, chi-square)
- SQL quality: `llm_eval/sql_quality.py` (structural scoring)
- Python execution: `llm_eval/python_executor.py` (Pandas/Polars sandbox)
- Análise unificada: `experiments/eval/analyze_results.py`

Ver [../methodology/experimental-design.md](../methodology/experimental-design.md)
para status M-series completo (M1-M8b + pendentes).
