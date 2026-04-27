---
title: Coverage gaps M1-M4 + intermediate SQL forms survey
date: 2026-04-22
type: research-note
status: DRAFT
---

# Coverage gaps e formas intermediárias de query

## 1. O que M1-M4 cobrem hoje

| Dimensão | Cobertura atual | Lacuna |
|----------|----------------|--------|
| Schema topology | Star (2 dims + 1 fact) | Snowflake, multiple facts, self-joins |
| Question types | Count, sum, avg, max, distinct, top-N, lookup | Filter (WHERE), date range, GROUP BY multi-col, subquery, HAVING |
| Scale | n=100 (M1/M3/M4), n=500-5000 (M2 scale probe) | Schema complexity >> row count |
| Models | 3 (7B, 14B, reasoning) | Commercial APIs (Claude, GPT-4o, Gemini) |
| Languages | PT | EN (F-Q3 confirmou equivalência para top-5) |
| Formats | TCF, CSV, JSON (M4) | YAML, Markdown table, Excel-style |
| Seeds | 3 (42, 123, 7) | Suficiente para variance (F-Q13: 0pp inter-seed) |
| Null rates | 5% (default fixture) | 30-50% (dados reais têm muitos nulls) |
| Column types | int, float, string, date | Boolean, ENUM, BLOB |

## 2. Lacunas prioritárias para validade externa

### 2a. Mais question types (impacto alto)
Os 7 question types atuais são todos **aggregation simples ou lookup**.
Dados reais precisam de:
- `WHERE` com filtro (ex: "soma de vendas em Março")
- `GROUP BY` multi-coluna (ex: "total por produto e mês")
- `HAVING` (ex: "clientes com mais de 3 compras")
- Subquery / CTE (ex: "produto mais vendido em cada região")
- Date arithmetic (ex: "vendas nos últimos 30 dias")

**Hipótese:** Modelos menores vão falhar em subqueries mesmo com schema TCF.
Esto seria análogo a F-Q12 (aritmética universal) mas para SQL complexidade.

### 2b. Schema com mais tabelas (impacto médio)
Todos os experimentos usam exatamente 3 tabelas (dim1, dim2, fact).
Schemas reais têm 5-20+ tabelas. Aumentar para 5 tabelas testaria:
- Model capacity para manter FK graph maior no contexto
- Ambiguidade aumentada (múltiplos caminhos de JOIN)

### 2c. Null handling (impacto médio)
null_rate=5% hoje. Em dados reais (healthcare, financial), 20-40% de colunas
opcionais têm nulls. SQL com `IS NULL` / `COALESCE` é padrão mas provavelmente
zero-shot incorreto para modelos menores.

### 2d. Variações de wording das perguntas (impacto médio)
Atualmente cada question tem um único template fixo. Robustez real requer
testar paráfrases:
- "Quantas linhas?" vs "Qual o total de registros?" vs "Conte os itens"
- Em dados reais, usuário nunca usa o mesmo template

---

## 3. Formas intermediárias de query (alternatives to raw SQL)

### Motivação
M1-M4 usaram SQL diretamente como target. Mas existem outras formas que:
(a) modelos podem gerar com maior confiabilidade (treinados em mais exemplos),
(b) podem ser convertidas deterministicamente para SQL ou executadas diretamente.

### 3.1 Pandas/Python expressions

**O que é:** API Python para operações relacionais.
```python
# q_sum
tables["vendas"]["total"].sum()

# q_top_product
tables["vendas"].merge(tables["produtos"], left_on="id_produto", right_on="id") \
    .groupby("nome")["id"].count().idxmax()
```

**Por que pode funcionar melhor:**
- Modelos são treinados em bilhões de linhas de Python com Pandas
- Join syntax é explícito (`left_on=`, `right_on=`) — menos alucinação de colunas
- Execução direta sem SQLite overhead

**Por que pode ser pior:**
- Pandas em memória não escala para tabelas grandes
- Syntax verbosa para queries complexas
- Modelos ainda podem alucinar column names

**Status em literatura:** PoT (Gao 2023) usa Python para aritmética, não para
relational queries. Sem baseline direto para text-to-Pandas em star schemas.

### 3.2 PRQL (Pipelined Relational Query Language)

**O que é:** Linguagem query com sintaxe pipeline (como dplyr/pipes).
```prql
from vendas
join produtos (==id_produto)
group produtos.nome (
  aggregate { count this }
)
sort { -count }
take 1
```

**Por que pode funcionar melhor:**
- Sem subconsultas implícitas — cada step é explícito
- FK sempre nomeado no join (menos alucinação)
- Compila deterministicamente para SQL

**Por que pode ser pior:**
- Pouco treinamento (linguagem nova, <2023)
- Modelo pode não conhecer a sintaxe

### 3.3 Structured JSON query (MongoDB-style)

**O que é:** Pipeline de agregação em JSON.
```json
[
  {"$lookup": {"from": "produtos", "localField": "id_produto",
               "foreignField": "id", "as": "prod"}},
  {"$group": {"_id": "$prod.nome", "count": {"$sum": 1}}},
  {"$sort": {"count": -1}},
  {"$limit": 1}
]
```

**Por que pode funcionar melhor:**
- JSON é gerado com alta confiança por qualquer modelo
- Pipeline explícito — sem ambiguidade de ordem de operações
- Modelos são treinados em muitos exemplos de MongoDB aggregation

**Por que pode ser pior:**
- Verbose para queries simples
- MongoDB e SQLite têm semânticas diferentes (nulls, types)
- Tradução para SQL não é trivial

### 3.4 Structured decomposition (chain-of-thought SQL)

**O que é:** Modelo emite passos em linguagem natural antes de gerar SQL.
```
Passos:
1. Preciso da tabela `vendas` e fazer JOIN com `produtos` pelo campo `id_produto`.
2. Agrupar por `produtos.nome` e contar ocorrências.
3. Ordenar decrescente e pegar o primeiro.
SQL: SELECT p.nome FROM vendas v JOIN produtos p ON v.id_produto = p.id ...
```

**Por que pode funcionar melhor:**
- Chain-of-thought reduz erros de alucinação em modelos reasoning
- Plano explícito força verificação dos JOINs antes de emitir SQL
- Compatível com cualquier executor SQL

**Por que pode ser pior:**
- Aumenta tokens drasticamente (latência + custo)
- Modelos com think=False não se beneficiam
- Verificação de passos é implícita — modelo ainda pode alucinações

### 3.5 Relational algebra / Datalog

**O que é:** Notação formal de álgebra relacional.
```
π_{nome}(σ_{max_total}(ρ_{total←custo}(vendas) ⋈_{id_produto=id} produtos))
```

**Por que pode funcionar pior (provavelmente):**
- Notação pouco vista em training data
- Mais ambígua do que SQL para modelos treinados em SQL
- Sem vantagem clara sobre SQL direto

---

## 4. Hipótese de experimento M5

**M5 — Intermediate forms:** Testar Pandas vs SQL vs CoT-SQL nos mesmos
3 domínios, mesmos 3 modelos, 7 question types.

| Variant | Generator | Executor |
|---------|-----------|----------|
| `sql_stats_fs` | LLM → SQL | SQLite |
| `pandas_stats_fs` | LLM → Python/Pandas | Python eval |
| `cot_sql_stats_fs` | LLM → CoT + SQL | SQLite |
| `prql_stats_fs` | LLM → PRQL | prqlc → SQLite |

**Hipótese principal:** Pandas generation vai ter accuracy ≥ SQL para modelos
menores (qwen2.5-coder:7b) em joins complexos, porque Pandas usa named params
para FK resolution em vez de SQL column aliasing.

**Risco:** Pandas exec em sandbox requer eval() — security concern.
Mitigação: executar em processo filho com timeout, sem rede.

---

## 5. Recomendação de prioridade

| Experimento | Valor científico | Custo | Recomendação |
|-------------|-----------------|-------|--------------|
| M5-pandas vs SQL | Alto — novo insight on execution form | Médio | **Fazer** |
| M6-WHERE/filter questions | Alto — coverage real-world | Baixo | **Fazer depois M5** |
| M7-snowflake schema | Médio — schema complexity | Alto | Adiado |
| M8-commercial models | Alto — paper credibility | Baixo (API) | **Fazer antes do paper** |
| M9-wording robustness | Médio — production validity | Médio | Pós-paper |
