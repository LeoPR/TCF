# M7 — Refactor + nova estrutura de debug

**Data**: 2026-05-15
**Estado**: e' (em curso)
**Sucede**: [M6](../2026-05-14-M6-sintaxe-composicional/) — apos:
  - User notou que M5 + M6 tiveram remendos (preambulo M2.A, mapping
    prov→final, virtual refs ausentes) que inflaram o codigo.
  - Debug empilhava tokens (alg16) + detector_trace + TCF + decode
    no mesmo lugar; dificultava leitura.

## Objetivos

1. **Refactor M6.C** — codigo compacto, fluxo claro de composicoes,
   sem remendos acumulados. Mesmo comportamento, melhor leitura.

2. **Nova estrutura de debug** — separar:
   - `resultados/tokens/<dataset>.txt`: alg16 raw (compartilhado entre micros)
   - `<micro>/output/<dataset>.tcf`: TCF
   - `<micro>/decoded/<dataset>.csv`: contra-prova
   - `<micro>/debug/<dataset>.txt`: INPUT/TCF/DECODE resumo
   - `<micro>/detector_trace/<dataset>.txt`: iteracoes do detector
   - `<micro>/redes/<dataset>.txt`: estado da rede (atomos+composicoes+uso)

3. **Reanalise algoritmo** — fluxo das fases:
   - Phase A: tokenize → pieces per line (lit + refs, prov atom IDs)
   - Phase B: detect compositions (greedy iterativo)
   - Phase C: emit body (single pass, ID interleaved)
   - Diferenca de M6.C: Phase 5 + Phase 6 unificadas em Phase C.

## Micros

| Micro | Foco |
|---|---|
| M1-E-range-baseline | referencia M1.E |
| M6-C-baseline | comparacao com M6.C anterior |
| M7-A-composicional | refactor limpo do M6.C |

## Hipotese

Bytes idênticos a M6.C (619 total D1-D4). Codigo significativamente
mais compacto e legivel. Debug separado por concern.

## Direcoes registradas (nao M7)

- **Detector com virtual refs** (capturar pairs (atom + alias) e
  (alias + alias)). Algebricamente: ~28 bytes adicionais em D1-D4.
  Complexidade alta — recursao na resolucao de sub-aliases.
  Adiado pro protótipo ou M8.

## Resultados

| Sintaxe | D1 | D2 | D3 | D4 | Total |
|---|---:|---:|---:|---:|---:|
| M1.E baseline | 149 | 180 | 206 | 141 | 676 |
| M6.C baseline | 128 | 175 | 194 | 122 | 619 |
| **M7.A (refactor)** | **128** | **175** | **194** | **122** | **619** |

RT 12/12 OK. M7.A == M6.C byte-a-byte.

Codigo: M6.C 674 linhas → M7.A 636 linhas (~5% menor; estrutura
significativamente melhor — 3 fases separadas, sem remendos de mapping).

Detalhes em [`notas/conclusoes_M7.md`](notas/conclusoes_M7.md).
