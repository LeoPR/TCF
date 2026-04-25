---
title: Plano-mestre de validação em profundidade — checklist consolidado
date: 2026-04-25
type: research-note
status: ROADMAP — ordem para execução progressiva
---

# Plano-mestre de validação em profundidade

## Princípio

**Duvidar dos resultados existentes.** Achados M1-M9 foram obtidos com:
- 3 seeds (subamostragem ainda larga)
- Synthetic em maior parte
- Single-language (PT)
- Sem stratification metrics registradas
- SQL avaliado por funcional, não por qualidade
- Single-format (TCF + CSV/JSON via M4)
- Sem modelos comerciais

**O paper precisa de redundância demonstrada.** Para cada achado F-Q*,
queremos:
1. Múltiplas variações de seed (LLM + extração)
2. Múltiplas perspectivas (synthetic + canonical)
3. Múltiplas dimensões (idioma, formato, modelo, escala)
4. Métricas de representatividade (TVD, chi2 — F-Q25 estabeleceu padrão)
5. Métricas de qualidade SQL (não só "executa" — "está bem escrito?")

Este documento consolida **o que falta** + **o que refazer com novas
perspectivas**, em ordem priorizada.

---

## Inventário consolidado

### O que JÁ FOI feito (mas com perspectivas limitadas)

| ID | Combos | Seeds | Datasets | Formato | Idioma | Stratify | Quality SQL |
|----|--------|-------|----------|---------|--------|----------|-------------|
| M0 | qualificação | 5 | — | — | PT/EN | — | — |
| M1 | 21 | 3 | retail synthetic | TCF | PT | não | não |
| M2 | 945 | 3 | retail synthetic | TCF | PT | não | não |
| M3 | 189 | 3 | 3 synth domains | TCF | PT | não | não |
| M4 | 567 | 3 | 3 synth domains | CSV/JSON/TCF | PT | não | não |
| M5 | 1260 | 5 | 3 synth domains | TCF | PT | não | parcial (sql_quality.py existe mas underused) |
| M6 | 108 | 3 | 3 synth domains | TCF | PT | não | não |
| M6b | 27 | 3 | 3 synth domains | TCF | PT | não | não |
| M7 | 81 | 3 | 3 synth domains | TCF | PT | não | não |
| M8 | 405 | 3 | 3 synth domains | TCF | PT | não | não |
| M8b | 405 | 3 | 3 synth domains | TCF | PT | não | não |
| M9 | 63 | 3 | TPC-H | TCF | PT | não | não |
| **M9-Adult** | 63 | 3 | Adult | TCF | PT | **sim** (TVD=0.0007) | não |
| M_inv | post-hoc | — | M6/M7 | TCF | PT | n/a | n/a |

**Tudo em PT, tudo synthetic em maior parte, todos com 3 seeds, todos sem stratify_by, todos sem quality SQL.**

### O que NUNCA FOI feito (gaps)

#### Pendentes de alta prioridade

1. **M-strat** — random vs stratified sampling: efeito em accuracy
2. **M-quality** — qualidade do SQL gerado (otimização, não só funcional)
3. **M-lang** — variações de idioma (EN data, EN prompts, mixed)
4. **M-comp** — efeito do nível TCF (L0/L1/L2/L3) na accuracy LLM
5. **M8-commercial** — Claude Haiku/Sonnet, GPT-4o-mini/4o, Gemini Flash

#### Pendentes de média prioridade

6. **M10-graph** — notação de grafo (DOT/Mermaid) para FK do schema
7. **M-format-extended** — TOON em Linha B; Markdown-KV; HTML+explanations
8. **M-volume-scaling** — accuracy vs scale (50/200/1000/5000) sistemático
9. **M_inv-canonical** — invariant analysis sobre M9 + M9-Adult manifests

#### Pendentes de baixa prioridade (post-paper)

10. **M-paraphrase** — robustez a paráfrases das mesmas perguntas
11. **M-noise** — null rate alto (30-50%) em synthetic
12. **M-perf** — benchmark de timing dedicado (3 réplicas, isolated)

---

## Ordem proposta de execução

### Fase A — Pendentes diretos (próximas 2 semanas)

**Critério:** novos experimentos pequenos que destravam outras coisas.

| Ordem | Experimento | Combos | ETA | Bloqueia |
|-------|-------------|--------|-----|----------|
| **A1** | **M-strat** | 1 dataset × 3 modelos × 7 q × 5 seeds × 2 modos = 210 | ~30min | nada |
| A2 | M_inv-canonical | post-hoc | ~30min eng | F-Q21 update |
| A3 | M-quality | post-hoc sobre manifests existentes | ~1h eng | F-Q22/Q23 update |
| A4 | M-comp | 4 níveis × 3 modelos × 7 q × 3 seeds = 252 | ~45min | F-Q17 update |

**Após Fase A:** todos os achados existentes terão métricas de qualidade SQL adicionadas; M-strat valida hipótese de variância.

### Fase B — Multi-language (próximas 2-3 semanas)

| Ordem | Experimento | Combos | ETA |
|-------|-------------|--------|-----|
| B1 | **M-lang-EN-prompt** | M3 com prompts EN | 189 ~30min |
| B2 | **M-lang-EN-data** | adicionar dataset EN-only (Northwind) | 63 ~15min |
| B3 | **M-lang-mixed** | dados EN + prompts PT | 189 ~30min |

**Após Fase B:** F-Q3 (PT≈EN) reafirmado em Linha B com canonical.

### Fase C — Format extension (3-4 semanas)

| Ordem | Experimento | Combos | ETA |
|-------|-------------|--------|-----|
| C1 | **M4-canonical-TOON** | TOON em Linha B sobre canonical | ~189 ~40min |
| C2 | **M4-extended** | + Markdown-KV + HTML+explanations | ~189 × 2 |
| C3 | **M10-graph** | DOT/Mermaid notation variants | ~189 |

**Após Fase C:** lacunas da literatura preenchidas (TOON em Linha B é finding original).

### Fase D — Modelos comerciais (4-5 semanas)

| Ordem | Experimento | Combos | Custo |
|-------|-------------|--------|-------|
| D1 | **M8-commercial-cheap** | Claude Haiku + GPT-4o-mini em M3 protocol | 126 | ~$2 |
| D2 | **M8-commercial-pro** | Claude Sonnet + GPT-4o em M3 + M9 + M9-Adult | 252 | ~$30 |
| D3 | **M-having-commercial** | F-Q19 (HAVING) em comercial | 27 | ~$5 |

**Após Fase D:** credibilidade do paper com modelos state-of-the-art.

### Fase E — Re-execução completa em escala (5-7 semanas)

**Critério:** consolidação final antes do paper.

| Ordem | Experimento | O que muda |
|-------|-------------|-----------|
| E1 | **Re-M3** | 5 seeds, canonical, multi-format, quality SQL, stratify | múltiplas dimensões |
| E2 | **Re-M5** | 5 seeds, canonical, quality SQL | dimensão extra |
| E3 | **Re-M6b** | canonical TPC-H + Adult com HAVING |
| E4 | **Re-M7** | canonical, com quality SQL |
| E5 | **Re-M8/M8b** | canonical, comercial, quality SQL |

**Após Fase E:** todos os achados validados em pelo menos 2 datasets, 5 seeds, com métricas completas.

### Fase F — Análise final (paper)

| Ordem | Item |
|-------|------|
| F1 | Compilar tabelas finais consolidando F-Q1..F-Q25+ |
| F2 | Pareto plots: accuracy × tokens × latency |
| F3 | Ablation tables: cada dimensão isoladamente |
| F4 | Threats to validity (synthetic vs canonical, modelos, idioma) |
| F5 | Paper draft completo |

---

## Detalhamento dos experimentos pendentes (Fase A prioritária)

### A1 — M-strat: efeito de stratification em accuracy

**Hipótese:** sampling estratificado vs aleatório produz **mesma accuracy
em média** mas com **variância inter-seed menor**.

**Design:**
- Adult Census (best testbed: 2 classes, distribuição 76/24)
- 3 modelos × 7 questions × 2 modos (random / stratify) × 5 seeds = 210 combos
- Variável principal: accuracy
- Variável secundária: variância inter-seed

**Métricas a coletar:**
- Accuracy global e por question
- Wilson CI da accuracy
- Stratification metrics (TVD/JSD/chi2_p) quando stratified
- Variância inter-seed por (modo, question)

**Hipóteses testáveis:**
- H1: mean_acc(stratified) ≈ mean_acc(random) → confirma F-Q25 não foi sorte
- H2: std_acc(stratified) < std_acc(random) → confirma stratification dá CI mais estreito
- H3: questions sensíveis a balanceamento (q_count_high_class) têm comportamento diferente

**Custo:** ~30min compute, low risk.

### A2 — M_inv-canonical: invariant analysis sobre canonical

**Reuso:** `experiments/eval/run_minv_invariant_check.py` adaptado para
manifests M9 + M9-Adult.

**Esperado:** taxa de detecção (Type A vs B) similar a F-Q21 (21% / 79%)
mas em dados reais.

### A3 — M-quality: qualidade SQL (não só accuracy)

**Reuso:** `experiments/eval/llm_eval/sql_quality.py` (existe! mas underused).

**Métricas existentes:**
- has_explicit_join, join_uses_on, no_select_star
- single_result_col, tables_exist
- has_subquery, has_cte
- token_count
- composite score [0,1]

**Aplicação:**
- Rodar score() sobre TODOS os manifests existentes (M3, M4, M5, M6b, M7, M8, M8b, M9, M9-Adult)
- Cruzar com accuracy: SQLs corretas têm quality score mais alto?
- Identificar modelos que geram SQL "barato" vs "elegante"

**Resultado esperado (hipótese):** quality score **prediz** accuracy
mas não perfeitamente (algumas SQLs feias funcionam, algumas elegantes
falham).

**Não-objetivo:** não vamos rodar nova LLM. É post-hoc puro.

### A4 — M-comp: nível TCF afeta accuracy?

**Hipótese:** L0 (expanded) ≈ L2 (sort+rle) ≈ L3 (dict+sort+rle) em
accuracy LLM. **Compressão não custa accuracy**.

**Design:**
- Adult Census (mais simples)
- 4 níveis TCF × 3 modelos × 7 questions × 3 seeds = 252 combos
- Variável: accuracy
- Variável: tokens no prompt

**Resultado esperado:** L3 tem ~50% menos tokens que L0 com mesma accuracy.
Reafirma F-Q3/F-Q4 sobre token efficiency.

---

## Variáveis a varrer (matriz consolidada)

Para a re-execução final (Fase E), eis as dimensões:

| Dimensão | Valores |
|----------|---------|
| **Seed (extração)** | 5 valores: 42, 123, 7, 17, 99 |
| **Seed (LLM)** | mesmo seed do extraction (correlacionado por design) |
| **Stratify mode** | random / stratified |
| **Stratify column** | dataset-specific (class para Adult; default para outros) |
| **Volume** | 50, 100, 500, 1000 |
| **Schema complexity** | minimal/core/chain/full (Shaper) |
| **TCF level** | L0, L1, L2, L3 |
| **Format** | TCF, CSV, JSONL, TOON, Markdown-KV, HTML, schema-graph |
| **Language** | PT-prompt, EN-prompt, EN-data, mixed |
| **Model class** | local (qwen3, phi4, qwen2.5-coder), commercial (Claude, GPT-4o, Gemini) |
| **Question complexity** | L1 (count/sum), L2 (WHERE/HAVING), L3 (CTE/subquery) |
| **Safe-SQL mode** | none, having, subquery_col, name_join, explicit_fk, low, full |

**Combinatorial explosion:** todas as combinações dariam >1M combos.
Estratégia: factorial fracionado — varrer cada dimensão isoladamente
no design principal; combinar apenas onde há hipótese específica.

---

## Métricas a registrar em TODOS os manifests

A partir de Fase A, manifests devem incluir:

```json
{
  "key": "...",
  "phase": "...",
  "model": "...",
  "dataset": "...",
  "volume": 100,
  "seed": 42,
  "question": "...",
  "ok": true,

  // Já registramos
  "sql": "...",
  "executed_result": "...",
  "expected": "...",
  "reason": "...",
  "total_ms": 1234,
  "prompt_chars": 2659,

  // ADICIONAR:
  "stratification_metrics": { "tvd": ..., "chi2_p": ... },  // F-Q25 padrão
  "sql_quality": {
    "has_explicit_join": true,
    "no_select_star": true,
    "single_result_col": true,
    "has_subquery": false,
    "has_cte": false,
    "token_count": 18,
    "score": 0.85
  },
  "format_used": "tcf_L2",  // ou csv, json, toon, etc
  "language": "pt",  // ou en, mixed
  "safe_sql_flags": []  // lista quando aplicável
}
```

Manifest enriquecido permite análises cross-experiment com Wilson CI,
chi-square por dimensão, Pareto plots automatizados.

---

## CI e tolerâncias — política

Para cada finding F-Q*, reportar:

1. **Wilson 95% CI** sobre accuracy
2. **Variância inter-seed** (std)
3. **Chi-square comparando configurações** (significância de diferença)
4. **Tamanho de efeito** quando comparações múltiplas (Cohen's d ou similar)
5. **Tolerância**: diferença <2pp não é finding; 2-5pp é "consistente"; >5pp é "diferenciação"

Ferramentas:
- `experiments/eval/llm_eval/stats.py` (já tem Wilson + chi-square)
- `_stratify_metrics.py` (já tem TVD, JSD, etc.)
- Tabelas finais geradas via `analyze_results.py`

---

## Roadmap temporal high-level

| Semana | Foco |
|--------|------|
| 1 | Fase A (4 experimentos pendentes, post-hoc + 2 novos) |
| 2 | Fase B (multi-language) |
| 3 | Fase C (format extension) |
| 4-5 | Fase D (comerciais) |
| 5-6 | Fase E1-E3 (re-M3/M5/M6b) |
| 6-7 | Fase E4-E5 (re-M7/M8/M8b) |
| 7-8 | Fase F (paper draft) |

**Total:** ~8 semanas de trabalho focado para paper consolidado.

---

## Próxima ação concreta

**M-strat (A1)** — primeiro porque:
1. Estabelece padrão metodológico para próximas re-execuções
2. Valida que F-Q25 (Adult 100%) não foi sorte
3. Demonstra ganho concreto da stratification (variância)
4. ~30min de compute, post-hoc fácil

Após M-strat, decidir se atacar A2-A4 (post-hoc, sem nova LLM) ou ir direto para B/C/D (precisa LLM).

## Pontos de atenção

- **Não esperar tudo:** Fase A pode entregar F-Q26..F-Q30 sem rodar mais nada novo (só análise post-hoc)
- **Comerciais custam $:** D2 estimado em $30 — orçamentar
- **Não duplicar trabalho:** se um achado já tem 95%+ Wilson CI e múltiplas confirmações, parar de varrer
- **Paper-driven:** cada experimento deve responder pergunta específica que vai para o paper
