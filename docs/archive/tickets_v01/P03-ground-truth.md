# P03 — Módulo de Ground Truth

**Status:** PARCIALMENTE FEITO (valores hardcoded em run_eval.py)  
**Tipo:** Infraestrutura  
**Bloqueia:** H02–H10 (todos dependem de ground truth correto)  
**Arquivo:** `experiments/eval/llm_eval/ground_truth.py` (criar)

## Problema

Ground truth está hardcoded em `run_eval.py`. Se o dataset mudar, os valores ficam desatualizados silenciosamente.

## Ground Truth Atual (vendas 41 linhas)

| Questão | Valor | Como calcular |
|---------|-------|---------------|
| Q1 sum_vl | 217.55 | sum(vl) |
| Q2 avg_vl | 5.3061 | sum/count |
| Q3 max_vl | 12.40 | max(vl) |
| Q4 min_vl | 1.00 | min(vl) |
| Q5 count_rows | 41 | len(vendas) |
| Q6 count_by_name(Ana) | 3 | count(id_pessoa==1) |
| Q7 sum_by_name(Ana) | 8.70 | sum(vl where id_pessoa==1) |
| Q8 top_fk_freq | Caneta (id=22, 5x) | mode(id_produto) |
| Q9 count_distinct_pessoa | 27 | len(distinct(id_pessoa)) |
| Q10 top_spender | calcular | argmax(sum(vl) group by id_pessoa) |

## Módulo

```python
# ground_truth.py
def compute(data_dir: Path) -> dict:
    """Compute all ground truth values from source CSVs."""
    vendas = load_csv(data_dir / "vendas.csv")
    pessoas = load_csv(data_dir / "pessoas.csv")
    ...
    return {
        "sum_vl":   round(sum(vl), 4),
        "avg_vl":   round(sum(vl)/len(vl), 4),
        "max_vl":   max(vl),
        "min_vl":   min(vl),
        "count":    len(vendas),
        "count_by_name": {"Ana": 3, ...},
        "sum_by_name":   {"Ana": 8.70, ...},
        "top_product":   {"id": "22", "name": "Caneta", "count": 5},
        "count_distinct_pessoa": 27,
        "top_spender":   {"id": "1", "name": "Ana", "total": ...},
    }
```

## Critério de Aceitação

`compute(DATA_DIR)["sum_vl"] == 217.55` — testável em `tests/test_ground_truth.py`.
