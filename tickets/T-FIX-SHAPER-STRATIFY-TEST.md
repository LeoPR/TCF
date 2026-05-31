---
title: T-FIX-SHAPER-STRATIFY-TEST — Corrigir expectativa do test_stratify_proportional
status: closed-done
priority: P4
created: 2026-05-27
closed: 2026-05-31
blocked-by: []
related:
  - tests/test_shaper.py
  - scripts/shaper/strategies/stratify.py
---

# T-FIX-SHAPER-STRATIFY-TEST

## Contexto

Durante a revisao de prontidao v1.0 (workflow 2026-05-27), o unico test
falhando da suite foi `test_shaper.py::TestShaperStratify::test_stratify_proportional`.

Investigacao concluiu que e' **bug do teste, nao do algoritmo**:

- `test_stratify_proportional` pede `volume=100, stratify_by="sex"` no
  Adult Census e assert `sexes["Male"] == 50 and sexes["Female"] == 50`.
- Mas stratify **proporcional** espelha a distribuicao da populacao.
  Adult Census tem ~67% Male / ~33% Female. Logo amostra de 100 deve dar
  ~67 Male / ~33 Female — que e' o que o algoritmo retorna (correto).
- A expectativa 50/50 confunde "proporcional" com "balanceado/equal".

## Estado atual

Marcado `@pytest.mark.xfail(strict=False)` em 2026-05-27 com nota
explicativa. Suite v1 fica verde. Tooling de suporte (`scripts/shaper/`),
NAO faz parte do TCF-CORE — nao bloqueia v1.0.

## Plano (fix)

Opcao A (corrigir teste — provavel correto):
- Trocar assert pra `sexes["Male"] == 67 and sexes["Female"] == 33`
  (ou ranges tolerantes ~67/~33 com rounding)
- Remover xfail

Opcao B (se quiser stratify balanceado tambem):
- Adicionar parametro `balance=True` em ShapeRequest pra equal-split
  explicito, e criar teste separado pra cada modo

## Resolucao (2026-05-31)

Opcao A. `test_stratify_proportional` agora asserta ~67/33 (Male>Female,
ranges tolerantes) sem xfail. Resolvido junto com T-SHAPER-SCIENTIFIC-GATING,
que adicionou validacao estatistica formal (chi2+TVD) em
`test_shaper_scientific.py::TestP2`. Rounding de stratify.py confirmado correto.

## Criterio de aceite

- [x] Decidir Opcao A ou B → Opcao A (corrigir teste)
- [x] test_stratify_proportional passa sem xfail
- [x] Confirmar que stratify.py rounding esta' correto pro caso proporcional
      (validado por TestP2 chi2_p>0.05 + TVD<0.02)

## Conexao

- Descoberto em revisao v1.0 readiness (workflow 2026-05-27)
- Nao-bloqueante pra v1.0 (tooling, nao formato/algoritmo)
