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

# T-DIST-RELEASE-0.8.0 (workstream C — release do ciclo lazy)

> **RETIFICAÇÃO (ADR-0028, 2026-06-24)**: este ticket é o **release `0.7.2`** (lazy + poda, formato
> `#TCF.7` inalterado), NÃO 0.8.0. O minor só move com mudança de formato → `0.8.0` fica reservado
> pro `#TCF.8` (cross-dict). **Filename/ID `T-DIST-RELEASE-0.8.0` é stale** — renomear pra
> `-0.7.2` é follow-up sob aprovação (quebra cross-links em STATUS/ROADMAP/T-EXP-H-GDICT; atualizar
> juntos). Por ora, nota de topo.

## Contexto / motivação

Fechar o ciclo do lazy: shipar o pacote com a view lazy promovida (A4) + a reference (A5) + a poda de
legado pré-0.7. Formato `#TCF.7` inalterado → **release `0.7.2`** (eixo C, ADR-0028). `#TCF.8` (e o
pacote `0.8.0`) ficam pro cross-dict, fora deste ticket.

## Plano

- **C1**: bump `pyproject` + `src/tcf/__init__.__version__` **0.7.1 → 0.7.2**; atualizar
  `test_version_pre_1_0` (pina a versão) — A4 já deixou `EXPECTED_PUBLIC_API` com
  `view`/`LazyTCF`/`Filtered`.
- **C2**: CHANGELOG (sub-entrada em 0.7.x) + STATUS + ROADMAP + MAP + reference (cross-ref).
- **C3**: tag `v0.7.2` → `release.yml` publica via Trusted Publishing.

## Critério de aceite

- [ ] Versão 0.7.2 consistente (pyproject + `__init__` + teste de versão).
- [ ] Suíte verde (incl. gate real-world) antes da tag.
- [ ] `from tcf import view` no wheel publicado (smoke test pós-build).
- [ ] Formato inalterado #TCF.7 (sem #TCF.8 neste release).

## Riscos / notas

- **Bloqueado por**: A4 (feito), A5 ([T-DOC-LAZY-REFERENCE](T-DOC-LAZY-REFERENCE.md)),
  e a decisão de B ([T-EXP-H-GDICT-01](T-EXP-H-GDICT-01.md) — entra no 0.8 ou difere 0.9).
- É o **último** da sequência (A → B → C); não destrava nada agora.

## Updates

- **2026-06-21**: aberto, blocked. A4 já fechou; faltam A5 + decisão de B antes de C.
- **2026-06-24 (decisão de escopo, owner)**: **0.8 = lazy (A1-A5, feito) + release**. Cross-dict
  (B2/B3) e filtros/spec-dict **deferidos pro 0.9** (#TCF.8 chega lá via B2). A5 feito → **só falta C
  (este ticket)**. Formato 0.8 = `#TCF.7` (sem #TCF.8). Desbloqueado p/ prep; tag/publish exige go
  explícito do owner.
- **2026-06-24-b (ADR-0028, retificação)**: este release = **`0.7.2`** (não 0.8.0); cross-dict #TCF.8
  = `0.8.0` (não 0.9). Plano acima corrigido pra 0.7.2. Sem bump agora (PyPI segura no 0.7.1).
