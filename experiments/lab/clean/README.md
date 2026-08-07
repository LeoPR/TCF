# clean/ — experimentos finalizados

Experimentos com ID `EXP-NNN-tema-curto`. Cada um tem README,
run.py, config, manifest, report, figures.

> **Regra**: experimento clean **nao muda** depois de fechado.
> Re-runs geram NOVO `EXP-NNN-v2-...`.

## Evolucao por ciclo

### Ciclo v0.5 (2026-04 → 2026-05-09) — LLM benchmark

Experimentos comparando formatos textuais (CSV, JSON, TCF v0.5,
TOON) em compressao + accuracy LLM em tarefas tabulares.

| EXP | Tema | Status |
|---|---|---|
| EXP-001 | CSV baseline (encode/decode/timing/bytes) | foi (v0.5) |
| EXP-002 | TCF baseline (vs CSV de EXP-001) | foi (v0.5) |
| EXP-003a | Calibracao CSV + compressor generico | foi (v0.5) |
| EXP-003b | TCF vs gzip (HP-T1) | foi (v0.5) |
| EXP-004 | Format bench formal | foi (v0.5) |
| EXP-004b | Sintaxe compacta no header (variante B) | foi (v0.5) |
| EXP-004c | Header shebang `#TCF.5 SRDM` | foi (v0.5) |
| EXP-005 | Progressao de formatos em datasets escalonados | foi (v0.5) |
| EXP-006 | Flag P (Affix-DICT) em identificadores | foi (v0.5) |

Esses experimentos sao do **ciclo anterior** (formato columnar para
LLM). Validos como historico; **NAO sao canonicos do v0.6**.

### Ciclo v0.6 (2026-05-10 → em curso) — algoritmo TCF-CORE

EXP-007 foi o primeiro experimento clean do v0.6, apos o welding do
algoritmo (alg16 + M8.A composicional) do dirty para `src/` — ver
[`../dirty/notas/2026-05/welding-plan.md`](../dirty/notas/2026-05/welding-plan.md).
Dai em diante o ciclo segue ativo.

| EXP | Tema | Status |
|---|---|---|
| **EXP-007** | Prototipo TCF-CORE (`from tcf import encode, decode`) validado vs M14 baseline | **foi** (fechado 2026-05-17; RT 9/9 OK, byte-identico a M14) |
| EXP-008 | TCF vs gzip/brotli/zstd/lzma/bz2 (4 formatos x 15 datasets) | foi |
| EXP-009 | Pre-tx por natureza — meta-pasta (sub-experimentos nascem ao fechar macros dirty) | stub |
| EXP-010 | Prototipo delta-aware do Pacote 1 (single-column, 20/20 RT) | ativo |
| EXP-011 | Multi-column basic (per-coluna independente, RT OK em D17a) | ativo |
| EXP-012 | Real-world Adult Census via shaper (RT 4/4 OK) | foi |
| EXP-013 | Real-world TPC-H, 8 tabelas (RT 8/8 OK apos ADR-0007) | foi |
| EXP-014 | Escala de performance no lineitem (1k-20k + full 60175) | foi |
| EXP-015 | TCF hierarquico: le CSV e JSON, reverte pros dois (prototipo v0) | foi |
| **EXP-016** | Familia bN/bits: bateria sintetica completa (72 casos, 11 familias, 4 provas por caso) | **foi** (fechado 2026-08-07; 0 falhas, bN ativa em 52) |

## Para entrar

- Para entender ciclo v0.5: ler READMEs de EXP-001..EXP-006.
- Para entender ciclo v0.6: ler
  [`../dirty/notas/2026-05/historia-dirty-lab.md`](../dirty/notas/2026-05/historia-dirty-lab.md).
