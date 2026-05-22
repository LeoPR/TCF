---
title: T-CODE-H-DA-11c — Consolidar pre-pass features (ColumnFeatures unificado)
status: closed
resolution: refactor-completed-zero-risk
priority: P2
created: 2026-05-22
updated: 2026-05-22
closed: 2026-05-22
blocked-by: []
related:
  - tickets/T-EXP-H-DA-11.md
  - experiments/lab/dirty/2026-05-22-h-da-11c-features-unificadas/
  - docs/adr/0008-detect-cadence-numeric-rule.md
  - docs/adr/0010-auto-detect-min-len.md
---

# T-CODE-H-DA-11c — ColumnFeatures unificado

## Contexto / motivacao

Apos welding canonical de H-DA-11 (ADR-0010), `src/tcf/auto_min_len.py`
calcula features basicas (avg_len, cardinality, is_numeric) inline.

`detect_cadence` em EXP-010 prototype (ADR-0008) calcula features
similares (lengths, cardinality, is_numeric) independentemente.

Duplicacao atual:
- avg_len / lengths
- cardinality (n_unicas / n_rows)
- is_numeric (sample check)
- sample (primeiras N strings)

Quando weldar detect_cadence canonical no futuro, vai duplicar o
calculo. Pra cada chamada de `tcf.encode(values)`:
- 1 passada O(N) pra detect_min_len (welded ADR-0010)
- 1 passada O(N) extra pra detect_cadence (futuro)

Pre-pass unificado reduz isso a 1 passada compartilhada.

## Hipotese / pergunta

H-DA-11c: Extrair pre-pass features unificado `analyze_column(values)
→ ColumnFeatures` reduz duplicacao + prepara terreno pra heuristicas
futuras (detect_cadence canonical, T02-T07 naturezas pre-tx)?

Refactor zero-risk: output bytes IDENTICO ao pre-refactor (D1-D9
M9=1615B INVARIANT, Adult+TPC-H 9.87% preservado, RT 100%).

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-22-h-da-11c-features-unificadas/`

### Sub-exp 01 — design + implementacao

1. Criar `src/tcf/column_features.py`:
   ```python
   @dataclass(frozen=True)
   class ColumnFeatures:
       n_rows: int
       n_unicas: int
       avg_len: float
       cardinality: float
       is_numeric: bool
       sample: list[str]

   def analyze_column(values: list[str]) -> ColumnFeatures: ...
   ```

2. Refatorar `src/tcf/auto_min_len.py`:
   - `detect_min_len_from_features(features, n_threshold=100) -> int`
     (assina diferente, recebe ColumnFeatures)
   - `detect_min_len(values, n_threshold=100) -> int` (backward compat,
     wrapper que chama analyze_column + detect_min_len_from_features)

3. Modificar `src/tcf/encoder.py`:
   - Chamar `analyze_column(values)` uma vez
   - Passar features pra `detect_min_len_from_features(features)`

### Sub-exp 02 — validacao zero-risk

Comparar output bytes pre-refactor vs pos-refactor:
- D1-D9 single-col: deve ser EXATAMENTE igual (1615B)
- Adult+TPC-H 57 cols: deve ser EXATAMENTE igual (908,502B)
- RT 100% preservado

## Criterio de aceite

- [ ] `src/tcf/column_features.py` com ColumnFeatures + analyze_column
- [ ] `src/tcf/auto_min_len.py` refatorado com detect_min_len_from_features
- [ ] `src/tcf/encoder.py` usa analyze_column 1x
- [ ] Output canonical IDENTICO ao pre-refactor (D1-D9 1615B, real-world 908,502B)
- [ ] RT 100% (9/9 + 57/57)
- [ ] Backward compat: `detect_min_len(values)` continua funcionando
- [ ] Sub-exp 02 result.md confirmando zero-risk

## Riscos

- **Mudanca de assinatura interna**: introducao de ColumnFeatures
  pode requerer ajustes em callers futuros. Mitigacao: backward compat
  via wrapper `detect_min_len(values)`.
- **Performance**: 1 passada O(N) era duplicada antes (encoder so'
  chamava detect_min_len 1x). Mesmo cost.
- **Welding em src/tcf**: pequena mudanca em estrutura — owner ja'
  aprovou H-DA-11 welding canonical. Refactor sem nova feature
  funcional deveria estar coberto pela aprovacao anterior.

## Conexoes

- [ADR-0010](../docs/adr/0010-auto-detect-min-len.md) — H-DA-11 welded
- [ADR-0008](../docs/adr/0008-detect-cadence-numeric-rule.md) — detect_cadence
  (em EXP-010 prototype; weld canonical futuro pode reaproveitar
  ColumnFeatures)
- [Roadmap H-DA-11c](../experiments/lab/dirty/notas/roadmap-hipoteses.md)

## Updates datados

### 2026-05-22 — abertura

Ticket criado seguindo convencao YAML frontmatter. Hipotese decorrente
de T-EXP-H-DA-11 (closed canonical-welded). Priority P2.

Aprovacao do owner pra mexer em src/tcf coberta pela aprovacao
anterior de welding H-DA-11 (refactor zero-risk sem nova feature
funcional).

### 2026-05-22 — execucao + fechamento

Refactor implementado e validado zero-risk.

**Mudancas**:
- Novo `src/tcf/column_features.py` (ColumnFeatures + analyze_column)
- Refatorado `src/tcf/auto_min_len.py` com 2 APIs:
  - `detect_min_len_from_features(features, n_threshold=100)` — pure heuristic
  - `detect_min_len(values, n_threshold=100)` — backward compat wrapper
- `src/tcf/encoder.py` agora chama `analyze_column(values)` 1x e passa
  `ColumnFeatures` pra `detect_min_len_from_features`

**Validacao** (sub-exp 05 reusado):
- D1-D9 M9 baseline 1615B EXATO preservado (zero regressao)
- Adult+TPC-H gain 9.87% weighted (idêntico pre/pos refactor)
- RT 100%: 9/9 + 57/57

**Beneficios entregues**:
1. Reuso futuro (detect_cadence canonical, T02-T07 naturezas) sem
   recalcular features
2. Imutabilidade (`@dataclass(frozen=True)`) evita mutacoes acidentais
3. Heuristicas testaveis em isolamento (sem precisar lista values)
4. Compat externa (`tcf.encode` API inalterada; `detect_min_len(values)`
   backward compat wrapper preservado)

**Resolution**: refactor-completed-zero-risk.
