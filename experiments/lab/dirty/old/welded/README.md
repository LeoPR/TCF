# dirty/old/welded/ — labs welded apos M14 (pos-2026-05-17)

Labs cujo aprendizado foi **incorporado ao canonical** (`src/tcf/`)
via welding formal (ADR + commit em src/tcf). Movidos pra ca em
2026-05-27 durante consolidacao do dirty lab (ver
[`../../2026-05-25-baseline-consolidado/`](../../2026-05-25-baseline-consolidado/)).

> Diferenca pro `old/` raiz: aqueles eram macros M0-M14 da fase
> inicial v0.6 (pre-canonical). Estes sao trabalhos pos-canonical
> que **incrementaram o `src/tcf/`** alem da baseline M14.

## Indice (ordem cronologica)

| Pasta | Data | Foco | ADR/Welding | Onde foi parar |
|---|---|---|---|---|
| [`2026-05-17-OBAT-delta-aware/`](2026-05-17-OBAT-delta-aware/) | 2026-05-17 | Pacote 1: pre-pass + delta-aware OBAT/HCC | [ADR-0008](../../../../../docs/adr/0008-detect-cadence-rules.md), [ADR-0010](../../../../../docs/adr/0010-detect-min-len.md), [ADR-0011](../../../../../docs/adr/0011-pipeline-canonical-m10.md) | `src/tcf/auto_cadence.py`, `auto_min_len.py`, `obat_shape.py`, `composicional/hcc_seqrle.py` |
| [`2026-05-18-canonical-parser-robustness/`](2026-05-18-canonical-parser-robustness/) | 2026-05-18 | Parser robustness pos-welding | — | Bug fixes em `src/tcf/decoder.py` |
| [`2026-05-19-h-da-09b-refino-real-world/`](2026-05-19-h-da-09b-refino-real-world/) | 2026-05-19 | Refino detect_cadence em real-world | [ADR-0008 update](../../../../../docs/adr/0008-detect-cadence-rules.md) | `auto_cadence.py` regra 2 |
| [`2026-05-19-obat-perf-optimization/`](2026-05-19-obat-perf-optimization/) | 2026-05-19 | OBAT perf phase 1 (LCS opt) | — | `src/tcf/core/online.py` micro-opt |
| [`2026-05-21-h-da-11-auto-min-len/`](2026-05-21-h-da-11-auto-min-len/) | 2026-05-21 | Auto-detect min_len v3 + gating n>=100 | [ADR-0010](../../../../../docs/adr/0010-detect-min-len.md) | `src/tcf/auto_min_len.py` |
| [`2026-05-21-revalidacao-categoria-B/`](2026-05-21-revalidacao-categoria-B/) | 2026-05-21 | Re-validacao de hipoteses Cat-B em real-world | [`revisao-conceitual-2026-05-21.md`](../../notas/revisao-conceitual-2026-05-21.md) | criterio `confirmada-empirica` reforcado |
| [`2026-05-22-h-da-07-shape-preserve-revalidacao/`](2026-05-22-h-da-07-shape-preserve-revalidacao/) | 2026-05-22 | Re-validacao shape-preserve em real-world | confirmada `confianca: Alta` | `obat_shape.py` permanece |
| [`2026-05-22-h-da-11c-features-unificadas/`](2026-05-22-h-da-11c-features-unificadas/) | 2026-05-22 | ColumnFeatures unified pre-pass | — | `src/tcf/column_features.py` |
| [`2026-05-22-pacote1-weld-canonical/`](2026-05-22-pacote1-weld-canonical/) | 2026-05-22 | Welding formal Pacote 1 -> src/tcf | [ADR-0011](../../../../../docs/adr/0011-pipeline-canonical-m10.md) | M10 baseline (1523B em D1-D9) |
| [`2026-05-23-multi-column-scaling/`](2026-05-23-multi-column-scaling/) | 2026-05-23 | Multi-column scaling (Adult+TPC-H) | [ADR-0013](../../../../../docs/adr/0013-multi-column-tcf-format.md), [ADR-0014](../../../../../docs/adr/0014-unified-encode-decode-api.md) | `src/tcf/multi.py`, format `#TCF.6 M`, API unificada |

## Convencao

Cada pasta preservada **intocada apos welding** — codigo dirty NAO
se copia, somente a IDEIA foi extraida pro `src/tcf/` (ver
[`feedback_dirty_lab_filosofia.md`](C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/feedback_dirty_lab_filosofia.md)).

Outputs visiveis (`.tcf`, `outputs/`) preservados pra auditoria
historica (princpio outputs visiveis padrao 2026-05-24).

## Continuidade

Welding mais recente: [ADR-0015 naturezas](../../../../../docs/adr/0015-natures-spec-protocol.md)
+ [ADR-0016 multi-delta seq-RLE](../../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md)
saiu de [`2026-05-24-cpf-templated-checked/`](2026-05-24-cpf-templated-checked/)
(movido pra ca na faxina 2026-06-21 — achado welded, ADR-0015/0016).

Ver tambem [`../../2026-05-27-baseline-consolidado/`](../../2026-05-27-baseline-consolidado/)
pra nova baseline + indices comparativos.
