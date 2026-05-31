# 0002 — Vertice triplice (compressao + memoria + latencia) como restricao dura

**Status**: accepted
**Date**: 2026-05-17
**Deciders**: project owner
**Tags**: design-principle, vertice-triplice, constraints

## Context and Problem Statement

O TCF poderia se beneficiar de tecnicas avancadas de compressao
(delta-of-delta, GCD auto-detect, dictionary global, sliding window,
block min subtraction). Mas estas tecnicas tem custos: multi-pass,
buffer ilimitado, look-ahead.

A pergunta: ate' onde otimizamos compressao se isso violar single-pass /
low-memory / low-latency?

## Considered Options

1. **Compressao maxima** (sem restricao de memoria/latencia) — atinge
   "estado-da-arte" em ratio
2. **Vertice triplice como restricao dura** — tecnicas multi-pass /
   memoria > O(1) / look-ahead sao **descartadas mesmo com ganho**
3. **Trade-off por flag** — usuario escolhe nivel (L0..L9)

## Decision Outcome

**Opcao 2 — Vertice triplice como restricao dura.**

Tres vertices co-otimizados, todos requeridos:
- **Compressao**: bytes finais minimos
- **Memoria**: O(1) extra alem do necessario (single-pass)
- **Latencia**: low TTFB, online-friendly

"Estado-da-arte" so' aceita se MAXIMIZAR OS TRES SIMULTANEAMENTE.
Se sacrifica algum, e' "algoritmo pra necessidade diferente",
nao competidor do TCF.

### Implicacoes praticas

| Tecnica | Status | Razao |
|---|---|---|
| Delta-of-delta (Gorilla VLDB 2015) | refutada | Multi-pass |
| Auto-detect GCD do stream | refutada | Multi-pass |
| Block-based min subtraction | refutada | Buffer > O(1) |
| Sliding window pattern detect | refutada | Buffer > O(1) |
| Calendar-aware delta | aceita | Single-pass possivel |
| OBAT shape-preserve hint | aceita | Single-pass + O(1) memoria |
| Composicao por outras naturezas | aceita | Single-pass possivel |

## Pros and Cons of the Options

| Opcao | Pros | Cons |
|---|---|---|
| Compressao maxima | Melhor ratio absoluto | Quebra streaming/online; memoria explode em data grande |
| **Vertice triplice** | Mantem TCF aplicavel em qualquer escala/contexto | Abre mao de algumas tecnicas de compressao |
| Trade-off por flag | Flexivel | Multiplos formatos pra suportar = manutencao alta |

## Por que rejeitar Opcao 1

Pre-tx multi-pass (T01 v2) foi descartado especificamente por violar
single-pass — mesmo que comprimisse mais. Decisao reforcada pelo user
em 2026-05-17:

> "delta-of-delta nao faz sentido o argumento 'estado-da-arte', pois
> lembra-se do foco nos tres vertices que sao compressao, memoria e
> latencia? se deixa de fazer single pass, logo multi-pass ja' foge
> do estado-da-arte em um dos vetores."

## More Information

- Doc teorico: `docs/theory/perspectiva-triplice-e-pre-tx.md`
- Aplicacao: Pacote 1 delta-aware (lab `2026-05-17-OBAT-delta-aware`)
  abandonou pre-tx multi-pass por isso
- ADRs derivados: [ADR-0003](0003-tripartite-pre-obat-hcc.md)

## Cross-references

- T01 v2 critica: `experiments/lab/dirty/notas/T01-v2-critica-e-direcao.md`
- Diario 2026-05-17 D1, D2
- Memoria user `feedback_rigor_cientifico.md`
