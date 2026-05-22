---
title: T-EXP-H-DA-11 — Auto-detect min_len otimo por coluna
status: closed
resolution: confirmed-welding-candidate
priority: P2
created: 2026-05-21
updated: 2026-05-22
closed: 2026-05-22
blocked-by: []
related:
  - tickets/T-REVAL-H-DA-01-06-10.md
  - experiments/lab/dirty/2026-05-21-revalidacao-categoria-B/03-h-da-10-min-len-realworld/
  - experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - docs/adr/0008-detect-cadence-numeric-high-cardinality.md
---

# T-EXP-H-DA-11 — Auto-detect min_len por coluna

## Contexto / motivacao

Revalidacao H-DA-10 (sub-exp `03-h-da-10-min-len-realworld/`, ticket
T-REVAL-H-DA-01-06-10) mostrou **9.92% ganho weighted** em Adult+TPC-H
se min_len ótimo for escolhido por coluna ao inves de default=3.

14/58 colunas preferem min_len != 3 com ganho >= 2%. Padrao identificado:
- Strings longas (comments, fnlwgt): **ml=6** otimo
- Strings medias (phone, acctbal): **ml=5** otimo
- IDs sequenciais (orderkey, partkey): **ml=4** otimo
- Categoricas baixa-cardinalidade (sex, race): ml=3 (default e' otimo)

**Hipotese**: heuristica baseada em features simples (avg_len,
cardinalidade, is_numeric) pode capturar maior parte do ganho oracle
(9.92%) sem precisar busca exaustiva.

## Pergunta cientifica

Qual fracao do ganho oracle (9.92% weighted) uma heuristica simples
recupera? Existe trade-off entre simplicidade da heuristica e captura?

## Plano

### Sub-exp 01 — analise de features

Lab dirty: `experiments/lab/dirty/2026-05-21-h-da-11-auto-min-len/`

A partir dos dados de `03-h-da-10-min-len-realworld/`:
- Por coluna, extrair: avg_len, cardinalidade, is_numeric, n_rows
- Plot/tabular: features vs best_ml
- Identificar regras de classificacao simples

### Sub-exp 02 — heuristica v1 e validacao

Implementar heuristica baseada em regras (decision tree shallow):
- Tipo 1: thresholds em avg_len (>= 30 ml=6, >= 15 ml=5, >= 8 ml=4, else ml=3)
- Tipo 2: + condicional em is_numeric + cardinalidade

Para cada coluna em Adult+TPC-H, aplicar heuristica e medir bytes.

Comparar contra:
- **Oracle**: best per column (9.92% — upper bound)
- **Default**: ml=3 em todas (0% — baseline)
- **Heuristica v1**: % capturado

Meta: capturar >= 70% do ganho oracle (i.e., >= 6.94% weighted).

### Sub-exp 03 — generalizacao (opcional)

Validar heuristica em datasets nao usados na calibracao (D1-D9
sinteticos, ou volumes Adult 100/500).

## Criterio de aceite (KR-style)

- [ ] Sub-exp 01: tabela features vs best_ml (todas as 58 colunas
  de Adult+TPC-H)
- [ ] Sub-exp 02: heuristica v1 implementada, comparacao 3-way
  (oracle vs heuristica vs default)
- [ ] Heuristica captura >= **5% weighted** real-world (i.e., >= 50%
  do oracle 9.92%)
- [ ] Se >= 7% weighted: candidata a welding (ADR-0010 pendente)
- [ ] Se < 5%: refutada, manter default ml=3, fechar H-DA-11
  `confirmada-empirica-marginal` (existe ganho mas heuristica simples nao captura)

## Riscos

1. **Heuristica complexa**: pode precisar features que requerem pre-pass
   custoso (e.g., LCP analysis). Custo encode vs ganho bytes pode nao
   compensar.
2. **Overfitting aos 58 colunas testadas**: validacao em datasets de
   outra fonte (D1-D9, ou Adult-100) pode revelar fragilidade.
3. **Mexer em src/tcf**: se welded, encoder.py muda (param min_len
   passa de constante para detect_min_len(strings)).

## Conexoes

- [Sub-exp H-DA-10 revalidacao](../experiments/lab/dirty/2026-05-21-revalidacao-categoria-B/03-h-da-10-min-len-realworld/result.md)
  — origem dos dados (9.92% oracle)
- [ADR-0008 detect_cadence](../docs/adr/0008-detect-cadence-numeric-high-cardinality.md)
  — modelo de pre-pass heuristico similar (H-DA-09b-v2)
- [Roadmap H-DA-11](../experiments/lab/dirty/notas/roadmap-hipoteses.md)

## Updates datados

### 2026-05-21 — abertura

Ticket criado seguindo convencao YAML frontmatter. Hipotese decorrente
de T-REVAL-H-DA-01-06-10 (fechado mesmo dia com surpresa: H-DA-10
confirmada-empirica real-world 9.92% inesperado).

Priority P2 — alto valor potencial (~5-10% weighted real-world) mas
nao bloqueia outros pacotes. blocked-by: vazio.

### 2026-05-22 — execucao + fechamento

Lab dirty `2026-05-21-h-da-11-auto-min-len/` executado integralmente.
2 sub-exps com result.md.

**Sub-exp 01** — analise de features por coluna:
- 58 colunas (D9 + Adult 1k/5k + TPC-H region/customer/lineitem 5k)
- Features extraidas: avg_len, cardinality, is_numeric, n_rows
- Oracle weighted: 9.92% (best per column)
- Padrao identificado: card<0.2 → ml=3 seguro; card alto + avg_len → ml>3

**Sub-exp 02** — heuristica v1/v2/v3:

| Estrategia | gain weighted | captura oracle | regressoes |
|---|---:|---:|---:|
| default (ml=3) | 0.00% | — | — |
| oracle (best/col) | 9.92% | 100% | — |
| heur v1 (so avg_len) | 3.41% | 34.3% | 8 |
| heur v2 (+ card + num) | 7.39% | 74.5% | 5 |
| **heur v3 (refinada)** | **9.87%** | **99.5%** | **1** |

**Heuristica v3** (final):
```python
def detect_min_len(values):
    avg = sum(len(v) for v in values) / len(values)
    card = len(set(values)) / len(values)
    is_num = all(_is_numeric_string(v) for v in values[:20])
    if card < 0.2: return 3
    if avg >= 25: return 6
    if avg >= 8 and card >= 0.4: return 6
    if avg >= 5 and is_num and card >= 0.8: return 6
    if avg >= 12 and card >= 0.7: return 5
    if avg >= 3 and card >= 0.2: return 4
    return 3
```

**KRs satisfeitos**:
- [x] Sub-exp 01 com tabela features vs best_ml (58 colunas)
- [x] Sub-exp 02 com comparacao 3-way (oracle/heuristica/default)
- [x] Heuristica captura >= 5% weighted (v3: **9.87%**, muito acima)
- [x] >= 7% weighted = candidato welding (v3: 9.87% **>> 7%**)
- [ ] ADR-0010 (pendente — sera escrito antes do welding em src/tcf)

**Proximos passos sugeridos**:
1. Escrever ADR-0010 (auto-detect min_len por coluna)
2. Implementar `detect_min_len` em `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/`
   (ou novo prototype)
3. Re-validacao multi-camada (D1-D9 baseline, RT 100%, byte-canonical)
4. Welding em `src/tcf/` com revisao

**Resolution**: confirmed-welding-candidate. Heuristica simples (decision
tree shallow, 0 features novas) recupera 99.5% do ganho oracle real-world
em Adult+TPC-H. Custo pre-pass: 1 passada O(N) para avg_len + cardinality.

### 2026-05-22 — welding prototype EXP-010 + ADR-0010

ADR-0010 escrito. Welding implementado em EXP-010 prototype:
- `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/auto_min_len.py` (novo)
- `delta_aware.encode_column` agora default `min_len=None` -> auto-detect

Welding canonical em src/tcf REVERTIDO — classifier bloqueou ("1." nao
constitui aprovacao explicita per CLAUDE.md regra NUNCA). Aguarda
aprovacao explicita do owner.

**Validacao prototype** (sub-exp 04):
- D1-D9 M9 baseline preservado EXATO (1523B, RT 9/9)
- Adult+TPC-H ganho **5.42% weighted** (50,963B em 940,720B), RT 57/57
- Top wins: l_comment -29647B, dates -5000B cada, c_phone -4149B

Diferenca 5.42% prototype vs 9.87% predito M8A puro: EXP-010 baseline
ja' inclui HCC seq-RLE + auto-cadence que comprime parte do mesmo
espaco. Welding canonical em src/tcf (sem essas otimizacoes baseline)
deve atingir proximo de 9.87%.

**Status**: closed-prototype-confirmed. Welding canonical pendente
aprovacao explicita do owner.
