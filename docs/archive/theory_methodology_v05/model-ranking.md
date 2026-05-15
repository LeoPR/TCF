---
title: Model Ranking — modelos locais testados no projeto TCF
date: 2026-04-23
type: methodology
status: LIVING DOCUMENT — atualizado com cada série M
---

# Model Ranking — modelos locais open-source

Ranking dos modelos testados no projeto, baseado em accuracy, latência e
comportamento por tipo de query. Todos os números vêm dos manifests M-series.

**Modelos no painel atual:** qwen3:14b, phi4:latest, qwen2.5-coder:7b
**Endpoint:** Ollama local (Docker), GPU VRAM

---

## Resumo executivo

| Modelo | Accuracy M3-M7 | Latência média | Perfil |
|--------|---------------|----------------|--------|
| **qwen3:14b** | **85.8%** (638/744) | **~6.4s** | Melhor equilíbrio accuracy+velocidade |
| **phi4:latest** | 84.5% (629/744) | ~13.7s | Bom em lookup/raciocínio; 2.1× mais lento |
| **qwen2.5-coder:7b** | 82.0% (610/744) | **~4.0s** | Mais rápido; fraco em subqueries complexas |

**Recomendação:**
- **Experimentos gerais:** qwen3:14b (melhor accuracy, velocidade razoável)
- **Throughput alto / muitos combos:** qwen2.5-coder:7b (queries L1-L2 apenas)
- **Queries de lookup/raciocínio:** phi4:latest ou qwen3:14b

---

## Breakdown por tipo de query (SQL complexity level)

### L1 — Aggregation simples (M3, M5)

| Question | qwen3:14b | phi4 | qwen2.5-coder |
|---------|-----------|------|---------------|
| q_count | 100% (69/69) | 100% | 100% |
| q_sum | 100% (69/69) | 100% | 100% |
| q_avg | 86% (59/69) | **100%** | **100%** |
| q_distinct | 64% (44/69) | 61% | 61% |
| q_lookup | 57% (39/69) | **71%** | 45% |

**Observação:** `q_distinct` baixo em todos por colisão de nome FK no domínio
financial ("titular" label = nome de coluna em `contas`). Ver F-Q17.
`q_lookup` é onde phi4 se destaca — melhor raciocínio sobre casos específicos.
qwen2.5-coder:7b tem q_lookup mais fraco (45%) apesar de ser um modelo de código.

### L2 — WHERE/HAVING/GROUP-BY (M6, M6b)

| Question | qwen3:14b | phi4 | qwen2.5-coder | Nota |
|---------|-----------|------|---------------|------|
| q_filter_month | 100% (9/9) | 100% | 100% | STRFTIME + WHERE |
| q_filter_entity | 100% (9/9) | 100% | 100% | WHERE + JOIN |
| q_group_sum | 100% (9/9) | 100% | 100% | GROUP BY + SUM |
| q_having (M6, sem fix) | 0% (0/9) | 11% (1/9) | 11% (1/9) | F-Q19: scope confusion |
| q_having (M6b, com fix) | **100%** (9/9) | 67% (6/9) | **100%** (9/9) | Subquery fewshot |

**Observação:** `q_having` sem fewshot é falha universal. Com fewshot de subquery:
qwen3 e qwen2.5-coder chegam a 100%, phi4 para em 67% por bug FK no financial.

### L3 — Subquery/CTE/COUNT DISTINCT (M7)

| Question | qwen3:14b | phi4 | qwen2.5-coder | Padrão SQL |
|---------|-----------|------|---------------|-----------|
| q_above_avg | 100% (9/9) | 100% | 100% | CTE + avg filter |
| q_top_e1_best_e2 | **100%** (9/9) | **100%** | 33% (3/9) | subquery aninhada WHERE |
| q_e2_most_e1 | 89% (8/9) | 67% (6/9) | 89% (8/9) | COUNT DISTINCT GROUP BY |

**Observação:** qwen2.5-coder:7b **colapsa em subqueries aninhadas** (q_top_e1_best_e2: 33%) —
usa coluna errada na subquery interna. Para queries L3, qwen3:14b ou phi4 são
obrigatórios. qwen3:14b tem apenas 1 falha total em M7 (vs 3 phi4, 7 coder).

---

## Failure mode profile

| Modelo | Failure mode principal | Característica |
|--------|----------------------|----------------|
| qwen3:14b | q_distinct FK collision | Resistente a subqueries complexas |
| phi4:latest | q_having FK bug (financial), q_lookup lento mas preciso | Gera CTEs mais elaboradas mas às vezes erradas |
| qwen2.5-coder:7b | subquery coluna errada (L3), q_lookup fraco | Rápido e confiável para L1-L2; degrada em L3 |

---

## Latência por modelo (indicativo — single-run, não-isolado)

> ⚠️ Latências são `total_ms` server-side do Ollama — incluem possível
> `load_duration`. Ver [timing-measurement-methodology.md](../research-notes/2026-04-22-timing-measurement-methodology.md)
> para limitações. Use para comparações de ordem de grandeza (ratio > 1.5× confiável).

| Modelo | Média M3-M7 | Relativo |
|--------|------------|---------|
| qwen2.5-coder:7b | ~4.0s | 1.0× (base) |
| qwen3:14b | ~6.4s | 1.6× |
| phi4:latest | ~13.7s | 3.4× |

phi4 é **3.4× mais lento** que qwen2.5-coder. qwen3:14b paga ~1.6× pela
accuracy superior em queries complexas — tradeoff favorável para experiments.

---

## Recomendações por cenário

| Cenário | Modelo recomendado | Justificativa |
|---------|-------------------|---------------|
| Experimento geral (M-series) | **qwen3:14b** | Melhor accuracy em L1-L3, velocidade aceitável |
| Screening rápido (muitos combos) | **qwen2.5-coder:7b** | 4s/query, ótimo para L1-L2 |
| Queries de lookup / raciocínio | **phi4:latest** ou qwen3 | phi4 lidera em q_lookup (71%) |
| Queries L3 complexas | **qwen3:14b** | Único com 100% em q_top_e1_best_e2 |
| Paper — validação comercial | Claude Haiku/Sonnet, GPT-4o | M8 pendente |

---

## Sobre o painel atual

**Por que só 3 modelos?**
Estes foram os 3 sobreviventes do painel de qualificação M0 (2026-04-20):
threshold de compreensão básica (>50% em q_count/q_sum), sem thinking intrínseco
forçado, sem timeouts patológicos. Ver F-Q10..F-Q12 e
[qualification-findings.md](../research-notes/2026-04-20-qualification-findings.md).

**Modelos descartados no M0:** deepseek-r1:7b (thinking intrínseco), qwen3-vl:8b
(timeout patológico text-only), modelos < 1B (abaixo do capacity floor).

**Próxima expansão (M8):** Claude Haiku, Claude Sonnet, GPT-4o-mini, GPT-4o — para
credibilidade do paper com modelos comerciais state-of-the-art.
