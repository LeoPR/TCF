---
title: T-EXP-H-PERF-05d — Counter incremental em HCC _detect_compositions
status: open
priority: P2
created: 2026-05-22
updated: 2026-05-22
blocked-by: []
related:
  - tickets/META-PERF-PHASE2.md
  - experiments/lab/dirty/2026-05-20-hcc-perf-optimization/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
---

# T-EXP-H-PERF-05d — Counter incremental HCC

## Contexto / motivacao

`_detect_compositions` em `src/tcf/composicional/syntax.py` (Pacote 4
sub-pacote 2). Outer loop:

```python
while True:  # iter N vezes
    contagem = Counter()              # FULL REBUILD cada iter
    for li, pieces in pieces_per_line:
        for p in pieces:
            if p[0] == 'refs':
                for sub in all_subtuples(p[1]):
                    contagem[sub] += 1
    # candidates + pick + substitute
```

Cada iter substitui UMA sub-tupla em LINHAS AFETADAS. Mas `contagem`
e' rebuildada do zero, contando TODAS as linhas (afetadas + nao
afetadas).

**Hipotese H-PERF-05d**: Manter `contagem` entre iters; aplicar DELTA
so' em linhas alteradas:
- Remove counts antigas (sub-tuplas em refs pre-substituicao)
- Add counts novas (sub-tuplas em refs pos-substituicao)
- Linhas nao alteradas: zero trabalho

Ganho potencial estimado: 50-70% no tempo de _detect_compositions
(se 90%+ das linhas nao mudam por iter).

## Status anterior

Sub-exp `2026-05-20-hcc-perf-optimization/`:
- H-PERF-05a/b/c (zero-risk variantes): só 1.04x cumulativo
- H-PERF-05e/f (caps): byte loss 3-6%, viola M9 invariant
- H-PERF-05d (counter incremental): **NAO TESTADO** (complexidade
  state entre iters + invariants)

Lab adiado, META-PERF-PHASE2 CLOSED-PARCIAL.

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-22-h-perf-05d-counter-incremental/`

### Fase 1 — profile granular (sub-exp 01)

Profile `_detect_compositions` em lineitem 5k, breakdown:
- % tempo em rebuild Counter
- % tempo em build candidates loop
- % tempo em _estimate_baseline_chars
- % tempo em substitution loop

**Criterio go/no-go**: se rebuild Counter > 30% do _detect_compositions,
prosseguir pra prototype. Senao, encerrar lab (counter incremental
nao vale).

### Fase 2 — prototype incremental (sub-exp 02)

Fork em dirty (NAO mexer src/tcf):
- Monkey-patch `_detect_compositions` com versao incremental
- Mantem `_contagem_state` entre iters
- Delta apply: remove counts de refs antigos, add counts de refs novos
- Lidar com `sub_first_line` + `alias_first_line` incrementalmente

**Critérios**:
- Bytes IDENTICOS ao canonical em lineitem 1k/5k (zero-risk byte loss)
- RT 100%

### Fase 3 — medir speedup real

Comparar canonical vs incremental:
- lineitem 1k, 5k, possivelmente 10k
- D1-D9 (controle, deve ser identico em bytes e proximo em tempo)

### Fase 4 (condicional) — welding canonical

Se speedup >= 30% E zero byte loss E RT 100%:
- Aprovacao explicita owner pra mexer src/tcf
- ADR-0012 documentando welding
- Re-validacao multi-camada

## Criterio de aceite (KR)

- [ ] Sub-exp 01: profile com breakdown
- [ ] Decisao go/no-go documentada
- [ ] (se go) prototype incremental funcional
- [ ] Bytes IDENTICOS em D1-D9 + lineitem 1k/5k
- [ ] Speedup >= 30% no _detect_compositions (lineitem 5k)
- [ ] (se welding) ADR-0012 + welding canonical aprovado

## Riscos

1. **Complexidade alta**: state entre iters + invariants
   (sub_first_line, alias_first_line). Bugs sutis possiveis.
2. **Byte loss inesperado**: invariant difference entre canonical e
   incremental pode mudar pick order. Mitigacao: byte-canonical test
   obrigatorio.
3. **Welding em src/tcf canonical ja' modificado (ADR-0006/0007)**:
   cuidado extra. Mitigacao: ADR-0012 + re-validacao multi-camada.
4. **Escopo**: pode ser sessao inteira. Prototype primeiro, decidir
   welding depois.

## Conexoes

- [Lab HCC perf (sub-exp anteriores)](../experiments/lab/dirty/2026-05-20-hcc-perf-optimization/)
- [META-PERF-PHASE2](META-PERF-PHASE2.md) — closed-parcial
- [src/tcf/composicional/syntax.py _detect_compositions](../src/tcf/composicional/syntax.py)
- [Roadmap H-PERF-05d](../experiments/lab/dirty/notas/roadmap-hipoteses.md)

## Updates datados

### 2026-05-22 — abertura

Ticket criado seguindo convencao YAML frontmatter. H-PERF-05d era
"candidata futura" desde 2026-05-20 (META-PERF-PHASE2 closed-parcial).
Agora reaberta como prioridade alta apos categoria B residual (H-DA-07)
fechar.

Fase 1 (profile) e' decisor — se Counter rebuild nao for dominante,
encerrar lab.
