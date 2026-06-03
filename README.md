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

> O ciclo **v0.5** (formato columnar para LLM benchmark) e' acessorio e
> vive separado — ver a secao "Benchmark LLM v0.5" mais abaixo.

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

## Benchmark LLM v0.5 (acessorio — projeto paralelo)

> Esta secao resume o ciclo **v0.5** (formato columnar para consumo por LLMs).
> NAO e' o algoritmo TCF v0.6 acima. Todo o material vive separado.

O ciclo v0.5 mediu compreensao de tabelas por LLMs (CSV/JSON/TOON/TCF,
Linha A "LLM le e computa" + Linha B "LLM gera SQL"): 7 modelos comerciais
+ 13 locais, 2 datasets, 2256 registros, 38 findings. Usava o **motor de
niveis** (`EncodeConfig(level=N)`) em [`old/tcf/`](old/tcf/) — ver
[`old/tcf/LEVELS-REVIEW.md`](old/tcf/LEVELS-REVIEW.md) para a semantica L0–L3.

- **Harness** (runners, llm_eval, scripts): [`llm-benchmark/`](llm-benchmark/)
- **Catalogo de achados** F-Q01..Q38: [`docs/findings/`](docs/findings/)
  + [`docs/FINDINGS_SUMMARY.md`](docs/FINDINGS_SUMMARY.md)
- **Manual / paper v0.5**: [`docs/archive/manual_v05/`](docs/archive/manual_v05/)
  + [`docs/archive/article_v05/`](docs/archive/article_v05/)

Candidato a spin-off (`tcf-llm-tools`) no futuro. Pode re-validar contra v0.6
se Phase 2 for revivida.

---

## Repository layout

```
TCF/
├── src/tcf/                 ← CANONICAL v0.6 API (OBAT+HCC, encode/decode, #TCF.6)
├── old/tcf/                 ← motor v0.5 (niveis L0–L3), congelado-historico (ver LEVELS-REVIEW.md)
├── scripts/                 ← Shaper (stratified sampling), CSV→SQLite, setup_* datasets
├── experiments/lab/         ← labs v0.6 (dirty + clean) — compressao composicional
├── llm-benchmark/           ← benchmark LLM v0.5 (harness: runners + llm_eval) — acessorio
├── tests/                   ← pytest suite (v0.6)
├── datasets/                ← canonical metadata + samples (dados reais em Z:)
├── tickets/                 ← planejamento markdown (YAML frontmatter)
├── docs/
│   ├── algorithms/          ← specs canonicos v0.6 (OBAT, HCC, TCF-format) [reference]
│   ├── adr/                 ← decisoes numeradas, imutaveis
│   ├── theory/              ← fundamentos teoricos [explanation]
│   ├── how-to/, tutorials/  ← Diataxis
│   ├── findings/            ← catalogo cientifico v0.5 LLM (F-Q01..Q38) [historico]
│   ├── workbench/           ← dev timeline, research notes (partes em _archive/)
│   └── archive/             ← material v0.5/v0.1 congelado (manual_v05, article_v05, etc.)
├── config/                  ← storage.json (aponta Z:), api_keys (gitignored)
├── README.md                ← you are here
└── CHANGELOG.md             ← release history
```

> Para o mapa detalhado, ver [MAP.md](MAP.md). Os diretorios `docs/manual/`
> e `docs/article/` NAO existem — o material v0.5 correspondente esta em
> `docs/archive/manual_v05/` e `docs/archive/article_v05/`.

---

## Tools shipped (v0.6)

O encoder e' a ferramenta principal; auxiliares de suporte (NAO TCF-core):

- **Shaper** (`scripts/shaper/`) — stratified, FK-preserving sampling
  framework. Standalone-able as a separate library; see
  [shaper-as-standalone-tool note](docs/workbench/research-notes/_archive/2026-04-25-shaper-as-standalone-tool.md)
- **DatasetReader** (`scripts/dataset_reader.py`) — uniform interface
  over SQLite hubs (rows, columns, query, column_stats)
- **setup_\*.py** (`scripts/`) — download/geracao dos datasets canonicos
  (Adult, TPC-H, IBGE, CNPJ, etc.); ver [datasets/README.md](datasets/README.md)

> v1.0 e' **library-only** (sem CLI — `pyproject.toml`). O benchmark LLM v0.5
> (CommercialClient, M-series runners) vive em [`llm-benchmark/`](llm-benchmark/),
> com instrucoes de reproducao no README de la'.

---

## Where to go next

- **I want to use TCF in my pipeline** → API v0.6: `from tcf import encode, decode` ([src/tcf/](src/tcf/)); manual v0.6 pendente. v0.5: [docs/archive/manual_v05/](docs/archive/manual_v05/)
- **I want to read the findings** → [docs/findings/](docs/findings/) (v0.5 LLM, historico)
- **I want to run the LLM benchmark** → [llm-benchmark/](llm-benchmark/) (acessorio v0.5)
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
(Ciclo v0.5) Commercial LLM testing supported by personal credits —
total spend $9.46 USD for 1968 records (75% cache savings).
