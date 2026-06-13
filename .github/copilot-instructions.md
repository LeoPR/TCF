# TCF — Copilot Instructions

> **Fonte canonica: [`CLAUDE.md`](../CLAUDE.md) na raiz.** Este arquivo e' uma
> re-expressao destilada pra GitHub Copilot (mesma autoridade, nao uma segunda).
> Em duvida ou conflito, `CLAUDE.md` vence. Detalhe completo la'.

## Projeto em 1 paragrafo

**TCF** (Tabular Compact Format) v0.6 — compressao de strings tabulares,
formato TEXTUAL e inspecionavel (nao compete com gzip/brotli). Pipeline:
pre-pass (`analyze_column`, `detect_cadence`, `detect_min_len`) → **OBAT**
(Online Bidirectional Affix Tokenizer) → **HCC** (Hierarchical Compositional
Coding + seq-RLE). API: `from tcf import encode, decode`. Formato `#TCF.6`
congelado (ADR-0017). Codigo canonical em `src/tcf/`.

## Onde estao as coisas

- `src/tcf/` — **CANONICAL v0.6 (NAO MODIFICAR sem aprovacao explicita)**.
  OBAT em `core/online.py`, HCC em `composicional/`, natures em `natures/`.
- `old/tcf/` — motor v0.5 (niveis L0-L3), congelado-historico. NAO importar.
- `scripts/` — ferramentas de suporte (shaper, dataset_reader, setup_*,
  schema_gadget). NAO e' TCF-core.
- `llm-benchmark/` — benchmark LLM v0.5 (acessorio). NAO e' TCF-core.
- `datasets/canonical/` — APENAS metadata+sample no git; dados reais em `Z:/tcf-data/`.
- `docs/adr/` — decisoes numeradas imutaveis. `STATUS.md`/`MAP.md` — wayfinding.
- `tickets/` — planejamento markdown (YAML frontmatter).

## Antes de agir (checklist)

- Antes de propor download/recriar dataset/infra: `Glob scripts/**`,
  `Glob datasets/**`, `Grep` termos relacionados, checar `Z:/tcf-data/`.
- Antes de modificar lab `closed`/`superseded`: NAO modificar; abrir novo.
- Mudanca que toca HCC `_detect_compositions`/pre-pass/prune: **DEVE** passar
  `tests/test_real_world_snapshots.py` (gate byte-canonical real-world).

## Invariantes (byte-canonical)

- D1-D9 = 1523B, D17a = 322B — pinados em `tests/`. Nao quebrar.
- RT lossless sempre: `decode(encode(x)) == x`.

## NUNCA

- Modificar `src/tcf/` sem aprovacao explicita.
- Push pra GitHub / pra main sem solicitacao explicita.
- Commit com `Co-Authored-By:`. Skip hooks (`--no-verify`).
- Superlativos ("incrivel", "melhor", "vencedor", "descoberta").
- Baixar dados externos quando infra `Z:/tcf-data/` existe.
- `git reset --hard` / `git push --force` sem aprovacao.

## Filosofia

TCF supoe **dados felizes** (sadios). Gadgets auxiliares (schema/quality)
so' ALERTAM, NUNCA arrumam. Vocabulario sobrio (descrever observado, nao
superlativo). Reportar bytes SEMPRE com round-trip validado.

> ⚠️ Repo vive dentro do OneDrive — se `git log` mostrar HEAD estranho ou
> aparecer arquivo `*-DESKTOP-*`, e' conflito de sync conhecido (ver ADR-0021).
