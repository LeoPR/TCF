# MAP — TCF project wayfinding

> 1-pagina mapa visual. Se voce sabe O QUE quer, encontre AONDE aqui.
> Se nao sabe o que quer, comece em `STATUS.md`.

## Mapa de alto nivel

```
TCF/
├── CLAUDE.md ............. guia pra Claude Code (project scope)
├── MAP.md ................ este arquivo
├── STATUS.md ............. ponto de entrada bibliografico
├── README.md, CHANGELOG.md
├── ROADMAP.md ........... o que fazer, em tiers (pré-1.0 / 2.0 / pesquisa-spinoff)
│
├── src/tcf/ .............. ALGORITMO CANONICO (M10 baseline; intocado sem aprovacao)
│   ├── core/online.py .... OBAT (canonical)
│   ├── obat_shape.py ..... OBAT shape-preserve hint (ADR-0011)
│   ├── composicional/syntax.py ... HCC M8.A
│   ├── composicional/hcc_seqrle.py ... HCC + seq-RLE near-identical (ADR-0011)
│   ├── auto_cadence.py ... detect_cadence (ADR-0008/0011)
│   ├── auto_min_len.py ... detect_min_len (ADR-0010, H-DA-11)
│   ├── column_features.py  ColumnFeatures + analyze_column (H-DA-11c)
│   ├── encoder.py, decoder.py .... API publica (pipeline delta-aware)
│   ├── multi/ ................... encode/decode multi-coluna (core.py + dict_v2b.py; #TCF.7/8 M)
│   ├── schema.py ................. build_schema per-tabela (CORE)
│   ├── side_outputs.py ........... SideOutputs (efeito colateral opt-in)
│   ├── view.py .................. view lazy/consultavel read-only (A4, `from tcf import view`)
│   ├── natures/ .................. pre-tx por natureza (CPF/CNPJ/IP, ADR-0015)
│   ├── _core/detect.pyx .......... acelerador Cython opcional (ADR-0020)
│   └── __init__.py
│
├── scripts/ .............. FERRAMENTAS DE SUPORTE (nao e' TCF-CORE)
│   ├── dataset_reader.py . le SQLite hubs em Z:
│   ├── shaper/ ........... sampler multidimensional
│   ├── _paths.py ......... resolve storage via config
│   ├── setup_adult.py, setup_tpch.py
│   ├── benchmark_*.py
│   └── writers/
│
├── datasets/
│   ├── synthetic/ ........ CSVs pequenos no repo (D1-D17)
│   └── canonical/ ........ metadata only (dados em Z:)
│
├── config/
│   └── storage.json ...... aponta pra Z:/tcf-data/
│
├── Z:/tcf-data/ .......... DADOS GRANDES (fora do repo)
│   └── interim/{adult-census,tpch-sf001}.db
│
├── docs/                  # mapeamento Diataxis local (ver ADR-0012)
│   ├── algorithms/ ....... specs canonicos (OBAT, HCC, TCF-format) [reference]
│   ├── adr/ .............. Architecture Decision Records
│   ├── theory/ ........... fundamentos teoricos [explanation]
│   ├── how-to/ ........... guias tarefa
│   ├── vocabulary.md ..... termos controlados
│   ├── findings/ ......... findings consolidados
│   ├── workbench/ ........ research notes (algumas em _archive/)
│   └── archive/ .......... v0.5 obsoleto (NAO USAR)
│
├── experiments/lab/
│   ├── clean/EXP-NNN-*/ .. prototypes consolidados
│   └── dirty/
│       ├── notas/ ........ narrativa + diario + roadmap + checkpoints
│       ├── 2026-*/ ....... labs ativos (3) + baseline-consolidado
│       └── old/ .......... labs historicos
│           ├── M0-M14/ ... pre-canonical (NAO USAR salvo historia)
│           ├── welded/ ... pos-canonical welded em src/tcf/
│           └── refuted/ .. pos-canonical refutados/insufficient-gain
│
└── tickets/, tests/
```

## "Quero fazer X" — onde olhar

| Quero... | Va para |
|---|---|
| Entender o projeto | `STATUS.md` -> aqui (`MAP.md`) -> `docs/algorithms/TCF-format.md` |
| Saber o estado atual | `STATUS.md` |
| Ver historico do dia | `experiments/lab/dirty/notas/diario/YYYY-MM-DD.md` |
| Retomar de uma pausa | `experiments/lab/dirty/notas/checkpoints/` |
| Adicionar/usar dataset real | `scripts/dataset_reader.py` + `scripts/shaper/` |
| Adicionar dataset sintetico | `datasets/synthetic/` + `README.md` la |
| Entender OBAT (tokenizer) | `docs/algorithms/OBAT.md` |
| Entender HCC (composicional) | `docs/algorithms/HCC.md` |
| **Portar o CORE pra C/Rust** (estruturas + fronteira CORE↔HOST) | `docs/algorithms/core-data-model.md` |
| **Capacidade dos SPECS/natures** (mapa único + EnumSpec no-go + self-describing) | `experiments/lab/dirty/notas/specs-capacity-map.md` |
| **Estrutura + plano do #TCF.8** (família self-describing, features, sequência, cross-dict, tcfx) | `experiments/lab/dirty/notas/tcf8-estrutura-plano.md` |
| **Bibliografia / literatura** (column-store Abadi/Parquet/Dremel, bitpacking, DSL — 24 refs) | `docs/reference/bibliografia.md` |
| **Arquitetura share × header × lazy** (balanço compressão↔lazy; cross-dict FECHADO; header=índice) | `experiments/lab/dirty/notas/arquitetura-share-header-lazy.md` |
| Ver hipoteses ativas/fechadas | `experiments/lab/dirty/notas/roadmap-hipoteses.md` (registry **ativo**; homônimo em `docs/theory/` é histórico) |
| Entender a **familia RLE** (linha/stream/intra-valor) | `experiments/lab/dirty/notas/rle-familia-estudo.md` |
| **V2-RLE-STREAM** (follow-up V2-B) | `experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md` + registry Pacote 11-bis |
| **Lazy/queryable view** (descomprimir o minimo) | `src/tcf/view.py` (`from tcf import view`; A4) · reference `docs/reference/lazy-view.md` · design 0.9 `experiments/lab/dirty/notas/hquery01-decode-dag-indices-design.md` |
| Knobs de encode + view (reference) | `docs/reference/encode-knobs.md`, `docs/reference/lazy-view.md` |
| Entender uma decisao tomada | `docs/adr/` (numerada) ou `experiments/lab/dirty/notas/diario/` |
| Continuar um sub-experimento | `experiments/lab/dirty/<lab>/<sub-exp>/README.md` |
| Comparar EXP-010 ao baseline | `experiments/lab/clean/EXP-010-*/report.md` |
| Format do .tcf | `docs/algorithms/TCF-format.md` |
| Convencao de header | `docs/algorithms/TCF-format.md` + ADRs |
| Welding pra src/tcf | `experiments/lab/dirty/notas/welding-plan.md` |
| Ideias futuras de formato | `experiments/lab/dirty/notas/futuras-otimizacoes-formato.md` |
| Adicionar novo lab | `experiments/lab/dirty/YYYY-MM-DD-name/` |
| Adicionar EXP clean | `experiments/lab/clean/EXP-NNN-name/` |

## Pontos cegos (evitar confusao)

- `docs/archive/` — v0.5 OBSOLETO. **Nao use.**
- `experiments/lab/dirty/old/` — labs historicos antigos. **Nao use** salvo
  pra entender historia.
- `old/tcf/` — motor v0.5 (niveis L0–L3), **congelado-historico**. Existe
  definitivamente; `src/tcf/` (canonical v0.7) tem acoplamento ZERO com ele.
  Semantica dos niveis revista em
  [`old/tcf/LEVELS-REVIEW.md`](old/tcf/LEVELS-REVIEW.md). **Nao use** salvo historia.
- `llm-benchmark/eval/` — benchmark LLM v0.5 (acessorio; reorg concluida,
  era `experiments/eval/`). **Nao e' TCF-core.**

## Entradas de lab atualmente ativas

Faxina 2026-06-21: 17 labs movidos pra `old/welded/` ou `old/refuted/`
(inclui naturezas-e-camada e cpf-templated-checked). Labs vivos:

- `experiments/lab/dirty/2026-05-24-benchmark-formats-compression/` —
  benchmark csv/json/tcf x gzip/brotli/zstd (TCF vence 4/6); `out_files/` removidos
- **`experiments/lab/dirty/2026-05-27-baseline-consolidado/`** —
  baseline de referencia (METRICS + ADRs-INDEX + lessons-learned + run-baseline.py)
- `experiments/lab/dirty/2026-06-19-lazy-testbank/` — banco de testes lazy A1/A2/A3
- `experiments/lab/dirty/2026-06-21-gdict-caracterizacao/` — B1 cross-dict (H-GDICT) + B2 design/revisao
- `experiments/lab/dirty/2026-06-27-gdict-b2-prototype/` — B2 prototype (formato `&<G>` RT-lossless) + gate N≥5 (FALHOU)
- `experiments/lab/dirty/2026-07-01-crossdict-emprestimo-indices/` — reabertura cross-dict + teste-teto (FECHADO)
- `experiments/lab/dirty/2026-07-01-dict-highcard/` + `2026-07-01-descapar-v2b/` — DICT-HIGHCARD → descapar V2-B (byte-safe)
- `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/` —
  prototype antigo (referencia historica)
- `experiments/lab/clean/EXP-011-multi-column-basic/` — multi-col basico

Referencia (old/, mas ainda consultado):
- `experiments/lab/dirty/old/welded/2026-05-24-cpf-templated-checked/` — CPF/IP
  lab que gerou ADR-0015 + ADR-0016 (14 sub-exps)

Pos-0.7 (2026-06, ainda referencia):
- `experiments/lab/dirty/old/welded/2026-06-16-lazy-query/` — PoC lazy view (gadget
  `scripts/tcf_lazy/`, H-QUERY-01)
- `experiments/lab/dirty/old/refuted/2026-06-16-staged-and-ordering-brotli/` — TCF+brotli em
  escala + ordenacao codec-dependente
- `experiments/lab/dirty/old/refuted/2026-06-16-number-nature-caracterizacao/` — number-nature (PARK)
- `experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/` — RLE no stream
  V2-B (CLOSED-geral / nicho textual-puro ABERTO)
- `experiments/lab/dirty/2026-06-19-lazy-testbank/` — A1/A2/A3 do lazy (banco de
  testes vs oraculo + bug de contagem + otimizacao do caminho do algoritmo)
- `experiments/lab/dirty/old/refuted/2026-06-19-header-rows-vs-bytes/` — teste de proporcao
  header linhas-vs-bytes (row-count REFUTADO; base-94 candidato)
- Notas de design recentes (em `notas/`): `v08-plano-etapas.md` (plano 0.8),
  `rle-familia-estudo.md`, `dict-referencia-hipoteses.md` (H-REF),
  `hquery01-decode-dag-indices-design.md`, `transmissao-api-onde-tcf-importa.md`
  (guia de transmissao), `f2-nature-mark-header-design.md`, `cep-outer-dict-codebook-pesquisa.md`

Labs **historicos** (NAO modificar, NAO continuar):
- `experiments/lab/dirty/old/M0-M14/` — fase v0.6 inicial pre-canonical
- `experiments/lab/dirty/old/welded/` — 10 labs welded apos M14 (ADRs
  0008/0010/0011/0012/0013/0014 etc.)
- `experiments/lab/dirty/old/refuted/` — 7 labs refutados ou
  closed-insufficient-gain

## Manutencao deste mapa

- Update quando criar lab/EXP novo
- Update quando mover/remover entrada importante
- Single-source: este arquivo NAO duplica conteudo, so' aponta
- Cross-links sao "information scent" (Morville)
