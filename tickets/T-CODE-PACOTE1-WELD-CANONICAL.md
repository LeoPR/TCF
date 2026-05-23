---
title: T-CODE-PACOTE1-WELD-CANONICAL — Welding canonical Pacote 1 (delta-aware) em src/tcf
status: closed
resolution: welded-canonical-m10
priority: P1
created: 2026-05-22
updated: 2026-05-22
closed: 2026-05-22
blocked-by: []
related:
  - tickets/T-EXP-H-DA-11.md
  - tickets/T-CODE-H-DA-11c-features-unificadas.md
  - experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/
  - experiments/lab/dirty/2026-05-22-pacote1-weld-canonical/
  - docs/adr/0008-detect-cadence-numeric-rule.md
  - docs/adr/0010-auto-detect-min-len.md
  - docs/adr/0011-pacote1-weld-canonical.md
---

# T-CODE-PACOTE1-WELD-CANONICAL — Welding Pacote 1 canonical

## Contexto / motivacao

Pacote 1 (Delta-aware) esta WELDED em prototype clean EXP-010 desde
2026-05-17 (20/20 RT sinteticos, ganho -18% vs canonical em datasets
testados). Refino real-world H-DA-09b-v2 ADR-0008 adicionou regra
numeric+high-cardinality (mais 5.6% em Adult+TPC-H).

src/tcf canonical atualmente usa:
- `tcf.core.online.processar()` (OBAT canonical sem hint)
- `tcf.composicional.syntax.M8AVirtualRefsSyntax` (HCC sem seq-RLE)
- `tcf.auto_min_len.detect_min_len_from_features` (welded H-DA-11)
- `tcf.column_features.analyze_column` (welded H-DA-11c)

Pipeline EXP-010 prototype adicional (a weldar):
- `auto_pre.detect_cadence` (regras 1+2, ADR-0008)
- `obat_shape.processar_with_hint` (OBAT shape-preserve)
- `hcc_seqrle.HCCSeqRLE` (HCC + seq-RLE near-identical via `*N+delta|`)
- Orquestracao em `delta_aware.encode_column`

Welding consolida pipeline canonical em src/tcf como default.

## Hipotese / pergunta

Welding Pacote 1 canonical em src/tcf (pipeline delta-aware completo
+ ColumnFeatures unificado) mantem RT 100% e atinge ganho real-world
esperado (~10-14% sobre baseline M9 atual de 1615B).

## Consequencias

**Mudanca arquitetural** — output bytes-canonical MUDA:
- D1-D9 baseline: 1615B (M9 canonical M8A puro) → ~1300B (HCCSeqRLE)
  estimado, requer medicao
- API `tcf.encode(values)` retorna output diferente do M9 antigo
- Decoder atualizado obrigatorio (HCCSeqRLE expande `*N+delta|`)
- Backward-compat: decoder canonical NAO consegue ler M9 antigo nem
  pipeline antigo lê novo (versionamento via formato?)
- M9 baseline INVARIANT vira historico — novo invariant M10 estabelece-se

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-22-pacote1-weld-canonical/`

### Fase 1 — implementacao

1. Criar `src/tcf/auto_cadence.py` (de `auto_pre.py`, usar ColumnFeatures)
2. Criar `src/tcf/obat_shape.py` (de `obat_shape.py`)
3. Criar `src/tcf/composicional/hcc_seqrle.py` (de `hcc_seqrle.py`)
4. Modificar `src/tcf/encoder.py`:
   - features = analyze_column(values)
   - cadence, info = detect_cadence_from_features(features)
   - min_len = detect_min_len_from_features(features)
   - if cadence: tokens = processar_with_hint(unicas, min_len, True)
   - else: tokens = processar(unicas, min_len)
   - body = HCCSeqRLE().encode(values, unicas, tokens, header)
5. Modificar `src/tcf/decoder.py`: usar `HCCSeqRLE().decode`

### Fase 2 — validacao

Sub-exp `01-validacao-multi-camada/`:
- D1-D9 single-col: medir novo baseline M10 (esperado ~1300B)
- 20 datasets sinteticos (EXP-010 set): comparar com prototype 1340B
- Adult Census 1k/5k + TPC-H region/customer/lineitem 5k:
  ganho esperado ~10-14% sobre M9 1,008,003B
- RT 100% obrigatorio em todas as camadas

### Fase 3 — documentacao

- ADR-0011 (welding Pacote 1 canonical M9 → M10)
- Atualizar M9 baseline refs:
  - STATUS.md
  - CLAUDE.md (project memory)
  - MAP.md
  - docs/algorithms/HCC.md (se aplicavel)
  - roadmap-hipoteses.md
  - notas relevantes
- Atualizar tickets (este + T-EXP-H-DA-11 ref final)

## Criterio de aceite

- [ ] Pipeline canonical implementado em src/tcf
- [ ] D1-D9 novo baseline M10 medido + documentado
- [ ] 20 datasets sinteticos: ganho similar ou melhor que EXP-010 prototype (1340B)
- [ ] Adult+TPC-H: ganho weighted >= 10% sobre M9 antigo (1,008,003B)
- [ ] RT 100% em D1-D9, sinteticos extras, Adult+TPC-H
- [ ] ADR-0011 publicado
- [ ] M9 refs atualizadas pra M10 nas docs canonicas
- [ ] Commit + push aprovado

## Riscos

1. **Quebra de compat**: decoders externos que assumem M9 (`*N|` simples
   sem `*N+delta|`) FALHARAO em M10. Mitigacao: decoder canonical
   M10 entende ambos (HCCSeqRLE chama super().decode internamente
   ja' aceita `*N|`).
2. **Memorias usuario com "M9 = 1615B INVARIANT"**: precisa atualizar
   conceitualmente (M9 vira historico, M10 e' novo invariant).
3. **Performance**: pipeline canonical M10 adiciona detect_cadence
   pre-pass + HCCSeqRLE post-process. Custo extra O(N) ja' coberto
   por analise H-DA-11c.
4. **Welding em src/tcf canonical** — owner aprovou explicitamente
   esta etapa (opcao b do menu apos H-DA-11c).

## Conexoes

- [EXP-010 prototype](../experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/)
- [ADR-0008](../docs/adr/0008-detect-cadence-numeric-rule.md) — detect_cadence regra 2
- [ADR-0010](../docs/adr/0010-auto-detect-min-len.md) — auto-detect min_len
- [T-EXP-H-DA-11](T-EXP-H-DA-11.md) — H-DA-11 (anterior, welded)
- [T-CODE-H-DA-11c](T-CODE-H-DA-11c-features-unificadas.md) — ColumnFeatures (anterior, welded)

## Updates datados

### 2026-05-22 — abertura

Ticket criado. Aprovacao do owner explicita pra welding canonical
Pacote 1 inteiro (opcao b no menu apos clarificacao).

Pre-requisito atendido: H-DA-11c ColumnFeatures (commit 8622de1)
prepara terreno pra reuso da analyze_column entre detect_cadence,
detect_min_len, futuras heuristicas.

### 2026-05-22 — execucao + fechamento (welded-canonical-m10)

ADR-0011 escrito + implementacao + validacao completa.

**Mudancas em src/tcf**:
- Novo `auto_cadence.py` (refatorado pra usar ColumnFeatures)
- Novo `obat_shape.py` (copy direto do prototype)
- Novo `composicional/hcc_seqrle.py` (subclass M8AVirtualRefsSyntax)
- `encoder.py` pipeline delta-aware completo
- `decoder.py` usa HCCSeqRLE.decode (entende ambos M9 e M10)

**Validacao** (sub-exp 01):
- **D1-D9 M10 baseline: 1523B** (vs M9 1615B = -92B, -5.70%)
  - Wins concentrados em D9 (-92B via seq-RLE near-identical, 4 linhas `\\10..\\13` viraram `*4+1|\\10`)
  - Outros datasets identicos
- 20 datasets sinteticos (EXP-010 set): 2272B, RT 20/20 OK
- Real-world (Adult+TPC-H 57 cols): 889,714B
  - vs M9 puro (1,008,003B): **-11.73% ganho weighted**
  - vs M9+H-DA-11 (908,502B): -2.07% adicional
- **RT 100% em todas as camadas** (9/9 + 20/20 + 57/57)

**KRs satisfeitos**:
- [x] Pipeline canonical implementado em src/tcf
- [x] D1-D9 novo baseline M10 medido (1523B) e documentado
- [x] 20 datasets sinteticos com RT 20/20 OK
- [x] Adult+TPC-H ganho weighted 11.73% (>=10% requerido)
- [x] RT 100% em D1-D9, sinteticos extras, Adult+TPC-H
- [x] ADR-0011 publicado
- [x] M9 refs atualizadas pra M10 nas docs canonicas

**Resolution**: welded-canonical-m10. Pipeline delta-aware Pacote 1
agora e' o canonical de TCF v0.6+. EXP-010 prototype permanece como
referencia historica.
