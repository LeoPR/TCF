# Funcionalidades do TCF até o `.8` — 3 tiers (developer / estrutural / nuclear) [referência]

**Data**: 2026-07-22 22:30. Snapshot do surface de features do `#TCF.8` (pacote 0.8.0)
pra estudo + material do F6/README. Fontes: `src/tcf/__init__.py`, `src/tcf/encoder.py`,
`docs/algorithms/TCF-format.pt-BR.md`, índice de ADRs, STATUS. **Estado pré-faxina** —
alguns itens têm defeito conhecido (marcados ⚠); ver
[`2026-07-22-2235-prefaxina-08-plano.md`](2026-07-22-2235-prefaxina-08-plano.md).

## Tier 1 — Disponíveis para o developer (API pública, `from tcf import …`)

| símbolo | uso |
|---|---|
| **`encode(data, …)`** | `data` = `list[str]` (single-col) **ou** `dict[str, list[str]]` (multi-col flat) → `str`. Kwargs: `side_outputs`, `parallel`, `nature`/`nature_per_col`, `layers` (PipelineConfig), `fallback`, `min_header`, `min_len`, `sort_by`, `name`, `stamp`, `drop_names`. |
| **`decode(str)`** | → `list \| dict`; **auto-roteia** pela assinatura (single/multi/`#TCF.8H`/órfão). |
| **`view(…)` · `LazyTCF` · `Filtered`** | consulta lazy read-only (column-pruning, `@dict`/raw, filtros, agregações). |
| **`SideOutputs`** | telemetria interna opt-in (via `side_outputs=`). ⚠ hoje não é zero-custo quando desligada. |
| **`PipelineConfig`** | toggles do pipeline (via `layers=`). |
| **`build_schema` · `TableSchema` · `ColumnSchema`** | schema per-tabela. |
| **`SPEC_CPF/CNPJ/IP` · `TemplatedCheckedSpec` · `TemplatedPaddedSpec`** | naturezas opt-in (via `nature=`). |
| ⚠ **`encode_hierarchical`** | **ERRO — não deveria estar exposto** (viola API unificada ADR-0014; `encode` deveria rotear aninhado). Ver plano de pré-faxina §1. |

**Superfície-alvo do dev (pós-faxina)**: `encode` · `decode` · `view` · `SideOutputs` ·
`PipelineConfig` · `build_schema` + specs. **Sem** `encode_hierarchical`.

## Tier 2 — Estruturais (o formato/wire — como o dado é representado)

- **Assinatura** `#TCF.<minor>` (`.8` default, ADR-0032) + **discriminador de 1 char** → dispatch O(1):
  `M` multi · `H` hierárquico · espaço single+spec · `\n` version-stamp/magic-number · nada = órfão
  single-col (0 B). Desconhecido → **fail-loud** (ADR-0029/0031).
- **Single-col órfão**: header 0 B; contrato imutável, congela no 1.0 (ADR-0030).
- **Multi-col `#TCF.8M`**: header inline, byte-sizes em **HEX**, `min_header` (última coluna sem size),
  **markers por-coluna** `!` raw / `@` dict categórico / `%` split estrutural, escaping de nomes com `\`
  (ADR-0022/0023/0025/0026, T-FMT-NAME-ESCAPING).
- **Hierárquico `#TCF.8H`** (welded, ADR-0033): shredding em colunas, `#count` explícito, **D_json
  completo** (escalares tipados, arrays, null, `\n`/`""` em chave/valor, raiz generalizada
  `#D`/`#E`/`#O`/`#V`), contratos de borda congelados, **schema-order canônica**.
- **RLE estrutural**: `*N|linha` (linhas idênticas adjacentes), ranges `A..B`, seq-RLE
  `*N+delta|template` (ADR-0016).
- **Naturezas self-describing** no header via `:id` (ADR-0027).
- **LF-only, UTF-8**. Legado `.6/.7` cortado (git-as-compat, ADR-0024/0028).

## Tier 3 — Nucleares (o core algorítmico)

- **Camada 0 — pré-pass**: `analyze_column` (features, H-DA-11c) + `detect_cadence` (ADR-0008) +
  `detect_min_len` (ADR-0010).
- **Camada 1 — OBAT** (Online Bidirectional Affix Tokenizer): tokenização bidirecional afixo (LCP+LCS),
  refs (prefixo/sufixo) + literais; **índice hash-trigrama** O(N) amortizado (ADR-0009); shape-preserve hint.
- **Camada 2 — HCC** (Hierarchical Compositional Coding, M8.A): composições recorrentes → refs nomeados
  pairwise; seq-RLE near-identical; **prune top-K** (ADR-0019).
- **Acelerador Cython** opcional (`_core/detect.pyx`, ADR-0020) — byte-equivalente ao fallback puro (T-CI-3).
- **Detecção zero-cost de anomalia** — só alerta via SideOutputs, **nunca arruma** (dados "felizes").
- **Plumbing de SideOutputs** — efeito colateral do encode; gadgets consomem a custo zero (ADR-0014).
  ⚠ ver telemetria na pré-faxina §2.

## Fora do TCF-core (acessórios)

Compressores externos gzip/brotli/zstd (só comparação, não são feature do formato) · gadgets
`src/shaper/`, `src/llm_query/`, `scripts/schema_gadget/`.

## Números medidos (vivem nos testes)

Single-col D1–D9 = 1523 B · multi-col D17a = 300 B · real-world −33% weighted (multi, vs raw).
Fonte: `test_regression_v1_baseline.py` / `test_real_world_snapshots.py` (a prosa aponta, o teste mede).
