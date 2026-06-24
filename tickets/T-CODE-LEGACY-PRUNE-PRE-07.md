---
title: T-CODE-LEGACY-PRUNE-PRE-07 — Podar fallbacks/legado pré-0.7 do core (rumo a 1.0)
status: closed
priority: P2
created: 2026-06-24
updated: 2026-06-24
related:
  - experiments/lab/dirty/notas/plano-poda-legado-pre-0.7-2026-06-24.md
  - docs/adr/0024-pre-1.0-versioning-git-as-compat.md
  - tickets/T-DIST-RELEASE-0.8.0.md
---

# T-CODE-LEGACY-PRUNE-PRE-07

## Contexto

Owner: o desenvolvimento gerou muitos artefatos; tirar os fallbacks pré-0.7, isolando o que serve de
comparação ou aposentando. Rumo a 1.0 o código converge para o formato final. Plano + inventário +
modelo de 3 eixos (formato/encoder-gen/pacote): [`plano-poda-legado-pre-0.7-2026-06-24.md`](../experiments/lab/dirty/notas/plano-poda-legado-pre-0.7-2026-06-24.md).

## Decisões (owner 2026-06-24)
1. Leitura `#TCF.6` → **isolar em `_legacy_read`** (dropar no 1.0).
2. `encode_table`/`decode_table` → **aposentar**; produção `#TCF.6`/baseline **322B → `tests/legacy/`** (comparação).
3. **Podar agora, fundido no release `0.7.2`** (formato #TCF.7 inalterado → patch, não 0.8.0; ADR-0028).

## Passos (cada um mantém suíte verde; toca src/tcf → aprovado no plano)
- [x] **S1** — aposentar `encode_table`/`decode_table` (commit 39e7c8b). Suíte 376.
- [x] **S2** — isolar produção `#TCF.6`/322B em `tests/legacy/` (commit 5d4a4dc). 375 + 5 legacy.
- [x] **S3** — marcar leitura `#TCF.6` como legada (decoder/multi/view; commit 7aa46bd). 375. (markers
  "remover no 1.0"; isolacao por marcacao — o parser tolerante e' compartilhado, nao reestruturado.)
- [x] **S4** — limpeza cosmética de docstrings (#TCF.6-default→#TCF.7; M9/M10=geracao interna eixo B;
  commit d44cb78). 375.
- [x] **S5** — modelo de versão (3 eixos) gravado: **ADR-0028** + `docs/vocabulary.md §Versionamento`
  + `TCF-format.md §Versionamento` (commit d44cb78).

## Critério de aceite
- D1-D9=1523B / D17a=303B intactos; `test_real_world_snapshots` verde a cada passo.
- 303B = único baseline vivo; 322B só em `tests/legacy/` (comparação).
- Caminho principal do decoder/multi/view sem `#TCF.6` (isolado em `_legacy_read`).
- `encode_table`/`decode_table` fora da API pública.

## Updates
- **2026-06-24**: plano aprovado pelo owner (3 decisões). Iniciando S1.
- **2026-06-24-b**: S1-S5 feitos (commits 39e7c8b, 5d4a4dc, 7aa46bd, d44cb78). **CLOSED.** Bump pra
  0.7.2 NÃO entra aqui — é o release (T-DIST-RELEASE, workstream C), segurado no go do owner. ADR-0028
  formalizou o modelo de versão (3 eixos) durante a poda.
