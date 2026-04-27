# Datasets — TCF

Esta pasta contem **metadados, amostras pequenas e documentacao** dos
datasets canonicos usados no projeto TCF.

**Os dados reais nao vivem aqui.** Eles ficam em `Z:\tcf-data\` (ou onde
voce configurar em `config/storage.json`). Ver
[docs/theory/architecture/storage.md](../docs/theory/architecture/storage.md) para a
estrategia de 3 camadas.

## Como experimentos consomem estes datasets

A partir de 2026-04-25, **TODO** acesso a dados em experimentos passa por
um único ponto de entrada:

```python
from data_sources import load_dataset

# Canonical via Shaper (FK-preserving sampling)
tables, meta = load_dataset(
    "canonical:tpch-sf001",
    volume=100, seed=42,
    schema=["partsupp", "part", "supplier"],
    fact_table="partsupp",
)

# Synthetic via fixture generators (ablacoes controladas)
tables, meta = load_dataset("synthetic:retail_sales", n_orders=100, seed=42)
```

Fluxo:
- `canonical:*` → `scripts/shaper/` (com `fk_preserving` strategy) →
  `scripts/dataset_reader.py` → `Z:/tcf-data/interim/*.db`
- `synthetic:*` → `tests/fixtures/synthetic_v2.py` ou `synthetic_domains.py`

Detalhes completos em
[docs/theory/architecture/data-pipeline.md](../docs/theory/architecture/data-pipeline.md).

## Estrutura

```
datasets/
├── README.md                       (este arquivo)
│
├── canonical/                      metadata de datasets canonicos
│   ├── tpch-sf001/
│   │   ├── metadata.json           (schema, PK, FK, tipos)
│   │   └── README.md               (origem, licenca, como baixar)
│   └── adult-census/
│       ├── metadata.json
│       └── README.md
│
├── samples/                        amostras pequenas (em git, <50KB)
│   ├── tpch-sf001/
│   │   ├── region.csv              (5 rows, ~400B)
│   │   ├── nation.csv              (25 rows, ~2KB)
│   │   └── lineitem-sample.csv     (100 rows de 60K+, ~30KB)
│   └── adult-census/
│       └── adult-sample.csv        (100 rows de 48K+, ~12KB)
│
├── quality-reports/                quality reports (em git, markdown)
│   ├── tpch-sf001.md
│   └── adult-census.md
│
├── questions/                      banco de perguntas com ground truth SQL
│   ├── tpch-sf001.json
│   └── adult-census.json
│
└── poor-reference/                 datasets minimalistas (legacy)
    └── retail-sales-synthetic/
        └── README.md
```

## Como configurar para rodar

Primeira vez:

```bash
# 1. Copie o template de config
cp config/storage.json.example config/storage.json
# Edite para apontar para seu disco (Z:\ por padrao)

# 2. Verifique
python scripts/_paths.py

# 3. Download dos datasets (tickets 04 e 05)
pip install -e ".[datasets]"  # instala duckdb, sklearn, pandas
python scripts/setup_tpch.py  # ~10MB para Z:\tcf-data\external\tpch-sf001\
python scripts/setup_adult.py # ~5MB para Z:\tcf-data\external\adult-census\
```

## Datasets disponiveis

### Canonicos (Fase 1)

- **`canonical/tpch-sf001/`** — TPC-H Scale Factor 0.01
  Padrao da industria desde 1999. 8 tabelas relacional normalizado,
  dominio wholesale retail. ~60K rows na maior tabela.
  Ver `datasets/canonical/tpch-sf001/README.md` para detalhes.

- **`canonical/adult-census/`** — UCI Adult (Census Income) 1994
  Dados demograficos reais dos EUA. 48K rows, 14 colunas, mixed types.
  Ver `datasets/canonical/adult-census/README.md` para detalhes.

### Poor reference (legacy)

- **`poor-reference/retail-sales-synthetic/`** — nosso sintetico antigo
  com nomes minimalistas (Ana, Bruno, Caneta). Mantido para comparacao
  com papers que usam dados similares.

### Backlog documentado

Outros ~18 datasets foram considerados mas nao entraram na Fase 1.
Ver [docs/research-notes/2026-04-10-canonical-datasets.md](../docs/research-notes/2026-04-10-canonical-datasets.md)
para a lista completa com origem, tamanhos e criterios de escolha.

## Por que esta separacao

Ver [docs/theory/architecture/storage.md](../docs/theory/architecture/storage.md)
para explicacao detalhada da estrategia de 3 camadas.

**TL;DR:**
- **Git** e para scripts e metadados pequenos
- **Disco externo** e para dados brutos e derivacoes
- **Amostras pequenas** em git permitem demos sem precisar baixar gigas
- **Config local** (`config/storage.json`) desacopla o codigo do seu disco
