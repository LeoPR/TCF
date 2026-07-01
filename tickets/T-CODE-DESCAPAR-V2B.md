---
title: T-CODE-DESCAPAR-V2B — Descapar o V2-B (dict como candidato do min() p/ high-card)
status: open
priority: P2
created: 2026-07-01
updated: 2026-07-01
related:
  - experiments/lab/dirty/2026-07-01-dict-highcard/
  - experiments/lab/dirty/2026-07-01-descapar-v2b/
  - src/tcf/multi/dict_v2b.py
  - src/tcf/multi/core.py
---

# T-CODE-DESCAPAR-V2B — Descapar o V2-B

## Contexto / motivação

Pivô do cross-dict fechado ([T-EXP-H-GDICT-01](T-EXP-H-GDICT-01.md)): a direção certa não é
compartilhar entre colunas, é **fortalecer o `min(tcf,raw,v2b,split)` per-coluna**. O cap
`_V2B_MAX_CARD=1024` (`dict_v2b.py`) faz `_v2b_encode` retornar `None` p/ K>1024 → o dict **nunca é
candidato** p/ high-card. Caracterização ([dict-highcard](../experiments/lab/dirty/2026-07-01-dict-highcard/result.md)):
o dict vence OBAT/HCC em high-card **espalhado** (l_partkey −46%, municipio −40%, razao_social −40%),
perde em **estruturado** (seq-RLE). Prototype read-only ([descapar-v2b](../experiments/lab/dirty/2026-07-01-descapar-v2b/result.md)).

## Pergunta

Descapar (deixar o dict entrar no `min()` p/ high-card) vale o custo de compute?

## Achados do prototype (read-only, monkeypatch do cap)

- **BYTE-SAFE**: delta ≤ 0 em TODAS as tabelas (o `min` nunca regride, core.py:178-191). RT=True.
- **Ganho**: −4.88% br-empresas, −5.32% receita (colunas high-card espalhadas); 0% onde é estruturado
  ou low-card. Concentrado, não weighted-amplo.
- **PINS INALTERADOS**: D1-D9/real-world (single-col) + D17a (low-card) idênticos capped vs uncapped —
  o V2-B nem é candidato neles. **Weld sem re-pin.**
- **Custo**: encode ~1.1–2.2× mais lento (o dict-encode extra por coluna K>1024). Skip barato
  (`N·w(K)≥tcf`) fraco (8%). Mitigação = skip **cadence-aware** (reusa `detect_cadence` do pré-pass).

## Opções de weld (owner decide a forma)

- **(A) cap-raise** `1024→~8192`: captura municipio/cpf/razao (K≈1.4–6k) com compute contido. **Baixo
  risco, 1 linha. RECOMENDADO como 1º passo.**
- **(B) descapar total + skip cadence-aware**: ganho máximo, compute recuperado; mais trabalho (a heurística).
- **(C) descapar puro**: ganho máximo, ~2× compute nas tabelas high-card. Simples mas caro.

## Critério de aceite

- byte-safe confirmado na suíte (D1-D9=1523B / D17a=303B / RW=89616B **inalterados**; RT 100%).
- ganho medido em ≥2 tabelas reais (br-empresas/receita ~−5%).
- (B) se escolhido: heurística de skip não perde nenhum win e recupera a maior parte do compute.

## Riscos / notas

- Toca `src/tcf` (dict_v2b.py + possível skip em core.py) → **sob aprovação explícita do owner**.
- Custo de compute é o único trade (bytes são estritamente ≥). Alinha Abadi 2006 / Zukowski PDICT.

## Updates

- **2026-07-01**: aberto. Prototype read-only feito (byte-safe, −5%, ~2× compute). Aguarda owner
  escolher forma (A/B/C) pro weld.
