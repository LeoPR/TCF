<!-- l10n: doc_id=contributing · lang=pt-BR · source_lang=en -->
[English](CONTRIBUTING.md) · **Português**

# Contribuir com o TCF

O que você precisa para mexer **no** TCF. Para *usar*, o [README](README.pt-BR.md) e o
[manual](docs/README.md) bastam.

O guia canônico das convenções, dos gates de evidência e das regras que valem no repo
inteiro é o [`AGENTS.md`](AGENTS.md). Comece por ele.

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

## Repository layout

```
TCF/
├── src/tcf/                 ← API CANÔNICA v0.8 (OBAT+HCC, encode/decode/view, #TCF.8)
├── docs/archive/old/tcf/                 ← motor v0.5 (niveis L0–L3), congelado-historico (ver LEVELS-REVIEW.md)
├── scripts/                 ← Shaper (stratified sampling), CSV→SQLite, setup_* datasets
├── experiments/lab/         ← labs v0.8 (dirty + clean): compressao composicional
├── docs/archive/old/llm-benchmark/       ← benchmark LLM v0.5 (harness: runners + llm_eval), acessorio
├── tests/                   ← pytest suite (v0.8)
├── datasets/                ← canonical metadata + samples (dados reais fora do repo)
├── tickets/                 ← planejamento markdown (YAML frontmatter)
├── docs/
│   ├── algorithms/          ← specs canonicos v0.8 (OBAT, HCC, TCF-format) [reference]
│   ├── adr/                 ← decisoes numeradas, imutaveis
│   ├── theory/              ← fundamentos teoricos [explanation]
│   ├── how-to/, tutorials/  ← Diataxis
│   ├── findings/            ← catalogo cientifico v0.5 LLM (F-Q01..Q38) [historico]
│   ├── workbench/           ← dev timeline, research notes (partes em _archive/)
│   └── archive/             ← material v0.5/v0.1 congelado (manual_v05, article_v05, etc.)
├── config/                  ← storage.json (aponta a raiz de dados), api_keys (gitignored)
├── README.md                ← you are here
└── CHANGELOG.md             ← release history
```

> Para o mapa detalhado, ver [MAP.md](MAP.md). Os diretorios `docs/manual/`
> e `docs/article/` NAO existem; o material v0.5 correspondente esta em
> `docs/archive/manual_v05/` e `docs/archive/article_v05/`.

---

## Ferramentas entregues (v0.8)

O encoder e' a ferramenta principal; auxiliares de suporte (NAO TCF-core):

- **Shaper** (`src/shaper/`): stratified, FK-preserving sampling framework.
  Standalone-able as a separate library; see
  [shaper-as-standalone-tool note](docs/archive/workbench/research-notes/_archive/2026-04-25-shaper-as-standalone-tool.md)
- **DatasetReader** (`scripts/dataset_reader.py`): uniform interface
  over SQLite hubs (rows, columns, query, column_stats)
- **setup_\*.py** (`scripts/`): download/geracao dos datasets canonicos
  (Adult, TPC-H, IBGE, CNPJ, etc.); ver [datasets/README.md](datasets/README.md)

> Pré-1.0: **library-only** (sem CLI; ver `pyproject.toml`).
> O benchmark LLM v0.5 (CommercialClient, M-series runners) vive em
> [`docs/archive/old/llm-benchmark/`](docs/archive/old/llm-benchmark/), com instrucoes de reproducao no README de la'.

---
