# Changelog

History of TCF condensed into logical versions. For commit-level detail
see `git log`. For per-experiment timeline (v0.5) see
[`docs/workbench/_archive/DEVELOPMENT.md`](docs/workbench/_archive/DEVELOPMENT.md);
for v0.6 (atual) ver
[`experiments/lab/dirty/notas/historia-dirty-lab.md`](experiments/lab/dirty/notas/historia-dirty-lab.md).

A partir de v1.0.0 o versionamento e' **semver** com format `#TCF.6`
congelado (ADR-0017). Versoes anteriores marcavam milestones logicos
internos (sem PyPI). Date em parenteses = consolidacao do milestone.

> **Reframe 2026-06-14 (ADR-0024)**: o projeto e' **pré-1.0**. O rotulo
> "1.0.0 STABLE / format congelado" abaixo deve ser lido como um milestone
> interno, NAO um contrato de compat. Os minors do formato (`#TCF.4/.5/.6/.7`)
> sao iteracoes de dev rumo a um 1.0 solido; git reproduz versoes antigas. O
> pacote voltou pra `0.7.0`.

---

## 0.7.x (pré-1.0, em andamento) — `#TCF.7` default

Ciclo "perseguir bytes" (abertura do que era chamado v2.0; agora pré-1.0).
`encode(dict)` multi-col sai em `#TCF.7` por default. Single-col inalterado.

- **V2-A fallback identity** ([ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)):
  por coluna `min(tcf, raw)`, marcador `!`.
- **Header minimo** ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)):
  meta sem prefixo `# ` + ultima coluna sem size.
- **V2-B dicionario/categorico** ([ADR-0025](docs/adr/0025-v2b-dictionary-categorical-weld.md)):
  3o candidato do fallback `min(tcf, raw, v2b)`, marcador `@`. Coluna low-card
  vira [tabela de unicos]+[stream de indices]. 13.9% weighted em 8 datasets reais.
- **`sort_by` order-free** (O-FMT-02): `encode(table, sort_by="col")` reordena
  linhas pela chave (decode retorna a ordem ordenada).
- **Knobs**: `fallback`/`min_header` (opt-out, default True), `min_len` (override).
- **0.7 default** ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)):
  baseline D17a re-pinado 322->303B (#TCF.6 legado lido pelo decoder). D1-D9=1523B
  (single-col) inalterado. Suite 385 passed.

---

## 1.0.0 (2026-05-27) — **STABLE** — format #TCF.6 + API congelados

Primeira versao estavel. Decisao formal de freeze em
[ADR-0017](docs/adr/0017-format-spec-v1-frozen.md).

### Estabilidade garantida (semver)

- **Format `#TCF.6` imutavel** ate' v2.0.0 — nenhum byte de arquivo TCF
  v1 muda entre versoes 1.x.y
- **API publica congelada**: `encode`, `decode`, `SideOutputs`,
  `PipelineConfig`, `build_schema`, `TableSchema`, `ColumnSchema`,
  `TemplatedCheckedSpec`, `TemplatedPaddedSpec`, `SPEC_CPF`, `SPEC_CNPJ`,
  `SPEC_IP` (+ deprecated `encode_table`/`decode_table`)
- **Semver**: 1.0.x bug fixes / 1.x.0 additive / 2.0.0 breaking

### Validado

- D1-D9 sinteticos: 1523B (53.2% ratio), RT 9/9
- D17a multi-col: 322B INVARIANT (preservado em 16 ADRs)
- Real-world: Adult Census + TPC-H 9 tabelas (-33.02% weighted) + 3 UCI
  novos (wine 90.9%, beijing 71.7%, online-retail 23.7%)
- Benchmark vs csv/jsonl + gzip/brotli/zstd: TCF vence 7/9 datasets
- Suite: 262 passed + 2 xfailed (test_regression_v1_baseline.py: 24
  tests gate byte-canonical + API surface)

### Bug fixes incluidos (categoria 1 — output era invalido)

- HCC seq-RLE multi-delta: marker `*N+-1,0|...` (primeiro delta negativo
  double-signed) era emitido mas decoder rejeitava com `ValueError`.
  Fix em `src/tcf/composicional/hcc_seqrle.py`. Descoberto em validacao
  real-world wine-quality (2026-05-27). 2 testes regressao.

### Packaging

- `pyproject.toml`: version 1.0.0; wheel empacota `src/tcf` canonical
  (corrigido de `old/tcf` v0.5 stale); `requires-python = ">=3.10"`
- `src/tcf/__init__.py`: `__version__ = "1.0.0"`
- CI: gate bloqueante `test_regression_v1_baseline.py` + PYTHONHASHSEED=0
  + matrix py 3.10-3.13

### Deprecated (removido em 2.0.0)

- `encode_table(table)` → use `encode(dict)`
- `decode_table(text)` → use `decode(text)`

---

## v0.6 (2026-05-10 → 2026-05-27) — TCF (Tabular Compact Format) — superseded por 1.0.0

**Reset em 2026-05-10**: foco do projeto migrou de "formato textual
columnar para LLMs" (v0.5) para **algoritmo de compressao de strings
tabulares** em duas camadas. Trabalho em `experiments/lab/dirty/`
(macros M0-M14) consolidado e welded para `src/tcf/`. Estabilizado
como 1.0.0 em 2026-05-27.

### Naming oficializado (2026-05-17, META-NAMING)

- **TCF** = **Tabular Compact Format** (projeto)
- **OBAT** = **Online Bidirectional Affix Tokenizer** (codnome `alg16`)
- **HCC** = **Hierarchical Compositional Coding** (codnome `M8.A`)

Ver `docs/algorithms/` para documentacao tecnica detalhada de cada
camada.

### Componentes canonicos

- **OBAT** (camada 1, tokenizacao): online incremental via LCP+LCS
  bidirecional. Tokens raiz: TokLit / TokRefPref / TokRefSuf.
  Intocado desde M0 (exp 16 do alg16).
- **HCC** (camada 2, compactacao): detector unificado (refs atomicos
  + virtuais no mesmo espaco) + emit composicional (`~` cria ref
  auto-nomeado, `,` concat efemero); restricao body-order para
  inline expansion correto; range `a..b` como caso particular.
- **Convencao output**: sem brackets `[`/`]`, LF only.

### Resultados validados

- D1-D9 (stress 9 datasets sinteticos): 1615 bytes em 2981 raw =
  **54.2% ratio medio**. Varia 26% (D8 cabeca-cauda) a 72% (D4 caos).
- RT 9/9 OK em todos os datasets.
- Cadeia byte-canonica: M9 → M10 → M11 → M12 → M13 → M14 (welding
  validado por contra-prova).

### Estado da API

```python
from tcf import encode, decode  # API publica v0.6

text = encode(["abc", "abcd", "abcde"])
values = decode(text)
```

### Phase 1 LLM (acessorio)

LLM benchmark (Q01-Q38 em `docs/findings/`) e' agora **acessorio**
ao foco. Codigo v0.5 (`old/tcf/`, antes `src/tcf/`) mantido para
referencia historica.

Ver:
- [`experiments/lab/dirty/notas/historia-dirty-lab.md`](experiments/lab/dirty/notas/historia-dirty-lab.md) — narrativa M0-M14
- [`experiments/lab/dirty/notas/roadmap-hipoteses.md`](experiments/lab/dirty/notas/roadmap-hipoteses.md) — 12 direcoes futuras
- [`docs/algorithms/`](docs/algorithms/) — OBAT, HCC, TCF-format

---

## v0.3-research (2026-04-27) — research-grade (HISTORICA)

**Repository reorganization**: GitHub-style README, manual with 7 chapters
(EN + 3 PT-BR), findings catalogue split by theme into `docs/findings/`,
workbench (tickets + research notes + dev/science timelines) under
`docs/workbench/`, theory snapshot under `docs/theory/`. Removed obsolete
`data/` and `data-local/` from repo root. Tickets moved from
`tickets/` to `docs/workbench/tickets/`.

**M-schema-scope finished**: F-Q37 (schema scope doesn't degrade N0;
sub-finding: models infer `Supplier#NNN` from lexical patterns even
without `supplier` table visible — TPC-H memorization caveat) and F-Q38
(schema reduced **helps** in natural wordings: -33pp in N3 between
minimal and full schemas — empirically justifies schema pruning literature).

## v0.2.6-anthropic (2026-04-26) — Anthropic family added

`commercial_client.py` extended for Anthropic Messages API:
- haiku 4.5 + sonnet 4.6 with `thinking={"type":"enabled","budget_tokens":2048}`
- opus 4.7 with `thinking={"type":"adaptive"}` + `output_config.effort`
  (different API!)
- 1968 records over 4 paradigms × 7 commercial models. Total spend
  $9.46 USD with prompt caching (~75% savings).

Findings:
- **F-Q36**: Anthropic ≈ OpenAI in Linha B (96-99% Adult, 80-88% TPC-H);
  OpenAI wins Linha A Adult (gpt-5.x 82-95% vs Anthropic 76-80%);
  paridade in Linha A TPC-H. claude-sonnet-4-6 wins TPC-H Linha B
  (88.1% > gpt-5.4 85.7%).

## v0.2.5-openai (2026-04-26) — OpenAI commercials

Migrated `commercial_client.py` to **OpenAI Responses API** (recommended
2026 path), added structured outputs via Pydantic, prompt caching with
`prompt_cache_key`, tiktoken-based count_tokens.

Models: gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-4o-mini (control).
1008 records (Linha A + B × Adult + TPC-H), $3.17 USD.

Findings:
- **F-Q31**: commercial reasoning models break the local Linha A ceiling
  (gpt-5.4 95% vs locals capped ~57%). The discriminating axis is
  REASONING, not size.
- **F-Q32**: gpt-5.4 + mini = **100% in all naturalness levels** for
  Adult Linha B.
- **F-Q33**: locals lose -30 to -45pp in TPC-H Linha B with N2
  wording — schema ambiguity systematic in multi-table.
- **F-Q34**: same applies to commercial top models — schema ambiguity
  is universal/paradigm-independent.
- **F-Q35**: Linha A commercial in TPC-H caps at 60-76%; even
  gpt-5.4 falls 21pp from Adult to TPC-H.

## v0.2.4-naturalness (2026-04-26) — naturalness axis (locals only)

Introduced **N0..N3 naturalness taxonomy** for question wordings:
- N0: schema-aware (literal column names, technical hints)
- N1: system-aware (domain-aware prose)
- N2: business-intent (no schema mentions)
- N3: business + implicit context

Implementation: `experiments/eval/llm_eval/question_naturalness.py` with
28 wordings × 2 datasets, runners adapted with `--naturalness` flag.
N0 byte-identical to legacy questions for backwards compat.

Findings:
- **F-Q29**: naturalness does NOT degrade Linha A in 13 local models
  0.6B-20B (delta < 5-14pp, within Wilson CI). Mechanism: arithmetic
  ceiling dominates; wording is invisible below it.
- **F-Q30**: naturalness DEGRADES Linha B in locals selectively (qwen3:14b
  immune; qwen2.5-coder -15pp). Two mechanisms: domain-semantic ambiguity
  + hyphenated columns.

ScoringConfig dataclass added with `string_match=lenient` default
(strict still available for legacy comparability).

## v0.2.3-canonical (2026-04-25) — canonical datasets baseline

`scripts/setup_adult.py` and `setup_tpch.py` for reproducible canonical
ingestion. `scripts/csv_to_sqlite.py` builds SQLite hubs in
`Z:/tcf-data/interim/`. Stratification metrics inline (TVD/JSD/Hellinger/
Wilson CI).

Findings:
- **F-Q24**: canonical TPC-H ≈ synthetic retail in accuracy under same
  protocol — synthetic was representative.
- **F-Q25**: H-TCF2 generalizes to single-table (Adult Census) with
  hyphenated columns. 100% Linha B local.
- **F-Q26**: random ≈ stratified in Adult — paradigm robust to sampling
  choice ("floor effect" of 100% accuracy).
- **F-Q27**: SQL quality structural metric correlates **inversely** with
  accuracy. Discarded.
- **F-Q28**: Linha A in canonical Adult = 52% bimodal (100% on full-table
  agg, 0-11% on filter+agg). Refines F-Q12.

## v0.2.2-shaper (2026-04-25) — unified data pipeline

`scripts/shaper/` framework with 7 strategies (schema_filter, join,
compressibility, stratify, fk_preserving, volume, ordering).
`experiments/eval/data_sources.py` provides single entry point
`load_dataset(source, **kwargs)` for both synthetic and canonical.

All M-runners migrated to `load_dataset` (no more direct fixture imports).

## v0.2.1-mseries (2026-04-15..04-23) — M1..M9 experiment runs

13 M-series runners exploring Linha B (LLM → SQL) systematically across
synthetic and canonical datasets. Findings F-Q13..F-Q23 (schema-only,
fewshot, cross-domain, format, intermediate forms, filter questions,
HAVING, complex queries, error types, style hints).

## v0.2.0-encoder (2026-04-10..04-13) — encoder/decoder v0.2

Rewrote encoder/decoder with separated `compression.py` module.
Public API: `encode`, `encode_rows`, `decode`, `EncodeConfig`. CLI
modernized.

## v0.1-llm-comprehension (2026-04-04..04-10) — Phase 1 LLM testing

Phase 1 ran 12 local models × 4 formats × 4 questions to test LLM
comprehension of TCF. **TCF 43% < JSONL 63%** in raw accuracy — pivot
to Linha B as the high-value path. F-Q1..F-Q12 catalogued.

## v0.0-prototype (2026-04 first week) — initial sketch

First handcrafted draft of the columnar text format. Encoder/decoder
v0.1 written in two weeks (`src/tcf/encoder.py`, `decoder.py`).
Roundtrip CSV → TCF → CSV verified. Format had conceptual issues
(DICT with `=`, `[sorted]` confusing, redundant IDs); kept as
historical reference in `docs/archive/`.

---

## Roadmap (open)

- v0.3: schema_qualifier (auto-prune schema for N2/N3 wordings before LLM)
- v0.3: numeric precision (open issue 23)
- Future: TOON benchmark integration (head-to-head Adult/TPC-H)
- Future: Shaper as standalone pip package
