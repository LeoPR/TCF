---
title: T-DIST-RELEASE-0.8.0 — Release do pacote 0.8.0 (workstream C do plano 0.8)
status: blocked
priority: P2
created: 2026-06-21
updated: 2026-06-21
blocked-by: [T-CODE-LAZY-VIEW-PROMOTE, T-DOC-LAZY-REFERENCE, T-EXP-H-GDICT-01]
related:
  - experiments/lab/dirty/notas/v08-plano-etapas.md
  - docs/adr/0024-pre-1.0-versioning-git-as-compat.md
  - .github/workflows/release.yml
---

# T-DIST-RELEASE-0.8.0 (workstream C do plano 0.8)

## Contexto / motivação

Fechar o ciclo 0.8: shipar o pacote com a view lazy promovida (A4) + a reference (A5),
e decidir formato conforme o veredito de B (cross-dict). **ADR-0024**: pacote **0.8.0**
≠ formato **#TCF.8**. `#TCF.7` segue default; `#TCF.8` só entra **se** o cross-dict
weldar (opt-in, default off byte-idêntico).

## Plano

- **C1**: bump `pyproject` + `src/tcf/__init__.__version__` **0.7.1 → 0.8.0**; atualizar
  `test_version_pre_1_0` (pina a versão) — A4 já deixou `EXPECTED_PUBLIC_API` com
  `view`/`LazyTCF`/`Filtered`.
- **C2**: CHANGELOG + STATUS + ROADMAP + MAP + reference (cross-ref); marcar A4/A5 feitos.
- **C3**: tag `v0.8.0` → `release.yml` publica via Trusted Publishing.

## Critério de aceite

- [ ] Versão 0.8.0 consistente (pyproject + `__init__` + teste de versão).
- [ ] Suíte verde (incl. gate real-world) antes da tag.
- [ ] `from tcf import view` no wheel publicado (smoke test pós-build).
- [ ] Decisão de formato registrada: #TCF.7 default (e #TCF.8 só se B entrou).

## Riscos / notas

- **Bloqueado por**: A4 (feito), A5 ([T-DOC-LAZY-REFERENCE](T-DOC-LAZY-REFERENCE.md)),
  e a decisão de B ([T-EXP-H-GDICT-01](T-EXP-H-GDICT-01.md) — entra no 0.8 ou difere 0.9).
- É o **último** da sequência (A → B → C); não destrava nada agora.

## Updates

- **2026-06-21**: aberto, blocked. A4 já fechou; faltam A5 + decisão de B antes de C.
