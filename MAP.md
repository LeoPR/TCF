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
│
├── src/tcf/ .............. ALGORITMO CANONICO (intocado sem aprovacao)
│   ├── core/online.py .... OBAT
│   ├── composicional/syntax.py ... HCC
│   ├── auto_min_len.py ... detect_min_len (ADR-0010, H-DA-11)
│   ├── encoder.py, decoder.py .... API publica
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
├── docs/
│   ├── algorithms/ ....... specs canonicos (OBAT, HCC, TCF-format)
│   ├── adr/ .............. Architecture Decision Records
│   ├── theory/ ........... fundamentos teoricos
│   ├── vocabulary.md ..... termos controlados
│   ├── findings/ ......... findings consolidados
│   ├── workbench/ ........ research notes (algumas em _archive/)
│   └── archive/ .......... v0.5 obsoleto (NAO USAR)
│
├── experiments/lab/
│   ├── clean/EXP-NNN-*/ .. prototypes consolidados
│   └── dirty/
│       ├── notas/ ........ narrativa + diario + roadmap + checkpoints
│       ├── 2026-*/ ....... labs ativos
│       └── old/ .......... labs historicos (NAO USAR)
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
- `old/tcf/` (se existir) — motor v0.5 obsoleto.

## Entradas de lab atualmente ativas

- `experiments/lab/dirty/2026-05-17-OBAT-delta-aware/` — Pacote 1 delta-aware (welded EXP-010)
- `experiments/lab/dirty/2026-05-21-escape-deduction/` — Pacote 2 CLOSED-INSUFFICIENT-GAIN
- `experiments/lab/dirty/2026-05-21-revalidacao-categoria-B/` — T-REVAL hipoteses (3 sub-exps)
- `experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/` — H-DA-11 WELDED canonical (ADR-0010)
- `experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/`
  — T01 (superseded por Pacote 1; nao continuar)
- `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/` — single-column delta-aware
- `experiments/lab/clean/EXP-011-multi-column-basic/` — multi-column basico

## Manutencao deste mapa

- Update quando criar lab/EXP novo
- Update quando mover/remover entrada importante
- Single-source: este arquivo NAO duplica conteudo, so' aponta
- Cross-links sao "information scent" (Morville)
