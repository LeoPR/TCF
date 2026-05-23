# 0011 — Pacote 1 (Delta-aware) welded canonical em src/tcf (M9 → M10)

**Status**: accepted + welded
**Date**: 2026-05-22
**Deciders**: project owner
**Tags**: welding, pacote-1, delta-aware, canonical, hcc-seqrle, obat-shape, baseline-M10

## Context and Problem Statement

Pacote 1 (Delta-aware) estava WELDED em prototype clean EXP-010 desde
2026-05-17, com refino real-world H-DA-09b-v2 (ADR-0008, 2026-05-19).
Pipeline:
- `auto_pre.detect_cadence` (regras 1+2)
- `obat_shape.processar_with_hint` (OBAT shape-preserve)
- `hcc_seqrle.HCCSeqRLE` (HCC + seq-RLE near-identical `*N+delta|`)
- `delta_aware.encode_column` (orquestrador)

`src/tcf` canonical (M9 baseline) usava encoder puro:
- `tcf.core.online.processar` (OBAT canonical sem hint)
- `tcf.composicional.syntax.M8AVirtualRefsSyntax` (HCC sem seq-RLE)
- `tcf.auto_min_len` (welded H-DA-11, ADR-0010)
- `tcf.column_features` (welded H-DA-11c)

API publica `from tcf import encode, decode` operava em M9 baseline
(1615B em D1-D9 single-col). Ganho real-world via H-DA-11 isolado: 9.87%
sobre M9 puro.

Pacote 1 prototype ja' validado (20/20 RT em sub-exp 09 dirty + EXP-010
welded). Owner aprovou explicitamente welding canonical (opcao "b" do
menu apos H-DA-11c).

## Considered Options

### Opcao A — Manter Pacote 1 so' em EXP-010 prototype

API canonical `tcf.encode` so' ganha H-DA-11 (auto_min_len). Pacote 1
inteiro requer importacao manual do prototype. Onus pra usuarios.

### Opcao B — Weld canonical Pacote 1 completo (M9 → M10)

Pipeline canonical vira delta-aware completo:
- `tcf.encode` usa `analyze_column` → `detect_cadence` → `detect_min_len`
  → `processar_with_hint`/`processar` → `HCCSeqRLE`
- Baseline M9 (1615B em D1-D9) muda para M10 (esperado ~1500B)
- Backward compat: decoder M10 (HCCSeqRLE.decode) ainda le outputs M9
  (super().decode pra linhas que nao sao `*N+delta|`)

### Opcao C — Weld parcial (so' HCCSeqRLE, sem obat_shape/detect_cadence)

Mantem pipeline atual mas substitui M8A por HCCSeqRLE. Ganha
near-identical compression mas perde shape-preserve sinergia.

## Decision Outcome

**Opcao B — Welding canonical Pacote 1 completo.**

Justificativa:
- Pipeline ja' validado em EXP-010 prototype (welded 2026-05-17)
- ColumnFeatures (H-DA-11c) prepara terreno pra reuso analise basica
- Ganho real-world esperado: +2-4% adicional sobre M9+H-DA-11
- M10 baseline em D1-D9 esperado: ~1500B (menor que M9 1615B,
  porque HCCSeqRLE comprime runs near-identical mesmo quando hint
  cadence nao dispara — usado pra qualquer ocorrencia de runs
  detectaveis no body M8A canonical)

## Implementacao

### Novos modulos em `src/tcf/`

| Arquivo | Origem | Funcao |
|---|---|---|
| `auto_cadence.py` | `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/auto_pre.py` | `detect_cadence_from_features` (refatorado pra ColumnFeatures) |
| `obat_shape.py` | `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/obat_shape.py` | `processar_with_hint` |
| `composicional/hcc_seqrle.py` | `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/hcc_seqrle.py` | `HCCSeqRLE(M8AVirtualRefsSyntax)` |

### Mudancas em `src/tcf/encoder.py`

Pipeline canonical novo:
```python
def encode(values, header="val"):
    unicas = dedup_preserve_order(values)
    features = analyze_column(values)
    cadence, _ = detect_cadence_from_features(features, unicas)
    min_len = detect_min_len_from_features(features)
    if cadence:
        tokens, _ = processar_with_hint(unicas, min_len=min_len,
                                          prefer_shape_consistency=True)
    else:
        tokens, _ = processar(unicas, min_len=min_len)
    return HCCSeqRLE().encode(values, unicas, tokens, header)
```

### Mudancas em `src/tcf/decoder.py`

Decoder canonical usa HCCSeqRLE (que expande `*N+delta|` e delega a
super().decode):
```python
def decode(tcf_text):
    return HCCSeqRLE().decode(tcf_text)
```

## Validacao empirica

`experiments/lab/dirty/2026-05-22-pacote1-weld-canonical/01-validacao-multi-camada/`

### D1-D9 (baseline)

| Camada | Antes (M9) | Depois (M10) | Delta |
|---|---:|---:|---:|
| D1-emails-simples | 118 | 118 | +0 |
| D2-emails-quote-id | 166 | 166 | +0 |
| D3-stress-substring | 177 | 177 | +0 |
| D4-caos-mix | 113 | 113 | +0 |
| D5-padroes-multiplos | 281 | 281 | +0 |
| D6-poucos-em-ruido | 287 | 287 | +0 |
| D7-aninhamento | 215 | 215 | +0 |
| D8-cabeca-cauda | 100 | 100 | +0 |
| D9-frequencia-alta | 158 | 66 | **-92 (-58%)** |
| **TOTAL** | **1615** | **1523** | **-92 (-5.70%)** |

**RT 9/9 OK**. D9 captura 4 linhas `\\10` `\\11` `\\12` `\\13` em
1 linha `*4+1|\\10` via seq-RLE near-identical.

### EXP-010 set (20 datasets sinteticos)

| Total bytes M10 | RT |
|---:|---|
| 2272B | 20/20 OK |

### Real-world (Adult Census + TPC-H, 57 colunas)

| Comparativo | Bytes M10 | Delta | RT |
|---|---:|---:|---|
| **vs M9 puro (1,008,003B)** | 889,714B | **-118,289B (-11.73%)** | 57/57 OK |
| vs M9 + H-DA-11 (908,502B) | 889,714B | -18,788B (-2.07%) | 57/57 OK |

Welding entrega +2% adicional ao H-DA-11 ja' welded (esperado: HCCSeqRLE
captura runs de dates/IDs adjacentes near-identical em real-world).

## Backward compat

- `decode(tcf_text)` canonical aceita BOTH M9 e M10:
  - M10 (com `*N+delta|template`): HCCSeqRLE expande markers
  - M9 (sem markers near-identical, so' `*N|linha` simples + literais):
    HCCSeqRLE chama super().decode pra qualquer linha que nao seja
    `*N+delta|`, entao M9 e' sub-set processado nativamente
- `encode(values)` canonical SEMPRE produz M10 (output bytes diferente
  do M9 antigo). Callers que dependam de M9 exato precisariam usar
  `M8AVirtualRefsSyntax` diretamente (escape hatch nao publico)

## Pros and Cons

| Opcao | Pros | Cons |
|---|---|---|
| A (manter prototype) | Zero risco src/tcf | Onus UX; canonical fica defasado |
| **B (weld canonical)** | API canonical = pipeline otimizado; reuso ColumnFeatures | Baseline M9 INVARIANT muda → M10; precisa atualizar refs em docs |
| C (weld parcial) | Compromisso | Sem sinergia OBAT shape + HCC seq-RLE |

## M9 → M10 baseline (deprecacao)

**M9 baseline (historico)**: 1615B em D1-D9 single-col com encoder M8A
puro + processar(min_len=3). Validado em sub-exp M9 dirty, EXP-007,
multiplos commits.

**M10 baseline (novo, 2026-05-22)**: **1523B** em D1-D9 single-col
com pipeline canonical delta-aware completo:
- analyze_column → detect_cadence → detect_min_len
- processar_with_hint OR processar
- HCCSeqRLE encode

Memorias/docs com "M9 baseline 1615B INVARIANT" sao **historicas** —
M10 e' o invariant atual. Refs a M9 podem permanecer como contexto
historico apos esta data, mas qualquer novo welding/validacao usa
M10 1523B como baseline.

## Riscos residuais

1. **Decoders externos M9-puro**: nao leem M10. Mitigacao: API publica
   `decode` canonical M10 le BOTH; clientes devem migrar pra esta API.
2. **Documentacao**: STATUS.md, CLAUDE.md, MAP.md, roadmap, etc. tem
   refs a "M9 baseline 1615B" que devem ser atualizadas pra M10.
   Mitigacao: este ADR + commit que weld o codigo atualiza essas refs.
3. **User memorias**: `project_macro_M9_stress.md` e similares
   permanecem como contexto historico (user scope).

## Hipoteses decorrentes (registrar)

- **Performance pipeline canonical**: pre-pass `analyze_column` + 
  detect_cadence + detect_min_len adiciona 3 passes O(N) sobre values
  antes do encode O(N²). Custo despresivel em N pequeno; medir em
  lineitem 60k pra confirmar.
- **detect_cadence weld pode interferir com auto-detect minigl_len**:
  precisa medicao se quando cadence dispara, min_len escolhido pela
  heur v3 ainda e' otimo (ou se hint shape-preserve+min_len precisam
  ser correlatos).

## Cross-references

- [Sub-exp validacao welding](../../experiments/lab/dirty/2026-05-22-pacote1-weld-canonical/01-validacao-multi-camada/)
- [EXP-010 prototype (origem)](../../experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/)
- [ADR-0008 detect_cadence regra 2](0008-detect-cadence-numeric-rule.md)
- [ADR-0009 OBAT trigram index](0009-obat-trigram-index-optimization.md)
- [ADR-0010 auto-detect min_len](0010-auto-detect-min-len.md)
- [Ticket T-CODE-PACOTE1-WELD-CANONICAL](../../tickets/T-CODE-PACOTE1-WELD-CANONICAL.md)
- [Roadmap H-DA-*](../../experiments/lab/dirty/notas/roadmap-hipoteses.md)
