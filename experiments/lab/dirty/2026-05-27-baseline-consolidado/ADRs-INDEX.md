# ADRs-INDEX — Indice navegavel 0001-0017

Sumario de 1-linha + onde codigo correspondente vive + qual lab dirty
originou.

| ADR | Titulo | Codigo (src/tcf/) | Lab origem |
|---|---|---|---|
| [0001](../../../../docs/adr/0001-tcf-format-spec.md) | TCF format spec (magic, LF, UTF-8) | format core | M0-M8 (`old/`) |
| [0002](../../../../docs/adr/0002-shebang-version.md) | Shebang versioning `#TCF.N` | `decoder.py` magic check | M8 |
| [0003](../../../../docs/adr/0003-clean-output-no-brackets.md) | Sem brackets no output | `composicional/syntax.py` | M8 |
| [0004](../../../../docs/adr/0004-multi-column-header-format.md) | Meta `# size=name,size=name` | `multi.py` | `old/welded/2026-05-23-multi-column-scaling` |
| [0005](../../../../docs/adr/0005-naming-tcf-obat-hcc.md) | Naming: TCF/OBAT/HCC | docstrings | META-NAMING decisao |
| [0006](../../../../docs/adr/0006-hcc-virtual-refs.md) | HCC virtual refs (M8.A) | `composicional/syntax.py` | M8 |
| [0007](../../../../docs/adr/0007-obat-bidirectional-affix.md) | OBAT bidir LCP+LCS | `core/online.py` | M0 |
| [0008](../../../../docs/adr/0008-detect-cadence-rules.md) | detect_cadence regras 1+2 | `auto_cadence.py` | `old/welded/2026-05-17-OBAT-delta-aware` |
| [0009](../../../../docs/adr/0009-side-outputs-recipient.md) | SideOutputs pra debug/stats | `side_outputs.py` | Pacote 1 |
| [0010](../../../../docs/adr/0010-detect-min-len.md) | detect_min_len v3 + gating n>=100 | `auto_min_len.py` | `old/welded/2026-05-21-h-da-11-auto-min-len` |
| [0011](../../../../docs/adr/0011-pipeline-canonical-m10.md) | Pipeline canonical M10 | `encoder.py`, `obat_shape.py`, `hcc_seqrle.py` | `old/welded/2026-05-22-pacote1-weld-canonical` |
| [0012](../../../../docs/adr/0012-column-features-unified.md) | ColumnFeatures unified pre-pass | `column_features.py` | `old/welded/2026-05-22-h-da-11c-features-unificadas` |
| [0013](../../../../docs/adr/0013-multi-column-tcf-format.md) | Multi-col `#TCF.6 M` | `multi.py` | `old/welded/2026-05-23-multi-column-scaling` |
| [0014](../../../../docs/adr/0014-unified-encode-decode-api.md) | API unificada `encode(list\|dict)` | `__init__.py`, `encoder.py` | Discussao apos 2026-05-23 |
| [0015](../../../../docs/adr/0015-natures-spec-protocol.md) | Naturezas: SPEC_CPF/CNPJ/IP | `natures/` | `2026-05-24-cpf-templated-checked` (ativo) |
| [0016](../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md) | HCC seq-RLE multi-delta | `composicional/hcc_seqrle.py` | `2026-05-24-cpf-templated-checked` sub-exp 14 |
| [0017](../../../../docs/adr/0017-format-spec-v1-frozen.md) | Format #TCF.6 + API frozen em v1.0 | `__init__.py` `__version__`, `pyproject.toml` | Sprint 1/2/3 v1.0 (2026-05-27) |

## Quais ADRs sao byte-canonical-preservadores

- 0011, 0012, 0013, 0014, 0015, 0016 — **default config preserva
  D1-D9 byte-canonical** (validado em `test_pipeline_config.py`)
- 0008-0010 — pre-pass detection, output identico no caso default

## Quais ADRs introduzem novo body syntax

- 0006: virtual refs (espaco `~` + ID)
- 0011: marcador seq-RLE `*N|template`
- 0013: header multi `#TCF.6 M` + linha meta
- 0016: marcador seq-RLE multi-delta `*N+d1,d2,...|template`

## ADRs em discussao / pendentes

Ver [`../../../../docs/adr/README.md`](../../../../docs/adr/README.md)
e tickets `tickets/T-CODE-*` para ADRs candidatos
(T-CODE-LAYERED-PIPELINE Fase 2, T-CODE-ENCODER-MANAGER Fase 2+,
schema_builder Fase 3 com nature detection).
