---
title: How to — Como inspecionar a compressão (SideOutputs + schema)
type: how-to
status: active
tags: [debug, inspecção, features, compressão, schema]
created: 2026-05-27
updated: 2026-05-27
---

# Como inspecionar a compressão (SideOutputs + schema)

Receita pra investigar por que uma coluna comprimiu bem ou mal,
visualizar features detectadas, e explorar decisões do pipeline.

## Motivação

Ao rodar `encode(data)`, TCF aplica heuristicas (cadence detection,
min_len auto, OBAT shaping, HCC compression). Resultado: algumas colunas
comprimem muito, outras pouco. Entender **por quê** requer acesso a
informação normalmente descartada — logs internos, features extraidas,
bytes por etapa. `SideOutputs` e `build_schema` expõem essa informação
pra debug e análise.

## Quando aplicar

- Quero ver por que uma coluna ficou grande (alta cardinalidade?
  sem repeticao? sem padrão?)
- Preciso validar que o schema foi detectado corretamente
- Investigando se heuristicas dispararam (cadence, min_len, etc)
- Explorando dados novos pra tuning de `nature` ou `layers`

## SideOutputs — capturar info interna

`SideOutputs` é um container que você passa a `encode()` pra coletar
informação produzida internamente mas normalmente descartada.

### Uso básico — single-col

```python
from tcf import encode
from tcf.side_outputs import SideOutputs

data = ["apple", "apple", "banana", "cherry", "cherry", "cherry"]

# Criar container
side = SideOutputs()

# Passar a encode()
text = encode(data, side_outputs=side)

# Campos populados agora
print(f"n_rows: {side.column_features.n_rows}")
print(f"n_unicas: {side.column_features.n_unicas}")
print(f"cardinality: {side.column_features.cardinality}")
print(f"body_bytes: {side.body_bytes}")
print(f"cadence_detected: {side.cadence_detected}")
```

Saída esperada:

```
n_rows: 6
n_unicas: 3
cardinality: 0.5
body_bytes: 26
cadence_detected: False
```

### Campos de SideOutputs — referência

**Pre-pass (por coluna):**

| Campo | Tipo | Significado |
|---|---|---|
| `column_features` | `ColumnFeatures \| None` | Features imutáveis extraídas em O(N): `n_rows`, `n_unicas`, `avg_len`, `cardinality`, `is_numeric`, `sample` |
| `cadence_detected` | `bool \| None` | True = heurística de cadence disparou (padrão repetido detectado) |
| `cadence_info` | `dict \| None` | Detalhe: `rule_hit`, `reason`, `lengths`, `cardinality`, etc |
| `min_len` | `int \| None` | Comprimento mínimo dos substrings (auto-detectado via heurística) |

**OBAT (por coluna):**

| Campo | Tipo | Significado |
|---|---|---|
| `obat_log` | `str \| None` | Log detalhado do shaping OBAT (prefixos/sufixos extraidos) |
| `obat_used_hint` | `bool \| None` | True = processado com hint, False = canonical |

**HCC (por coluna):**

| Campo | Tipo | Significado |
|---|---|---|
| `hcc_trace` | `str \| None` | Trace do detector de composições HCC (iterações de busca) |
| `hcc_rede` | `str \| None` | Rede final de atoms + compositions após HCC |
| `seq_rle_runs` | `list[dict]` | RLE runs detectados (vazio se nenhum) |

**Bytes e multi-col:**

| Campo | Tipo | Significado |
|---|---|---|
| `body_bytes` | `int \| None` | Bytes do corpo (single-col); calculado por coluna em multi-col |
| `multi_info` | `dict \| None` | Info agregada multi-col: `n_rows`, `n_cols`, `total_bytes`, `header_bytes`, `body_bytes` |
| `per_col` | `dict[str, SideOutputs] \| None` | Ninhada: `per_col[colname]` tem SideOutputs de cada coluna |

### Uso — multi-col

```python
from tcf import encode
from tcf.side_outputs import SideOutputs

data = {
    "id": ["1", "2", "3", "4"],
    "name": ["alice", "bob", "charlie", "alice"]
}

side = SideOutputs()
text = encode(data, side_outputs=side)

# Agregado (multi-col)
print(f"total_bytes: {side.multi_info['total_bytes']}")
print(f"header_bytes: {side.multi_info['header_bytes']}")
print(f"body_bytes: {side.multi_info['body_bytes']}")

# Por coluna
for col_name, col_side in side.per_col.items():
    print(f"\n{col_name}:")
    print(f"  body_bytes: {col_side.body_bytes}")
    print(f"  cardinality: {col_side.column_features.cardinality}")
    print(f"  cadence: {col_side.cadence_detected}")
```

Saída esperada:

```
total_bytes: 53
header_bytes: 24
body_bytes: 29

id:
  body_bytes: 8
  cardinality: 1.0
  cadence: True

name:
  body_bytes: 21
  cardinality: 0.75
  cadence: False
```

## build_schema — inspecionar schema detectado

`build_schema(data)` chama `encode()` internamente (com `SideOutputs`),
extrai features por coluna + decisões de heuristicas, e retorna
`TableSchema` estruturado. Mais conveniente que acessar SideOutputs
diretamente se você só quer o schema.

### Uso — single-col

```python
from tcf import build_schema

data = ["apple", "apple", "banana", "cherry", "cherry", "cherry"]
schema = build_schema(data)

print(f"n_rows: {schema.n_rows}")
print(f"n_cols: {schema.n_cols}")
print(f"is_multi_col: {schema.is_multi_col}")
print(f"total_bytes: {schema.total_bytes}")

col = schema.columns["val"]
print(f"\nColuna 'val':")
print(f"  n_unicas: {col.n_unicas}")
print(f"  avg_len: {col.avg_len}")
print(f"  cardinality: {col.cardinality}")
print(f"  is_numeric: {col.is_numeric}")
print(f"  body_bytes: {col.body_bytes}")
print(f"  cadence_detected: {col.cadence_detected}")
print(f"  cadence_rule: {col.cadence_rule}")
print(f"  min_len: {col.min_len}")
print(f"  seq_rle_runs_count: {col.seq_rle_runs_count}")
print(f"  sample: {col.sample}")
```

Saída esperada:

```
n_rows: 6
n_cols: 1
is_multi_col: False
total_bytes: 26

Coluna 'val':
  n_unicas: 3
  avg_len: 5.667
  cardinality: 0.5
  is_numeric: False
  body_bytes: 26
  cadence_detected: False
  cadence_rule: None
  min_len: 3
  seq_rle_runs_count: 0
  sample: ['apple', 'apple', 'banana', 'cherry', 'cherry', 'cherry']
```

### Uso — multi-col

```python
from tcf import build_schema

data = {
    "id": ["1", "2", "3", "4"],
    "name": ["alice", "bob", "charlie", "alice"]
}

schema = build_schema(data)

print(f"n_rows: {schema.n_rows}")
print(f"n_cols: {schema.n_cols}")
print(f"total_bytes: {schema.total_bytes}")
print(f"header_bytes: {schema.header_bytes}")
print(f"body_bytes: {schema.body_bytes}")

for col_name, col in schema.columns.items():
    print(f"\n{col_name}:")
    print(f"  n_unicas: {col.n_unicas}")
    print(f"  cardinality: {col.cardinality}")
    print(f"  is_numeric: {col.is_numeric}")
    print(f"  body_bytes: {col.body_bytes}")
    print(f"  cadence_rule: {col.cadence_rule}")
```

Saída esperada:

```
n_rows: 4
n_cols: 2
total_bytes: 53
header_bytes: 24
body_bytes: 29

id:
  n_unicas: 4
  cardinality: 1.0
  is_numeric: True
  body_bytes: 8
  cadence_rule: 2-numeric-high-cardinality

name:
  n_unicas: 3
  cardinality: 0.75
  is_numeric: False
  body_bytes: 21
  cadence_rule: None
```

### Serializar schema — to_json()

```python
from tcf import build_schema
import json

data = {
    "id": ["1", "2", "3", "4"],
    "name": ["alice", "bob", "charlie", "alice"]
}

schema = build_schema(data)
json_str = schema.to_json()
print(json_str)

# Ou to_dict() pra processar manualmente
d = schema.to_dict()
print(json.dumps(d, indent=2))
```

## Interpretar: relacionar bytes a features

Por que uma coluna comprimiu mal? Busque padrões nos campos de
`SideOutputs` / `schema.columns[name]`:

### Padrão 1: Alta cardinalidade, sem repetição

**Sinais:**

- `cardinality ≈ 1.0` (muitas/todas strings únicas)
- `n_unicas ≈ n_rows`
- `cadence_detected = False`
- `body_bytes` grande (próximo de `avg_len * n_rows`)

**Interpretação:**

Cada string aparece poucas vezes (ou uma só). TCF não consegue explorar
repetição. OBAT nem HCC conseguem comprimir bem.

**Exemplo:**

```python
from tcf import build_schema

data = [f"user{i}" for i in range(100)]  # 100 strings únicas
schema = build_schema(data)

col = schema.columns["val"]
print(f"cardinality: {col.cardinality}")  # ~1.0
print(f"body_bytes: {col.body_bytes}")     # ~280 (pior caso)
```

### Padrão 2: Baixa cardinalidade, alta repetição

**Sinais:**

- `cardinality << 1.0` (poucos valores únicos)
- `n_unicas << n_rows` (muita repetição)
- `body_bytes` pequeno (HCC combina bem as repetições)

**Interpretação:**

Excelente compressão. Poucas strings distintas = referências + RLE
comprimem muito.

**Exemplo:**

```python
from tcf import build_schema

data = ["A"] * 50 + ["B"] * 50  # 2 strings únicas
schema = build_schema(data)

col = schema.columns["val"]
print(f"cardinality: {col.cardinality}")  # 0.02
print(f"body_bytes: {col.body_bytes}")     # ~12 (excelente)
```

### Padrão 3: Cadence detectado (padrão repetido)

**Sinais:**

- `cadence_detected = True`
- `cadence_rule` preenchido (ex: `"1-uniform-length-high-lcp-lcs"`)
- `cadence_info['reason']` explica (ex: "high LCP/LCS ratio")
- `body_bytes` moderado (sequência é comprimida de forma eficiente)

**Interpretação:**

Strings variam de forma sistemática (datas incrementais, IPs sequenciais,
etc). OBAT detectou padrão e aplicou shaping. HCC referencia componentes
comuns. Compressão acima da média.

**Exemplo:**

```python
from tcf import build_schema

data = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
schema = build_schema(data)

col = schema.columns["val"]
print(f"cadence_detected: {col.cadence_detected}")  # True
print(f"cadence_rule: {col.cadence_rule}")  # "1-uniform-length-high-lcp-lcs"
print(f"body_bytes: {col.body_bytes}")        # ~25 (boa compressão)
```

### Padrão 4: Numeric + alta cardinalidade (seqüência)

**Sinais:**

- `is_numeric = True`
- `cardinality = 1.0` (cada número aparece uma vez, ou poucos)
- `cadence_detected = True`
- `cadence_rule = "2-numeric-high-cardinality"`

**Interpretação:**

Números sequenciais ou proximais (IDs, índices, timestamps). Mesmo que
aparententemente "únicos", OBAT detecta que diferenças sao incrementais.

**Exemplo:**

```python
from tcf import build_schema

data = ["1", "2", "3", "4", "5"]
schema = build_schema(data)

col = schema.columns["val"]
print(f"is_numeric: {col.is_numeric}")           # True
print(f"cardinality: {col.cardinality}")         # 1.0
print(f"cadence_detected: {col.cadence_detected}") # True
print(f"cadence_rule: {col.cadence_rule}")       # "2-numeric-high-cardinality"
```

## Debug avançado — acessar logs internos

Se você precisa investigar muito mais a fundo, acesse os logs do OBAT
e HCC via SideOutputs:

```python
from tcf import encode
from tcf.side_outputs import SideOutputs

data = ["apple", "apricot", "banana", "blueberry"]

side = SideOutputs()
encode(data, side_outputs=side)

# Log do OBAT (shaping: prefixos/sufixos)
print("=== OBAT Log ===")
print(side.obat_log)

# Trace do HCC (iterations de busca por composições)
print("\n=== HCC Trace ===")
print(side.hcc_trace)

# Rede final (atoms + compositions)
print("\n=== HCC Rede ===")
print(side.hcc_rede)
```

## Connexões

- **Algoritmos:** [`../algorithms/OBAT.md`](../algorithms/OBAT.md),
  [`../algorithms/HCC.md`](../algorithms/HCC.md)
- **Format:** [`../algorithms/TCF-format.md`](../algorithms/TCF-format.md)
- **API pública:** [`../../src/tcf/__init__.py`](../../src/tcf/__init__.py)
