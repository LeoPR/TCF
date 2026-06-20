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
| Ver hipoteses ativas/fechadas | `experiments/lab/dirty/notas/roadmap-hipoteses.md` |
| Entender a **familia RLE** (linha/stream/intra-valor) | `experiments/lab/dirty/notas/rle-familia-estudo.md` |
| **V2-RLE-STREAM** (follow-up V2-B) | `experiments/lab/dirty/2026-06-19-v2rle-stream-caracterizacao/result.md` + registry Pacote 11-bis |
| **Lazy/queryable view** (descomprimir o minimo) | `scripts/tcf_lazy/` + `experiments/lab/dirty/notas/hquery01-decode-dag-indices-design.md` |
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
  definitivamente; `src/tcf/` (canonical v0.6) tem acoplamento ZERO com ele.
  Semantica dos niveis revista em
  [`old/tcf/LEVELS-REVIEW.md`](old/tcf/LEVELS-REVIEW.md). **Nao use** salvo historia.
- `llm-benchmark/eval/` — benchmark LLM v0.5 (acessorio; reorg concluida,
  era `experiments/eval/`). **Nao e' TCF-core.**

## Entradas de lab atualmente ativas

Pos-consolidacao 2026-05-27 (17 labs movidos pra `old/welded/` ou
`old/refuted/`):

- `experiments/lab/dirty/2026-05-15-naturezas-e-camada/` — T-tracks
  naturezas pre-tx (parcialmente subsumido por ADR-0015)
- `experiments/lab/dirty/2026-05-24-cpf-templated-checked/` — CPF/IP
  lab que gerou ADR-0015 + ADR-0016 (14 sub-exps; ainda referencia)
- `experiments/lab/dirty/2026-05-24-benchmark-formats-compression/` —
  benchmark csv/json/tcf x gzip/brotli/zstd (TCF vence 4/6)
- **`experiments/lab/dirty/2026-05-27-baseline-consolidado/`** —
  baseline de referencia (METRICS + ADRs-INDEX + lessons-learned +
  run-baseline.py)
- `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/` —
  prototype antigo (referencia historica)
- `experiments/lab/clean/EXP-011-multi-column-basic/` — multi-col basico

Pos-0.7 (2026-06, ainda referencia):
- `experiments/lab/dirty/2026-06-16-lazy-query/` — PoC lazy view (gadget
  `scripts/tcf_lazy/`, H-QUERY-01)
- `experiments/lab/dirty/2026-06-16-staged-and-ordering-brotli/` — TCF+brotli em
  escala + ordenacao codec-dependente
- `experiments/lab/dirty/2026-06-16-number-nature-caracterizacao/` — number-nature (PARK)
- `experiments/lab/dirty/2026-06-19-v2rle-stream-caracterizacao/` — RLE no stream
  V2-B (CLOSED-geral / nicho textual-puro ABERTO)
- Notas de design recentes (em `notas/`): `rle-familia-estudo.md`,
  `hquery01-decode-dag-indices-design.md`, `f2-nature-mark-header-design.md`,
  `cep-outer-dict-codebook-pesquisa.md`

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
