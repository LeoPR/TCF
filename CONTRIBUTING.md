<!-- l10n: doc_id=contributing · lang=en · canonical -->
**English** · [Português](CONTRIBUTING.pt-BR.md)

# Contributing to TCF

What you need to work **on** TCF. To *use* it, the [README](README.md) and the
[manual](docs/README.md) are enough.

The canonical guide for conventions, evidence gates and the rules that hold across
the repo is [`AGENTS.md`](AGENTS.md). Start there.

## First-time setup (dev)

```bash
# Clone + install dev deps
git clone https://github.com/LeoPR/TCF.git && cd TCF
pip install -e ".[dev]"

# (recommended) install pre-commit hooks
pre-commit install

# Run hooks on all files (optional, baseline)
pre-commit run --all-files
```

Configured hooks (see [`.pre-commit-config.yaml`](.pre-commit-config.yaml)):
- `ruff` lint + format
- `detect-secrets` (scan)
- basics: trailing-whitespace, end-of-file-fixer, check-merge-conflict, check-added-large-files
- custom: blocks cache dirs (`__pycache__/`, `.pytest_cache/`, etc.) accidentally staged

## Repository layout

```
TCF/
├── src/tcf/                 ← CANONICAL v0.8 API (OBAT+HCC, encode/decode/view, #TCF.8)
├── docs/archive/old/tcf/                 ← v0.5 engine (levels L0–L3), frozen-historical (see LEVELS-REVIEW.md)
├── scripts/                 ← Shaper (stratified sampling), CSV→SQLite, setup_* datasets
├── experiments/lab/         ← v0.8 labs (dirty + clean): compositional compression
├── docs/archive/old/llm-benchmark/       ← LLM benchmark v0.5 (harness: runners + llm_eval), accessory
├── tests/                   ← pytest suite (v0.8)
├── datasets/                ← canonical metadata + samples (real data outside the repo)
├── tickets/                 ← markdown planning (YAML frontmatter)
├── docs/
│   ├── algorithms/          ← canonical v0.8 specs (OBAT, HCC, TCF-format) [reference]
│   ├── adr/                 ← numbered, immutable decisions
│   ├── theory/              ← theoretical foundations [explanation]
│   ├── how-to/, tutorials/  ← Diataxis
│   ├── findings/            ← v0.5 LLM scientific catalog (F-Q01..Q38) [historical]
│   ├── workbench/           ← dev timeline, research notes (parts in _archive/)
│   └── archive/             ← frozen v0.5/v0.1 material (manual_v05, article_v05, etc.)
├── config/                  ← storage.json (points to the data root), api_keys (gitignored)
├── README.md                ← you are here
└── CHANGELOG.md             ← release history
```

> For the detailed map, see [MAP.md](MAP.md). The `docs/manual/`
> and `docs/article/` directories do NOT exist; the corresponding v0.5 material is in
> `docs/archive/manual_v05/` and `docs/archive/article_v05/`.

---

## Tools shipped (v0.8)

The encoder is the main tool; support helpers (NOT TCF-core):

- **Shaper** (`src/shaper/`): stratified, FK-preserving sampling framework.
  Standalone-able as a separate library; see
  [shaper-as-standalone-tool note](docs/archive/workbench/research-notes/_archive/2026-04-25-shaper-as-standalone-tool.md)
- **DatasetReader** (`scripts/dataset_reader.py`): uniform interface
  over SQLite hubs (rows, columns, query, column_stats)
- **setup_\*.py** (`scripts/`): download/generation of the canonical datasets
  (Adult, TPC-H, IBGE, CNPJ, etc.); see [datasets/README.md](datasets/README.md)

> Pre-1.0: **library-only** (no CLI; see `pyproject.toml`).
> The LLM benchmark v0.5 (CommercialClient, M-series runners) lives in
> [`docs/archive/old/llm-benchmark/`](docs/archive/old/llm-benchmark/), with reproduction instructions in its own README.

---
