---
title: Banco de perguntas canonicas por dataset
type: task
status: OPEN
priority: 8
parent: 01-M-datasets-setup
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
