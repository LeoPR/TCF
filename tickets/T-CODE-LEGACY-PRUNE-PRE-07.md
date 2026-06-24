---
title: T-CODE-LEGACY-PRUNE-PRE-07 — Podar fallbacks/legado pré-0.7 do core (rumo a 1.0)
status: in-progress
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
- [ ] **S1** — aposentar `encode_table`/`decode_table` (remover de `multi.py` + `__init__` `__all__` +
  `EXPECTED_PUBLIC_API`; remover 4 testes deprecation/legacy_info). Zero efeito de bytes.
- [ ] **S2** — isolar produção `#TCF.6`/322B em `tests/legacy/`; gate principal afirma só `#TCF.7`/303B.
- [ ] **S3** — isolar leitura `#TCF.6` em caminho `_legacy_read` marcado (decoder/multi/view). Re-rodar
  D1-D9/D17a/real-world.
- [ ] **S4** — limpeza cosmética de docstrings (M9/v0.6/#TCF.6-default → linguagem dos 3 eixos).
- [ ] **S5** — gravar o modelo de versão (3 eixos) em local canônico (ADR ou TCF-format §Versionamento).

## Critério de aceite
- D1-D9=1523B / D17a=303B intactos; `test_real_world_snapshots` verde a cada passo.
- 303B = único baseline vivo; 322B só em `tests/legacy/` (comparação).
- Caminho principal do decoder/multi/view sem `#TCF.6` (isolado em `_legacy_read`).
- `encode_table`/`decode_table` fora da API pública.

## Updates
- **2026-06-24**: plano aprovado pelo owner (3 decisões). Iniciando S1.
