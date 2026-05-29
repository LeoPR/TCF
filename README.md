# TCF — Tabular Compact Format

[![CI](https://github.com/LeoPR/TCF/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoPR/TCF/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Format](https://img.shields.io/badge/format-%23TCF.6%20frozen-green)

**TCF** e' um formato textual compacto para dados tabulares (single e
multi-column de strings). Algoritmo em duas camadas:

- **OBAT** (Online Bidirectional Affix Tokenizer) — tokenizacao via
  matching LCP+LCS contra strings anteriores.
- **HCC** (Hierarchical Compositional Coding) — compactacao
  composicional com operadores `~`/`,` e auto-naming.

Ver [`docs/algorithms/`](docs/algorithms/) para documentacao tecnica
detalhada de cada camada.

## Getting started (1 minuto)

```python
from tcf import encode, decode

# Single-column: lista de strings
text = encode(["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"])
assert decode(text) == ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]

# Multi-column: dict de colunas
table = {
    "id":    ["1", "2", "3"],
    "email": ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"],
}
text = encode(table)
assert decode(table_text := encode(table)) == table  # round-trip lossless

# Naturezas (opt-in): CPF/CNPJ/IP comprimidos sem digito verificador/padding
from tcf import SPEC_CPF
text = encode(["111.444.777-35", "529.982.247-25"], nature=SPEC_CPF)
```

`encode` dispatcha por tipo (list → single-column, dict → multi-column).
`decode` roteia pelo shebang. Round-trip e' sempre lossless.

Tutorial passo-a-passo: [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md).
Guias praticos: [`docs/how-to/`](docs/how-to/).

## Estado v1.0 (stable)

- Format `#TCF.6` e API publica **congelados** ([ADR-0017](docs/adr/0017-format-spec-v1-frozen.md))
- Implementacao canonica em [`src/tcf/`](src/tcf/)
- D1-D9 sinteticos: **1523 bytes** (53.2% ratio), RT 9/9
- D17a multi-col: **322B INVARIANT** (preservado em 16 ADRs)
- Real-world: Adult Census + TPC-H (-33.02% weighted) + 3 UCI
  (wine/beijing/online-retail). Benchmark: **TCF vence 7/9 datasets**
  vs csv/jsonl + gzip/brotli/zstd
- Suite: 262 passed + 2 xfailed
- Mudancas: ver [`CHANGELOG.md`](CHANGELOG.md). Historia M0-M14:
  [`experiments/lab/dirty/notas/historia-dirty-lab.md`](experiments/lab/dirty/notas/historia-dirty-lab.md)

## Ciclo v0.5 (acessorio)

Codigo v0.5 (formato columnar com RLE/dict/stats para LLM benchmark)
vive em [`old/tcf/`](old/tcf/). NAO e' canonico no v0.6 — material
de Phase 1 LLM Q01-Q38 em [`docs/findings/`](docs/findings/) e'
referencia historica. Pode virar projeto a parte no futuro.

## First-time setup (dev)

```bash
# Clone + install dev deps
git clone https://github.com/LeoPR/TCF.git && cd TCF
pip install -e ".[dev]"

# (recomendado) instalar pre-commit hooks
pre-commit install

# Rodar hooks em todos arquivos (opcional, baseline)
pre-commit run --all-files
```

Hooks configurados (ver [`.pre-commit-config.yaml`](.pre-commit-config.yaml)):
- `ruff` lint + format
- `detect-secrets` (scan)
- basicos: trailing-whitespace, end-of-file-fixer, check-merge-conflict, check-added-large-files
- custom: bloqueia cache dirs (`__pycache__/`, `.pytest_cache/`, etc.) acidentalmente staged

## How to cite

Ver [`CITATION.cff`](CITATION.cff). GitHub renderiza badge "Cite this
repository" na pagina do repo automaticamente.

---

## (v0.5 historico) A compact text format for LLMs to reason over relational tables

> **Nota**: descricao abaixo refere-se ao ciclo v0.5 (acessorio).
> Para o algoritmo TCF v0.6 atual, ver acima.

TCF v0.5 compresses CSV/JSON tabular data via columnar layout + RLE + statistics
hints, without losing roundtrip fidelity. Models read it directly (Linha A)
or use it as schema carrier for SQL generation (Linha B).

```python
# v0.5 API (acessorio):
from old.tcf import encode_rows, EncodeConfig
text = encode_rows("sales", rows, config=EncodeConfig(level=2, include_stats=True))
```

---

## Why TCF?

We benchmarked 7 commercial models (OpenAI gpt-5.x family, Anthropic
haiku/sonnet/opus 4.5-4.7) and 13 local models (qwen3, phi4, gemma3, etc.)
across 2 datasets (Adult Census, TPC-H sf001), 4 paradigms (Linha A
single-table / multi-table, Linha B single-table / multi-table) and 4
levels of question naturalness — **2256 records, 38 findings catalogued**.

### Headline results

| Workload | Best model | Accuracy | Cost / 100 calls* |
|----------|-----------|----------|-------------------|
| Single-table SQL gen | **gpt-5.4-mini** or **claude-haiku-4-5** | 100% / 99% | $0.07 / $0.15 |
| Multi-table SQL gen | **claude-sonnet-4-6** | 88% | $0.29 |
| Single-table read-and-compute | **gpt-5.4** | 95% | $0.73 |
| Local SQL gen (no spend) | **qwen3:14b** (Ollama) | 100% Adult / 95% TPC-H N0 | $0 |

\* with prompt caching, ~75% cheaper than no-cache.

### Compression vs alternatives

For 100-row Adult Census (single table, 15 columns):

| Format | Bytes | Roundtrip? |
|--------|-------|-----------|
| JSON  | ~14000 | ✅ |
| CSV  | ~9000 | ✅ |
| **TCF L2** (RLE + STATS, sorted by `class`) | **~7188** | ✅ |
| TCF L3 (schema-only) | ~470 | ❌ schema |

For 8-table TPC-H sf001 sample, full TCF payload at ~33 KB enables Linha A
in 1-shot context.

### Notable discoveries

- **Schema ambiguity is universal and paradigm-independent** (F-Q33-Q35):
  TPC-H questions like *"what's the most expensive item?"* drop to **0%**
  in N2 wording (mid-naturalness) across **every** commercial top model
  tested — schema linking remains an open problem in 2026.
- **Reasoning is the discriminating axis**, not size: gpt-4o-mini
  (non-reasoning, $0.15/M) falls into local-tier accuracy (52%) while
  gpt-5.4-nano (reasoning, $0.20/M) breaks the local ceiling at 87%.
- **Schema pruning is mandatory for natural wordings** (F-Q38): full
  schema (8 tables) drops 33pp vs minimal (1 table) in N3 — confirms
  Cortex Analyst / DAIL-SQL / CHESS recommendations.

---

## Quickstart

```bash
pip install -e .
```

```python
from tcf import encode_rows, EncodeConfig

text = encode_rows("people", rows, config=EncodeConfig(level=2, include_stats=True))
print(text)
```

CLI:

```bash
python -m tcf encode --meta data/metadata.json --data-dir data/ --level 2 --out out.tcf
python -m tcf decode out.tcf --out-dir restored/
```

→ Full manual: [docs/archive/manual_v05/](docs/archive/manual_v05/) (v0.5 historico — manual v0.6 pendente)

---

## Repository layout

```
TCF/
├── src/tcf/                 ← public encode/decode API
├── scripts/                 ← Shaper (stratified sampling), CSV→SQLite
├── experiments/             ← M-series runners + result manifests
├── tests/                   ← pytest suite
├── datasets/                ← canonical metadata + samples
├── docs/
│   ├── manual/              ← user-facing guide (7 chapters EN, PT-BR partial)
│   ├── findings/            ← scientific catalogue (F-Q1..F-Q38)
│   ├── theory/              ← architecture + methodology snapshot
│   ├── workbench/           ← dev timeline, tickets, research notes
│   ├── article/             ← paper drafts + figures
│   └── archive/             ← legacy v0.1 material
├── config/                  ← API keys (gitignored), storage config
├── README.md                ← you are here
└── CHANGELOG.md             ← release history
```

---

## Comparison with other tabular formats

### vs CSV / JSON

CSV and JSON are the LLM industry default but neither was designed for
LLM consumption. TCF L2 with `include_stats=True` adds a **STATS hint**
line per numeric column with pre-computed `sum/min/max/avg`, which
boosts agg-over-table accuracy from ~60% to ~100% in local 7-14B models
(F-Q8). RLE compresses repeated values typical of low-cardinality
columns (sex, class, region).

### vs TOON

TOON is a sibling effort exploring token-oriented object notation for
LLM-readable tables. We see it as **complementary**: TOON optimizes for
structured nested objects with type-rich notation; TCF optimizes for
flat columnar tables with statistical hints and SQL-friendly schema
emission. We have not benchmarked them head-to-head; if you have TOON
results on Adult or TPC-H with the same protocol (M-Acomm-style), open
an issue and we'll integrate them.

Both formats share the goal of replacing CSV/JSON for LLM input.
Different optimization targets:

|              | TOON                               | TCF                                |
|--------------|-----------------------------------|------------------------------------|
| Primary unit | Nested object / typed structure   | Column / table                     |
| Compression  | Type tags, dictionary             | RLE + DICT + STATS                 |
| Schema       | Inline with values                | Separable (L3 schema-only)         |
| Best for     | Nested config, semi-structured    | Flat tables, NL2SQL, BI            |

---

## Tools shipped

The repo is set up so the encoder is the headline tool, with several
auxiliaries:

- **`tcf` CLI** (`src/tcf/cli.py`) — encode/decode/info on disk
- **Shaper** (`scripts/shaper/`) — stratified, FK-preserving sampling
  framework. Standalone-able as a separate library; see
  [shaper-as-standalone-tool note](docs/workbench/research-notes/2026-04-25-shaper-as-standalone-tool.md)
- **DatasetReader** (`scripts/dataset_reader.py`) — uniform interface
  over SQLite hubs (rows, columns, query, column_stats)
- **CommercialClient** (`experiments/eval/llm_eval/commercial_client.py`)
  — unified client for Anthropic Messages API + OpenAI Responses API,
  with cost tracking, prompt caching, structured outputs, and
  count_tokens validation
- **M-series runners** (`experiments/eval/run_m*.py`) — reproducible
  experiments, each with `--summary` for table view of saved manifests

---

## Reproducing experiments

To regenerate the 38 findings:

1. Set up canonical datasets:
   ```bash
   python scripts/setup_adult.py       # downloads UCI Adult Census
   python scripts/setup_tpch.py         # generates TPC-H sf001 via DuckDB
   python scripts/csv_to_sqlite.py adult-census
   python scripts/csv_to_sqlite.py tpch-sf001
   ```
   See [datasets/README.md](datasets/README.md) for details.

2. For local experiments (no spend):
   ```bash
   ollama pull qwen3:14b qwen2.5-coder:7b phi4:latest
   python experiments/eval/run_m9_adult.py --naturalness all
   python experiments/eval/run_m9_canonical.py --naturalness all
   python experiments/eval/run_m_alocal.py --naturalness all
   python experiments/eval/run_m_schema_scope.py --naturalness all
   ```

3. For commercial experiments ($1-10 USD with caching):
   ```bash
   # Add config/api_keys.json with {"openai":"sk-...","anthropic":"sk-ant-..."}
   python experiments/eval/run_m_acomm.py --dry-run --naturalness all  # validate first
   python experiments/eval/run_m_acomm.py --naturalness all
   python experiments/eval/run_m_acomm_b.py --naturalness all
   python experiments/eval/run_m_acommA_tpch.py --naturalness all
   python experiments/eval/run_m_acommB_tpch.py --naturalness all
   ```

Use `--summary` on any runner to display saved results without re-running.

---

## Where to go next

- **I want to use TCF in my pipeline** → API v0.6: `from tcf import encode, decode` ([src/tcf/](src/tcf/)); manual v0.6 pendente. v0.5: [docs/archive/manual_v05/](docs/archive/manual_v05/)
- **I want to read the findings** → [docs/findings/](docs/findings/)
- **I want to understand the architecture** → [docs/theory/](docs/theory/)
- **I want to read the paper** → drafts v0.5: [docs/archive/article_v05/](docs/archive/article_v05/) (paper v0.6 pendente)
- **I want to see how it evolved** → [CHANGELOG.md](CHANGELOG.md) +
  [docs/workbench/](docs/workbench/)

---

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Project conceived as part of an academic dissertation (TCC). Datasets:
[UCI Adult Census](https://archive.ics.uci.edu/ml/datasets/adult) and
[TPC-H](https://www.tpc.org/tpch/) (via DuckDB tpch extension).
Commercial LLM testing supported by personal credits — total spend
$9.46 USD for 1968 records (75% cache savings).
