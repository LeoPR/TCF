---
title: T-SHAPER-CODE-HARDENING — Hardening de codigo do shaper (escala, dedup, bugs latentes)
status: deferred
priority: P2
created: 2026-05-30
updated: 2026-06-15
blocked-by: []
related:
  - scripts/shaper/pipeline.py  (carga em memoria, except ImportError pass)
  - scripts/shaper/strategies/join.py  (lstrip("lops_") bug latente)
  - scripts/shaper/strategies/stratify.py  (proportional allocation duplicada)
  - scripts/shaper/strategies/fk_preserving.py  (mesma duplicacao + sem teste)
  - T-SHAPER-SCIENTIFIC-GATING (ticket irmao; ataca claims, nao codigo)
---

# T-SHAPER-CODE-HARDENING — Polish do codigo do shaper

> **Fechamento 0.7 (2026-06-15) — PARK pos-0.7**: shaper e' gadget externo paralelo
> (nao TCF-core); 5 acoes de polish/escala >100k (A1-A5) sem impacto em bytes/formato.
> O irmao T-SHAPER-SCIENTIFIC-GATING (integridade dos testes) ja' fechou. Revisitar
> se a escala >100k virar necessidade real.

> **REABERTURA PARCIAL (2026-07-05) — só A1, à luz do assessment de cobertura**: o
> [assessment 2026-07-05](../experiments/lab/dirty/notas/2026-07-05-cobertura-datasets-shaper-assessment.md)
> (gap **G2**) identificou que o tier **XL (>1M linhas)** dos cenários de transmissão é o único
> descoberto na ponta grande, e o **A1 (filter-before-load) é exatamente o bloqueador**: o shaper
> trava >100k porque carrega tudo antes de filtrar. A "escala >100k virar necessidade real" (gatilho
> do PARK acima) **aconteceu** — o eixo idealista-grande do owner + os cenários T2/T6 (cap Lambda
> 6MB / >1M) exigem XL. **A2-A6 seguem PARK**; só **A1** volta pra fila, condicionado à priorização
> do [T-DATA-EDGE-TRANSMISSION-PAYLOADS](T-DATA-TRANSMISSION-GROUPING.md) (decorrente). Não executar
> agora (owner: foco-agora = só assess); reanalisar quando o tier XL for pra frente.

## Contexto

Auditoria de saude de codigo do shaper (2026-05-30, workflow paralelo):
classificacao **NEEDS-POLISH** — codigo funcional, 49/50 tests passam,
6 dimensoes documentadas todas presentes. Mas tem hardening pendente
antes de escala maior e antes de uso em produto.

Especificamente, 5 acoes identificadas. Este ticket as registra.

## Achados

### A1 — Filter-before-load em pipeline (escala)

Atual: `pipeline.py:97-100` chama `reader.rows(table_name)` para
**todas as tabelas** antes de aplicar qualquer strategy. Mesmo
`schema="minimal"` (que descarta tabelas depois) carrega tudo.

Impacto: TPC-H sf=1 lineitem (~6M rows) trava. **Nao suporta dataset
1M+ rows sem refactor.**

Fix: resolver `schema` strategy ANTES de `reader.rows()`. Ordem
correta: schema (filtra lista de tabelas) -> reader.rows(tabela
filtrada) -> demais strategies.

### A2 — Teste unitario para `fk_preserving`

Strategy mais complexa (250 LOC, cascata recursiva, fact-table
detection heuristica) com **zero cobertura**. Ja' coberto em
T-SHAPER-SCIENTIFIC-GATING P1, mas tambem precisa cobertura unit:

- Single-table fallback (sem FK)
- Simple star (TPC-H core: lineitem+orders+customer)
- Cascade chain (TPC-H chain: lineitem->partsupp->part+supplier)
- Fact-table detection com schema balanceado (heuristica pode falhar)
- FK apontando pra tabela ausente (silent warning, sem teste)
- Cascade hitando max_depth=10 (silent break, sem teste)

### A3 — `lstrip("lops_")` bug latente em join.py

`scripts/shaper/strategies/join.py:76` faz:
```python
fk_col.replace("_key", "").lstrip("lops_")
```

`lstrip("lops_")` remove **qualquer combinacao** de l/o/p/s/_. Provavel
intencao: remover prefixos TPC-H (`l_`, `o_`, `p_`, `s_`). Funciona por
acaso em TPC-H mas falha conceitualmente: `lupa_x` perderia letras
indevidamente.

Fix: usar regex explicito ou lookup:
```python
re.sub(r"^[lopsc]_", "", fk_col.replace("_key", ""))
```

### A4 — Extrair proportional allocation duplicada

Mesmo algoritmo de alocacao proporcional (Neyman-style com min-1)
implementado em DUAS copias:
- `scripts/shaper/strategies/stratify.py` linhas 74-108
- `scripts/shaper/strategies/fk_preserving.py` `_stratified_sample_indices` (~80 LOC)

Risco: copias divergem se uma for editada. Fix: extrair para helper
em `scripts/shaper/_stratify_metrics.py` ou novo
`scripts/shaper/_proportional.py`.

### A6 — Lazy-load de strategies e' fragil (descoberto 2026-05-31)

`_load_builtin_strategies()` (pipeline.py) faz `if _STRATEGY_REGISTRY: return`.
Se QUALQUER modulo de strategy for importado antes do 1o `apply()` (e.g.
`from shaper.strategies.schema import SCHEMA_LEVELS`), o registry fica com
SO' aquela strategy, e o early-return silencia TODAS as outras (join, volume,
stratify, fk_preserving, ordering nunca carregam). Sintoma: pipeline roda
parcial sem erro — volume nao amostra, flat nao junta, etc.

Descoberto ao escrever T-SHAPER-SCIENTIFIC-GATING (gate passava no full-suite
mas falhava standalone). Workaround no teste: forcar `_load_builtin_strategies()`
antes de importar schema. Fix real (junto com A5): carregamento idempotente
que registra cada strategy uma vez independente de ordem de import (e.g.
registry como dict por nome, ou import explicito ordenado sem early-return
sensivel a estado pre-existente).

### A5 — Trocar `except ImportError: pass` por re-raise

`pipeline.py:64-67`:
```python
try:
    from .strategies.foo import FooStrategy
except ImportError:
    pass  # silencia erro real
```

Se um strategy quebra na importacao (typo, dependencia removida), o
pipeline simplesmente roda sem ele e ninguem percebe. Strategy
ausente vira "feature ausente sem aviso".

Fix: log warning + raise condicional baseado em config (ou simples
re-raise se a strategy e' obrigatoria — `volume`, `order` sao
core; `compressibility` talvez opt-in).

## Plano

Atacar na ordem (mais valor por hora):

1. **A1 (filter-before-load)** — destrava escala alem de 100k rows
2. **A3 (lstrip bug)** — fix curto, alto valor (correctness latente)
3. **A5 (ImportError silencioso)** — fix curto, debug ergonomico
4. **A4 (dedup proportional)** — refactor moderado, manutenibilidade
5. **A2 (fk_preserving tests)** — coordenado com T-SHAPER-SCIENTIFIC-GATING P1
   (test integrity + unit tests podem viver no mesmo PR ou separados)

## Criterio de aceite

- [ ] A1: `schema` aplicado antes de `reader.rows()`; teste verifica que
      `schema="minimal"` em TPC-H sf=0.1 nao carrega lineitem completo
- [ ] A2: pelo menos 3 testes unitarios pra `fk_preserving` (single,
      star, chain); cobertura cascade + max_depth + missing-FK warnings
- [ ] A3: `lstrip("lops_")` substituido por regex ou lookup; teste
      regressivo com `lupa_x`-like que falharia no antigo
- [ ] A4: helper proportional extraido; ambos `stratify.py` e
      `fk_preserving.py` usando o mesmo
- [ ] A5: import error em strategy emite log warning; strategies
      obrigatorias re-raisam (decidir core vs opt-in)
- [ ] Suite shaper continua verde (50/50, ou 50/0 se A4 envolver
      remover xfail)

## Riscos

- **A1 muda contrato de execucao**: ordem das strategies. Se algo
  externo confiava em ordem antiga, quebra. Mitigar: feature flag ou
  manter ordem mas adicionar pre-filter.
- **A4 refactor toca codigo testado**: precisa rodar suite completa
  pos-fix. Determinismo crucial (seed -> mesma amostra antes/depois).
- **A2 expoe bugs latentes**: pode encontrar problemas em
  `fk_preserving` que demandam fix adicional. OK — descobrir e'
  parte do trabalho.

## Conexao

- **Irmao**: T-SHAPER-SCIENTIFIC-GATING (ataca claims/tests; este ataca
  codigo)
- **Filosoficamente**: shaper e' [gadget auxiliar externo](../CLAUDE.md#filosofia-dos-gadgets-auxiliares),
  nao TCF-CORE. Pero precisa funcionar bem porque alimenta experimentos.
- **Origem**: auditoria 2026-05-30 (workflow paralelo)
- **Custo estimado**: 1-2 sessoes total (A1+A3+A5 curtos; A4+A2 medios)
