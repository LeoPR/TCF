---
title: Quality reports — relatorios de qualidade por dataset
type: task
status: DONE
priority: 6
parent: 01-M-datasets-setup
completed: 2026-04-11
---

## STATUS: COMPLETO (2026-04-11)

**Separacao arquitetural aplicada:** criamos um modulo reader
reutilizavel (`dataset_reader.py`) que sera usado tambem por
derivations (ticket 08) e questions (ticket 09). Este e um
**client de suporte**, nao parte do core TCF.

**Criado:** `scripts/dataset_reader.py` (~330 linhas)
- Classe `DatasetReader` com:
  * `tables`, `schema()`, `pk()`, `fk()`, `row_count()`
  * `rows()` / `iter_rows()` — row-oriented (list[dict])
  * `columns()` — column-oriented (dict[col, list])
  * `query()` — SQL arbitrario (para ground truth)
  * `column_stats()` — estatisticas numericas ou categoricas
- Helpers `is_numeric()`, `is_text()`
- Context manager `open_dataset()`
- Self-test executavel direto

**Criado:** `scripts/quality_report.py` (~180 linhas)
- Gera markdown legivel em `datasets/quality-reports/{name}.md`
- Schema summary (PK, FK, tipos)
- Estatisticas por coluna (numericas vs categoricas)
- Top-K values + entropia (categoricas)
- Sample rows (head)

**Reports gerados:**
- `adult-census.md` (2.7 KB) — 15 colunas, 48K rows, missing values documentados
- `tpch-sf001.md` (14.7 KB) — 8 tabelas, 86K rows, todas as FKs documentadas

**Achados interessantes (ja visiveis):**
- Adult: workclass dominado por "Private" (69.4%), baixa entropia (1.4 bits)
- Adult: `native-country` tem 41 valores distintos mas `United-States` provavelmente domina (detalhe no report)
- TPC-H: cardinalidades exatas por tabela
- TPC-H lineitem tem 16 cols, 3 FKs, composite PK — caso complexo

**Reproducivel:**
- `python scripts/quality_report.py` (todos)
- `python scripts/quality_report.py tpch-sf001` (um)

**Reusabilidade do reader:**
Tickets 08 (derivations), 09 (questions) e 07 compartilham o mesmo
`DatasetReader`. Se amanha trocarmos SQLite por Parquet, so o reader
muda — scripts de consumo continuam iguais.

---


# Quality Reports

## Objetivo

Gerar um `quality-report.md` para cada dataset canonico documentando:
- Distribuicoes
- Missing values
- Outliers
- Cardinalidade por coluna
- Tipos detectados
- Amostras representativas (head, tail, random)

Isso da **transparencia** sobre os dados antes de rodar experimentos.

## O que incluir em cada report

### 1. Resumo executivo

```markdown
# Quality Report — tpch-sf001

- **Total rows (lineitem):** 60,175
- **Total tables:** 8
- **Total columns:** 61 (somando todas as tabelas)
- **Missing values:** 0 (TPC-H nao gera nulls)
- **Gerado em:** 2026-04-10
```

### 2. Schema summary

```markdown
## Schema

| Tabela | Rows | Cols | PK | FKs |
|--------|------|------|-----|-----|
| region | 5 | 3 | r_regionkey | - |
| nation | 25 | 4 | n_nationkey | region |
| supplier | 100 | 7 | s_suppkey | nation |
| ...
```

### 3. Por coluna numerica

```markdown
## lineitem.l_extendedprice

- **Type:** REAL
- **Nullable:** false
- **Count:** 60,175
- **Min:** 901.00
- **Max:** 104,749.50
- **Mean:** 38,206.73
- **Median:** 36,822.96
- **StdDev:** 23,300.42
- **Zeros:** 0
- **Negatives:** 0
- **Histograma:** [visual ASCII ou referencia a PNG]
```

### 4. Por coluna categorica

```markdown
## customer.c_mktsegment

- **Type:** TEXT
- **Nullable:** false
- **Distinct values:** 5
- **Top 5:**
  - BUILDING: 304 (20.3%)
  - HOUSEHOLD: 298 (19.9%)
  - AUTOMOBILE: 302 (20.1%)
  - MACHINERY: 294 (19.6%)
  - FURNITURE: 302 (20.1%)
- **Entropy:** 2.32 bits (max: 2.32)
- **Distribution:** uniforme
```

### 5. Amostras representativas

```markdown
## Sample rows (lineitem)

### Head (first 5)
| l_orderkey | l_partkey | l_quantity | l_extendedprice | l_shipdate |
|-----------|-----------|-----------|-----------------|-----------|
| 1 | 1552 | 17 | 24710.35 | 1996-03-13 |
| ...

### Tail (last 5)
...

### Random (5)
...
```

### 6. Anomalias detectadas

```markdown
## Anomalias

- Nenhuma detectada (TPC-H e sintetico bem controlado)
```

(Para Adult: provavelmente vai ter:
- Missing values em 3 colunas (`?`)
- Outliers em capital-gain/loss (poucas amostras com >$99,999)
- Imbalance no target (75% <=50K, 25% >50K)
)

## Implementacao

Script `scripts/generate_quality_report.py` que:
1. Le SQLite do dataset
2. Roda queries de agregacao por coluna
3. Gera markdown estruturado
4. Salva em `datasets/quality-reports/{name}.md`

Usa stdlib (sqlite3, statistics) — nao precisa de pandas.

## Tarefas

- [ ] Criar `scripts/generate_quality_report.py`
- [ ] Gerar report para tpch-sf001
- [ ] Gerar report para adult-census
- [ ] Revisar manualmente — esta claro? util?
- [ ] Commit dos reports gerados (sao pequenos, legiveis, uteis)

## Verificacao

- 2 arquivos em `datasets/quality-reports/`
- Cada um tem schema + colunas + amostras + anomalias
- Reproducivel via script
