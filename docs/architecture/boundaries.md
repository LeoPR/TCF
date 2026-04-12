# Architecture Boundaries — O que e TCF Core vs Support

## Principio

**TCF core (`src/tcf/`)** e um tradutor de formato. Nao busca dados,
nao conecta a bancos, nao gera datasets. Recebe dados em estruturas
Python genericas e produz texto TCF (encode) ou reconstroi estruturas
a partir de texto TCF (decode).

**Support tools (`scripts/`)** fazem todo o resto: download datasets,
conversao SQLite, sampling, derivacoes, quality reports, ground truth.
Sao ferramentas do projeto de pesquisa, nao do TCF como biblioteca.

**Experiment runners (`experiments/`)** orquestram LLMs via Ollama
e medem accuracy. Tambem nao sao parte do TCF core.

## Fronteiras visuais

```
┌─────────────────────────────────────────────────┐
│  TCF Core (src/tcf/)                            │
│  pip installable, zero deps externas            │
│                                                  │
│  encoder.py  — dados → texto TCF                │
│  decoder.py  — texto TCF → dados                │
│  compression.py — RLE, dict, sort primitivos    │
│  schema.py   — parser de metadata.json          │
│  cli.py      — CLI (encode/decode/info)         │
│  timing.py   — medicao de fases (generico)      │
│                                                  │
│  Aceita:  estruturas Python (dicts, lists)       │
│  Retorna: texto (str) ou estruturas Python       │
│  Deps:    stdlib ONLY                            │
│  NAO sabe de: SQLite, pandas, Ollama, DuckDB    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Support Scripts (scripts/)                      │
│  ferramentas do PROJETO, nao do TCF              │
│                                                  │
│  _paths.py          — storage resolver           │
│  dataset_reader.py  — le SQLite → dicts          │
│  writers/           — CSV/JSONL/MD output        │
│  shaper/            — sampler multidimensional   │
│  setup_*.py         — downloaders                │
│  csv_to_sqlite.py   — conversao                  │
│  quality_report.py  — relatorios                 │
│  compute_ground_truth.py — SQL execution         │
│                                                  │
│  Deps:    sqlite3, duckdb, sklearn, pandas       │
│  (tudo opcional)                                 │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Experiment Runners (experiments/eval/)           │
│  orquestracao de LLMs                            │
│                                                  │
│  run_etapa*.py      — benchmarks                 │
│  run_diagnostic*.py — ablacoes                   │
│  llm_eval/          — Ollama client, metrics     │
│                                                  │
│  Deps:    requests (Ollama HTTP)                 │
│  USA:     TCF core para encode/decode            │
│  USA:     Support scripts para ler dados          │
└─────────────────────────────────────────────────┘
```

## O ponto cinzento (encoder atual)

O encoder atual (`src/tcf/encoder.py`) faz mais do que "traduzir":

```python
def encode(meta_path, data_dir, config) -> str:
    # 1. Le metadata.json (IO)
    # 2. Le CSVs do diretorio (IO + parsing)
    # 3. Faz JOINs (resolve FKs) ← logica de dados, nao de formato
    # 4. Aplica compressao (RLE, sort, dict) ← formato
    # 5. Retorna string TCF
```

Passos 1-3 sao **IO + data loading**, nao traducao de formato. Isso existe
por conveniencia (o encoder foi criado antes da infraestrutura de scripts).

### Refactoring planejado (futuro)

```python
# Core puro (aceita dados ja carregados):
def encode_columns(columns: dict[str, list], *, level=2, stats=True) -> str:
    """Encode dados ja em formato columnar."""
    ...

def encode_rows(rows: list[dict], *, level=2, stats=True) -> str:
    """Encode dados em formato row-oriented."""
    ...

# Convenience wrapper (mantem compat com CLI):
def encode_from_csv(meta_path, data_dir, config=None) -> str:
    """Le CSVs e chama encode_columns internamente."""
    ...
```

Isso separaria claramente:
- `encode_columns` / `encode_rows`: **core puro**, aceita dicts
- `encode_from_csv`: **wrapper** que faz IO, pode viver em `cli.py`
  ou em um modulo `io.py` separado

**Quando fazer:** quando iniciarmos a Fase 2 e o encoder precisar
consumir dados do shaper. Por enquanto o encoder atual funciona.

## O que NAO deve estar no core

| Funcionalidade | Onde vive | Por que |
|----------------|-----------|---------|
| SQLite reader | `scripts/dataset_reader.py` | DB-specific |
| DuckDB TPC-H | `scripts/setup_tpch.py` | Download tool |
| sklearn fetch | `scripts/setup_adult.py` | Download tool |
| Shaper/sampler | `scripts/shaper/` | Experiment infra |
| CSV/JSONL/MD writers | `scripts/writers/` | Baseline formats |
| Ollama client | `experiments/eval/llm_eval/` | LLM specific |
| Quality reports | `scripts/quality_report.py` | Analysis tool |
| Ground truth SQL | `scripts/compute_ground_truth.py` | Validation |

## O que PODE estar no core (discutivel)

| Funcionalidade | Status | Razao |
|----------------|--------|-------|
| `timing.py` | **Ja esta** | Util para qualquer usuario benchmark |
| `schema.py` | **Ja esta** | Parse de metadata (pequeno, util) |
| `encode_from_csv` | **Ja esta** (misturado) | Sera separado |
| torch acceleration | **Futuro** | Se comprovado util, pode ser opcional |
| TOON encoder | **Nunca no core** | Outro formato, vive em scripts |

## Como isso se relaciona com os testes

```
tests/
  test_encode_decode.py        ← testa o CORE (encoder/decoder roundtrip)
  test_compression_benchmark.py ← testa o CORE (compressao)
  test_p01_p02_p03.py          ← testa o CORE (infra de scoring)
  test_timing.py               ← testa o CORE (timing module)
  test_shaper.py               ← testa SUPPORT (shaper)
```

Testes de core rodam **sem SQLite, sem disco, sem datasets canonicos**.
Testes de shaper **precisam** dos SQLite databases (skipam se nao existem).

## Resumo

> **TCF core e um tradutor: dados entram, TCF sai. TCF entra, dados saem.**
> **Tudo o que nao e traducao, e support ou experiment.**
