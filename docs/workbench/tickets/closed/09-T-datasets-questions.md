---
title: Banco de perguntas canonicas por dataset
type: task
status: DONE
priority: 8
parent: 01-M-datasets-setup
completed: 2026-04-11
---

## STATUS: COMPLETO (2026-04-11)

**Criado:** `datasets/questions/tpch-sf001.json` (15 questoes)
**Criado:** `datasets/questions/adult-census.json` (10 questoes)

Ambos com:
- Texto bilingue (pt-BR + en-US)
- SQL executavel (ground truth autoritativo)
- Categorias (aggregation, lookup, filter_aggregation, group_by, join, distinct)
- Operacoes (sum, avg, max, min, count, argmax_count, count_by_group, etc)
- Dificuldade (easy/medium/hard)
- Answer type (numeric, count, string, pairs)

**Criado:** `scripts/compute_ground_truth.py`
- Usa `DatasetReader.query()` para executar SQL
- Normaliza resultados (scalar vs pairs)
- Suporta `--preview` (dry-run)
- Salva JSON com ground_truth populado

**Executado — 25 ground truths populados:**

TPC-H (15):
```
q1_sum_extendedprice            [numeric] 2152189760.47
q2_avg_discount                 [numeric] 0.04993003739094308
q3_max_totalprice               [numeric] 466001.28
q4_min_acctbal                  [numeric] -994.79
q5_count_lineitem               [count]   60175
q6_distinct_mktsegment          [count]   5
q7_filter_sum_returnflag_r      [numeric] 534594445.35
q8_count_returnflag_n           [count]   30397
q9_top_mktsegment               [string]  BUILDING
q10_orders_by_priority          [pairs]   (5 pairs)
q11_join_customers_by_nation    [pairs]   MOROCCO, IRAN, CANADA, BRAZIL, SAUDI...
q12_join_top_region_by_supplier [string]  ASIA (3-table join!)
q13_avg_orderprice_by_status    [pairs]   F/O/P
q14_quantity_above_threshold    [count]   12056
q15_sum_extendedprice_shipmode  [numeric] 303207759.31
```

Adult (10):
```
q1_avg_age                 [numeric] 38.64
q2_count_rows              [count]   48842
q3_max_hours               [numeric] 99
q4_distinct_education      [count]   16
q5_missing_workclass       [count]   2799    ← bate com metadata!
q6_count_high_income       [count]   11687
q7_avg_age_high_income     [numeric] 44.28
q8_group_count_by_sex      [pairs]   Female/Male
q9_top_occupation          [string]  Prof-specialty
q10_avg_hours_by_class     [pairs]   <=50K:38.84, >50K:45.45
```

**Cobertura por categoria:**
- Easy (lookup simples): 8 perguntas
- Medium (filter, group-by): 13 perguntas
- Hard (joins 2-3 tabelas): 4 perguntas

**Reproducivel:**
```
python scripts/compute_ground_truth.py              # ambos
python scripts/compute_ground_truth.py tpch-sf001   # so um
python scripts/compute_ground_truth.py --preview    # dry-run
```

**Tudo em git:** os JSONs de perguntas + ground_truth (pequenos, ~11KB total).
SQL e a "unica fonte de verdade" — se os dados mudam, roda o script e re-gera.

---


# Banco de Perguntas Canonicas

## Objetivo

Criar um banco de perguntas para cada dataset canonico, com:
- Texto da pergunta em linguagem natural
- Query SQL equivalente (ground truth executavel)
- Tipo de operacao (aggregation, lookup, filter, join)
- Nivel de dificuldade (easy, medium, hard)

**Importante:** perguntas sao **derivadas do SQLite** (com schema tipado),
e ground truth e **computada via SQL**, nao hardcoded.

## Localizacao

```
datasets/questions/
├── tpch-sf001.json
└── adult-census.json
```

## Formato

```json
{
  "dataset": "tpch-sf001",
  "version": "1.0",
  "questions": [
    {
      "id": "q1",
      "text_pt": "Qual a quantidade total de items pedidos (sum de l_quantity)?",
      "text_en": "What is the total quantity of items ordered?",
      "sql": "SELECT SUM(l_quantity) FROM lineitem",
      "category": "aggregation",
      "operation": "sum",
      "difficulty": "easy",
      "answer_type": "numeric"
    },
    {
      "id": "q2",
      "text_pt": "Qual o pedido com maior valor total (l_extendedprice)?",
      "text_en": "Which order has the highest extended price?",
      "sql": "SELECT l_orderkey, l_extendedprice FROM lineitem ORDER BY l_extendedprice DESC LIMIT 1",
      "category": "lookup",
      "operation": "argmax",
      "difficulty": "medium",
      "answer_type": "row"
    },
    ...
  ]
}
```

## Categorias de perguntas

**Para TPC-H:**
1. **Aggregation** (sum, avg, count, max, min em colunas numericas)
2. **Filter + Aggregation** (sum WHERE categoria = X)
3. **Group By** (sum por grupo)
4. **Join** (2-3 tabelas)
5. **Distinct** (contagem de valores unicos)
6. **Top-K** (ORDER BY + LIMIT)

**Para Adult:**
1. **Distribuicao** (contagem por categoria)
2. **Media condicional** (avg age WHERE income = '>50K')
3. **Proporcoes** (% de mulheres em cada education level)
4. **Missing values** (quantas rows tem '?' em workclass)

## Quantas perguntas por dataset

**TPC-H:** ~15 perguntas
- 5 agregacoes simples
- 3 filter + agg
- 3 group by
- 2 joins (2 tabelas)
- 2 distinct/top-k

**Adult:** ~10 perguntas
- 4 distribuicoes
- 3 media condicional
- 2 proporcoes
- 1 missing values

## Ground truth computation

Script `scripts/compute_ground_truth.py`:

```python
import sqlite3
import json
from pathlib import Path

def compute_answers(dataset_name):
    db = sqlite3.connect(f"datasets/sqlite/{dataset_name}.db")
    qfile = Path(f"datasets/questions/{dataset_name}.json")
    data = json.loads(qfile.read_text(encoding="utf-8"))

    for q in data["questions"]:
        cursor = db.execute(q["sql"])
        result = cursor.fetchall()
        # Normalize to simple types
        if len(result) == 1 and len(result[0]) == 1:
            q["ground_truth"] = result[0][0]
        else:
            q["ground_truth"] = result

    qfile.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    db.close()
    print(f"Computed {len(data['questions'])} answers for {dataset_name}")
```

## Tarefas

- [ ] Escrever 15 perguntas para TPC-H (manual, baseadas no schema)
- [ ] Escrever 10 perguntas para Adult (manual)
- [ ] Criar `scripts/compute_ground_truth.py`
- [ ] Rodar para ambos — ground_truth preenchido automaticamente
- [ ] Review manual: ground truth faz sentido?
- [ ] Commit dos JSONs (incluindo ground_truth — pequenos)

## Criterio

- `datasets/questions/tpch-sf001.json` com 15 perguntas + ground truth
- `datasets/questions/adult-census.json` com 10 perguntas + ground truth
- Ground truth verificavel via SQL (reproducivel)
- Perguntas bilingues (pt-BR + en-US) para testar idioma no futuro

## O que NAO fazer

- **Nao rodar LLM** nesta etapa — so gerar perguntas + respostas
- **Nao comparar** com perguntas antigas do `retail_sales` (aqueles viram backlog)
- **Nao incluir** perguntas muito complexas (multi-join 4+ tabelas)
  — deixa para v2 se necessario
