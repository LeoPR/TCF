# Changelog

History of TCF condensed into logical versions. For commit-level detail
see `git log`. For per-experiment timeline see
[docs/workbench/DEVELOPMENT.md](docs/workbench/DEVELOPMENT.md).

Versioning is **internal** (we haven't shipped to PyPI). Versions mark
**logical milestones** in the project. Date in parentheses is when the
milestone consolidated.

---

## v0.3-research (2026-04-27) — current — research-grade

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
