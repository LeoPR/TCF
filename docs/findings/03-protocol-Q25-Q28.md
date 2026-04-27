---
title: Protocolo + canonical baseline (F-Q25..F-Q28)
type: findings-block
range: F-Q25..F-Q28
parent: docs/findings/README.md
---

# Protocolo + canonical baseline (F-Q25..F-Q28)

## F-Q25 `{B}` — H-TCF2 generaliza para single-table com colunas hifenadas e categóricos ricos

**Conclusão:** Aplicar o protocolo M9 (sql_stats_fs, 3 modelos locais) sobre
**Adult Census** (single-table, 14 colunas, mistura de numerics/categoricals,
nomes hifenados como `hours-per-week`, `education-num`) produz **63/63 =
100% de accuracy**, superando inclusive M9-TPCH (95.2% strict). Confirma
que o paradigma generaliza para datasets reais com convenções de naming
diferentes do retail synthetic.

**Evidência (M9-Adult, 2026-04-25):** 1 dataset Adult × 3 modelos × 7 questions
× 3 seeds = 63 combos. Stratify_by='class' garantiu representatividade
(TVD=0.0007, chi2_p=0.99 — distribuição idêntica à população).

| Question | qwen3:14b | phi4 | qwen2.5-coder | Acc |
|----------|----------|------|---------------|-----|
| q_count | 3/3 | 3/3 | 3/3 | 100% |
| q_avg_age | 3/3 | 3/3 | 3/3 | 100% |
| q_max_age | 3/3 | 3/3 | 3/3 | 100% |
| q_distinct_workclass | 3/3 | 3/3 | 3/3 | 100% |
| q_top_education | 3/3 | 3/3 | 3/3 | 100% |
| q_count_high_class (WHERE +COUNT) | 3/3 | 3/3 | 3/3 | 100% |
| q_avg_hours_male (WHERE +AVG hifenado) | 3/3 | 3/3 | 3/3 | 100% |

**SQLs gerados (samples qwen3:14b):**
```sql
SELECT COUNT(*) FROM adult                                                       -- q_count
SELECT AVG(age) FROM adult                                                       -- q_avg_age
SELECT COUNT(DISTINCT workclass) FROM adult WHERE workclass IS NOT NULL          -- q_distinct_workclass
SELECT education FROM adult GROUP BY education ORDER BY COUNT(*) DESC LIMIT 1   -- q_top_education
SELECT COUNT(*) FROM adult WHERE class = '>50K'                                  -- q_count_high_class
SELECT AVG("hours-per-week") FROM adult WHERE "sex" = 'Male'                     -- q_avg_hours_male
```

LLMs aplicam aspas duplas corretamente em `"hours-per-week"` e `"sex"`,
respeitam `IS NOT NULL` em distinct counts, geram WHERE clauses com
strings literais — comportamentos não-triviais.

**Comparação consolidada do paradigma H-TCF2:**

| Experimento | Dataset | Topology | Accuracy | Tie-aware? |
|-------------|---------|----------|----------|-----------|
| M3 cross-domain | synthetic 3 domínios | star 3-table | 96% | apenas q_distinct (F-Q17) |
| M9 | TPC-H canonical | star 3-table | 95.2% / 100% | sim, em q_top_product |
| **M9-Adult** | **Adult canonical** | **single-table** | **100%** | n/a |

**Implicação:** o paradigma "TCF schema carrier + LLM gera SQL + SQLite executa"
generaliza independentemente de:
1. **Topologia** — star 3-table OU single-table
2. **Origem** — synthetic (gerado) OU canonical (real industrial)
3. **Naming convention** — PT (cliente, vendas) OU EN (supplier, partsupp) OU
   hyphenated (hours-per-week)
4. **Schema complexity** — 3 colunas simples OU 14 colunas mistas

**Bônus de stratification:** TVD=0.0007 entre amostra (n=100) e população
(n=48 842) confirma que volume modesto é representativo quando estratificado.
Manifests M9-Adult registram métricas inline para auditoria.

**Implicação metodológica:**
- Para o paper, M9-Adult é evidência mais forte que M3 (synthetic) ou M9-TPCH
  (sintético-canônico): dataset 100% real, naming industrial, accuracy
  perfeita. Vale destacar como caso de validação externa final.
- Stratification metrics inline no manifest são novo padrão para todos
  os experimentos canonical com sampling.

**Referência:** `experiments/results/m9_adult/manifest.jsonl` (2026-04-25).
Comparar com `experiments/results/m9_canonical/` (TPC-H) e
`experiments/results/m3_crossdomain/` (synthetic).

---

## F-Q26 `{B}` — Random ≈ Stratified em Adult Census; "floor effect" do paradigma robusto

**Conclusão:** Em Adult Census com volume=100 e 5 seeds, **random sampling
e stratified sampling produzem accuracy idêntica (100%/100%, std=0)**. A
hipótese de que stratification reduz variância (H2) **não pôde ser
testada** — não há variância para reduzir. O paradigma TCF schema-carrier
é tão robusto neste cenário que mesmo amostras aleatórias produzem 100%.

**Evidência (M-strat, 2026-04-25):** 1 dataset Adult × 3 modelos × 7 questions
× 2 modos (random/stratify) × 5 seeds = 210 combos. Após dedup correto
(re-runs por crash de Ollama no meio): 210/210 = 100% em ambos modos.

**Vereditos das 3 hipóteses:**

| Hipótese | Resultado | Interpretação |
|---------|-----------|---------------|
| H1: mean(stratify) ≈ mean(random) | **CONFIRM** | Diferença = 0pp (threshold 2pp) |
| H2: std(stratify) < std(random) | **REJECT** (floor effect) | Ambos com std=0 — não há variância |
| H3: q_count_high_class diferenciado | **NÃO** | Todas 7 questions = 100% em ambos modos |

**Stratification metrics (todos os 5 seeds idênticos):** TVD=0.0007,
JSD=0.0, chi2_p=0.99 — distribuição preservada quase perfeitamente.

**Implicação prática:**
- **Em Adult vol=100:** random é suficiente; stratification não muda accuracy
- **Onde stratification ainda agrega:** 
  1. Auditabilidade científica (TVD/chi2_p registrados)
  2. Casos com sample muito pequeno (vol<20) — ver pre-runs anteriores onde
     std random=9.7 vs std stratify=0
  3. Datasets com queries L3 (subquery, CTE) onde accuracy é menor
  4. Reportabilidade — "amostra estratificada com TVD=X" é linguagem de paper

**Importante:** este finding **não invalida F-Q25** — pelo contrário, reforça.
A robustez do paradigma é tão alta em Adult que stratification não muda nada.
F-Q25 (M9-Adult 100% com stratify) e F-Q26 (M-strat 100% com random + stratify)
juntos = paradigma é independente de modo de sampling em Adult vol=100.

**Para o paper:** stratification metrics no manifest são padrão metodológico
mas accuracy é o veredito principal. Em datasets harder (queries L3, vol<20),
stratification provavelmente diferencia. Próximos experimentos (V-series)
devem testar isso.

**Caveat metodológico — bug no print_summary corrigido:** durante crash de
Ollama, 77 records de modo random ficaram como exception. Re-run completou,
mas print_summary tinha bug de "first occurrence wins" — leu os exception
antigos. **Corrigido em todos os 10 runners** para "last occurrence wins"
(handles re-runs corretamente). Padrão para futuros experimentos.

**Referência:** `experiments/results/m_strat/manifest.jsonl` (2026-04-25,
210 combos = 5 seeds × 3 models × 7 questions × 2 modes).

---

## F-Q27 `{B}` — Quality score estrutural correlaciona INVERSAMENTE com accuracy

**Conclusão:** Análise post-hoc de **1551 SQLs** (todos os manifests Linha B
M3-M_strat) usando `sql_quality.py` revela que **SQLs erradas têm quality
score médio MAIS ALTO** (0.839) que **SQLs corretas** (0.753), diferença
de -0.087 — o oposto do esperado intuitivamente.

**Mecanismo identificado:** quality_score atual mede *complexidade
estrutural* (JOIN explícito, ON correto, no SELECT *, single col, etc.),
não *correção semântica*. Em queries difíceis (q_distinct com FK
ambíguo em financial, q_having com scope de agregação), modelos geram
SQL **estruturalmente sofisticada** (com JOIN+ON, ricas, ~1.0 quality)
que **executa com erro** (`sql_error:OperationalError` por coluna
inexistente). Em queries fáceis (q_count single-table, q_above_avg sem
JOIN), modelos geram SQL simples (~0.25 quality) que acerta sempre.

**Resultado: complexidade SQL é proxy de DIFICULDADE da query, não de
qualidade.** Quanto mais difícil a question, mais elaborada a SQL, e
mais provável de errar — anti-correlação acidental.

**Evidência (M-quality, 2026-04-25):** 1551 SQLs analisadas em 9 fases
(M3, M6, M6b, M7, M8, M8b, M9, M9-Adult, M-strat). Accuracy global 77.3%
(1199/1551).

**Componentes prevalência (proporção de SQLs com cada característica):**

| Componente | % | Comentário |
|-----------|---|-----------|
| no_select_star | 100% | Modelos nunca usam SELECT * |
| tables_exist | 96.9% | Maioria referencia tabelas válidas |
| single_result_col | 91.7% | Retorno escalar, conforme pedido |
| has_explicit_join | 54.1% | Metade usa JOIN (depende da query) |
| join_uses_on | 49.6% | Quando há JOIN, quase sempre com ON |
| has_subquery | 31.1% | Subqueries são minoria |
| has_cte | 3.1% | CTEs são raras |

**Discrepâncias notáveis:**
- 241 SQLs com quality ≥ 0.85 mas falharam (16% do total) — mostram que
  estrutura não garante correção
- 17 SQLs com quality < 0.5 mas acertaram — geralmente queries triviais
  sem JOIN

**Por modelo (sem diferenciação significativa):**
- qwen3:14b: quality 0.786 (n=517)
- qwen2.5-coder:7b: quality 0.779 (n=517)
- phi4:latest: quality 0.752 (n=517)

**Implicações metodológicas:**

1. **Quality score atual NÃO é métrica de qualidade SQL no sentido prático**
   — é métrica de *complexidade estrutural*. Útil como **descritor**, não
   como **avaliador**.

2. **Métrica alternativa proposta — `quality_when_ok`:** computar
   quality_mean APENAS sobre SQLs corretas. Proxy de "elegância": entre
   SQLs que funcionam, quanto bem-estruturadas são. Métrica útil para
   diferenciar modelos que acertam com SQL elaborado vs com SQL
   simples-mas-correto.

3. **Para comparar comerciais com locais (M-Acomm pendente):** reportar
   quality_when_ok além de accuracy. Se comerciais mantêm accuracy ~100%
   com SQLs estruturalmente complexas (CTEs, subqueries), isso indica
   capacidade de construções avançadas além de funcionalidade.

4. **Não publicar como "TCF gera SQL de alta qualidade"** — publicar como
   **descoberta metodológica**: structural quality metrics underestimate
   semantic correctness in LLM-generated SQL. Achado independente de TCF.

**Referência:** `experiments/results/m_quality/per_record.jsonl`
(1551 records), `report.json`, `summary.md`. Reproduzível via
`python experiments/eval/run_m_quality.py`.

---

## F-Q28 `{B}` — Linha A local em canonical: 52% — STATS resolvem agregação simples, FALHAM em filter+agg

**Conclusão:** Reproduzindo F-Q12 em **Adult Census canonical** com método
moderno (stratify, dedup correto, scoring atualizado): modelos locais 7-14B
em Linha A (LLM lê TCF e calcula) atingem **52.4% (33/63 combos)**.
Decomposição por tipo de question é **dramática**:

| Tipo de Question | Acc média | Mecanismo |
|-----------------|-----------|-----------|
| **Stats agregadas diretas** (count, sum, avg, max sobre tabela inteira) | **100%** | LLM lê STATS hint pré-computada no topo |
| Lookup categórico (top_education) | 52% | LLM precisa contar ocorrências |
| **Filter + agregação** (WHERE + COUNT/AVG) | **5-11%** | LLM precisa **operar** sobre dados |
| Distinct count manual | **0%** | LLM precisa coletar valores únicos |

**Evidência (M-Alocal, 2026-04-25):** 3 modelos locais × 7 questions × 3 seeds
= 63 combos sobre Adult vol=100 stratified by class. Mesmo dataset que F-Q25
(M9-Adult Linha B = 100%).

**Per modelo (todos similares, ~50-57%):**
- qwen2.5-coder:7b: 12/21 = 57.1%, CI [36.5%, 75.5%]
- phi4:latest: 11/21 = 52.4%, CI [32.4%, 71.7%]
- qwen3:14b: 10/21 = 47.6%, CI [28.3%, 67.6%]

Sem diferenciação significativa entre modelos — **arquitetura/capacity não
ajuda em questões filter+agg para 7-14B**. Wilson CIs sobrepõem.

**Atualização vs F-Q12 antigo:**
- F-Q12 sintético antigo: **~60-70% ceiling** (synthetic retail)
- F-Q28 canonical novo: **52.4%** — **pior** que F-Q12 antigo

Adult Census é mais difícil porque tem mais questões com filter (vs synthetic
retail dominado por full-table aggregations). Logo F-Q12 era subestimado se
generalizado para datasets reais.

**Comparação direta com Linha B (mesmo dataset, mesmas 7 questions):**

| Paradigma | Accuracy | Mecanismo |
|-----------|----------|-----------|
| Linha A (LLM calcula) | **52%** | TCF L2 + STATS + LLM como calculador |
| Linha B (LLM gera SQL) | **100%** (F-Q25) | TCF schema + LLM gera SQL + SQLite executa |

**Diferenciação clara:** 48pp de gap. Linha B vence Linha A em filter+agg.

**Implicação científica fortalecida:**

1. **STATS hints servem para "aritmética grátis"**, não para "raciocínio
   condicional". Se a question é "soma total" → LLM lê STATS sum=. Se é
   "soma para sex='Male'" → LLM precisaria iterar sobre rows e filtrar,
   o que não funciona.

2. **Linha A é VIÁVEL para um subset bem-definido** (questions sem WHERE
   sobre tabela inteira). Para qualquer question com filter, Linha A é
   inviável em modelos locais.

3. **F-Q12 fica refinado:** não é "Linha A satura em 60-70%". É:
   - Aritmética agregada com STATS: ~100%
   - Filter+agg sem STATS: ~5%
   - Mistura proporcional dependente da workload

4. **Paper benefit:** decomposição por tipo de question é mais defensável
   que average global. Permite recomendação prática: "Use Linha A se 100%
   das suas queries são full-table aggregations; senão use Linha B."

**Para M-Acomm (Linha A em comerciais):** baseline definitivo é
**52.4% locais com filter heavy**. Comerciais precisam superar isso
**em queries com filter** especificamente para refutar F-Q12 universal.

**Referência:** `experiments/results/m_alocal/manifest.jsonl` (2026-04-25,
63 combos × Adult × Linha A).

---
