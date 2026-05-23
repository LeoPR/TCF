---
title: T-CI-1 — GitHub Actions CI (pre-commit lint; tests refactor follow-up)
status: open
priority: P3
created: 2026-05-23
updated: 2026-05-23
blocked-by: []
related:
  - tickets/T-CLEAN-1-pre-commit-hooks.md
  - .pre-commit-config.yaml
  - tests/
---

# T-CI-1 — GitHub Actions CI

## Contexto / motivacao

Apos T-CLEAN-1 fechado (pre-commit config criado), proximo passo
natural e' CI continua via GitHub Actions:
- Lint automatico em PRs (pre-commit run --all-files)
- Tests automatizados (pytest)

Mas pesquisa pre-implementacao revelou que `tests/` atual tem
problemas que impedem CI direto:

1. **Imports broken (v0.5 obsoleto)**: 4 arquivos importam APIs que
   nao existem mais em src/tcf/ (encode_columns, encode_rows,
   EncodeConfig, tcf.timing):
   - test_compression_benchmark.py
   - test_encode_canonical.py
   - test_encode_decode.py
   - test_timing.py

2. **Dependencias externas (Z:/tcf-data SQLite)**:
   - test_encode_canonical.py
   - test_shaper.py (73 passing local + 1 fail, mas precisa Z:)

3. **Fixtures missing**:
   - test_p01_p02_p03.py (12 FileNotFoundError)

## Plano

### Fase 1 (este ticket) — CI MINIMAL

Workflow `.github/workflows/ci.yml` que roda:
- Job `lint`: pre-commit run --all-files em Python 3.12 ubuntu
- Job `test`: SKIPPED (TODO ate' tests serem refactored)

Documenta limitacao em README.

### Fase 2 (ticket separado T-CI-2) — fix tests CI-friendly

- Limpar tests broken (v0.5 imports): deletar ou refactor pra v0.6 canonical
- Tests SQLite-dependent: usar fixture com SQLite mock OR rodar so' local
- Tests com fixtures missing: criar fixtures ou marcar @pytest.skip

Apos Fase 2, ativar job `test` no CI.

## Criterio de aceite (Fase 1)

- [ ] `.github/workflows/ci.yml` criado
- [ ] Job lint roda pre-commit + passa em push/PR
- [ ] Badge CI no README.md
- [ ] Ticket T-CI-2 aberto pra Fase 2 (tests fix)

## Riscos

1. **Pre-commit lint pode falhar em codigo legado**: mitigacao —
   workflow tem `continue-on-error` no run inicial; baseline opcional
2. **Performance**: actions tem quota gratis generosa; jobs leves nao
   impactam

## Conexoes

- T-CLEAN-1 (pre-commit config) — pre-requisito
- Metodologia §"Versionamento e higiene" — CI complementa pre-commit

## Updates datados

### 2026-05-23 — abertura

Ticket criado seguindo convencao YAML frontmatter. Fase 1 (lint only)
e' minimal viable CI; Fase 2 (tests) requer refactor de tests legados
(separado em T-CI-2 futuro).
