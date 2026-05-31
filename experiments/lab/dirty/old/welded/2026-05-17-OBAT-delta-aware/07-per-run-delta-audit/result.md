# Resultado — Sub-exp 07 (H-DA-08 per-run delta)

**Data**: 2026-05-17
**Estado**: concluido (audit-only, sem implementacao)
**Plano**: [README.md](README.md)
**Audit**: [audit.md](audit.md)

## Conclusao executiva

**H-DA-08 REFUTADA.** Ganho potencial total **9 bytes** em todos
D11 + D16 datasets. Custo de implementacao (sintaxe nova
`*N+delta@run_idx|`, decoder mais complexo, marker overhead que
come o ganho em pares de 2 linhas) **nao justifica**.

## Numeros

| Dataset | Pares qualificaveis | Bytes potencial |
|---|---:|---:|
| D11a | 1 | 3 |
| D11b | 2 | 6 |
| D11c | 0 | 0 |
| D11d-h | 0 | 0 |
| D16a-c | 0 | 0 |
| **Total** | **3** | **9** |

## Por que tao pouco

A maioria dos pares qualificaveis sao runs de **2 linhas apenas**.
Marker per-run (`*2+1@1|<template>`) custa ~5 bytes extras alem do
template; em 2 linhas isso come quase toda a economia.

Em D11d-h e D16a-c, o sub-exp 04 (OBAT shape-preserve) ja' eliminou
varias dessas situacoes ao manter shape uniforme — pares qualificaveis
ficam apenas em D11a e D11b (bordas, sem cadencia).

## Decisao

NAO implementar. Manter detector atual.

Caso futuro: se aparecer dataset com runs maiores (3+ linhas) onde
algumas runs nao mudam, re-avaliar. Provavelmente nao acontece em
dados realistas.

## Status H-DA-08 no roadmap

**refutada** — ganho marginal (9 bytes) nao justifica complexidade.
