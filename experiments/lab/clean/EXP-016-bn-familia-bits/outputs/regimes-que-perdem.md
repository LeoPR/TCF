# Regimes em que o bN NÃO ativa (n≥10)

Gerado por `run.py`. Duas coisas diferentes moram aqui: **decisões corretas do FLOOR**
(§1) e uma **lacuna de rota** que é ticket aberto (§2).

## §1 — o FLOOR recusou, e recusou certo

Nestes o bN é consultado e **perde**: outro mecanismo do core faz menor. Nada a
corrigir; ficam listados para o estudo de volume — *são comuns no dado real?*

| caso | família | bytes | por que existe |
|---|---|---:|---|
| `null-so` | F2 null | 14 | coluna 100% null: k=1, o core resolve com RLE |
| `null-um-so` | F2 null | 16 | 1 null em N-1 iguais: k=2 mas RLE domina |
| `k-257` | F3 bordas | 1217 | k=257: PASSA do teto — o bN deve recusar e o core assumir |
| `so-vazio` | F4 espaços | 13 | todos vazios: k=1 |
| `corpo-rle-vs-bn` | F10 bN×RLE | 21 | corpo perfeitamente RLE-ável (2 blocos): o core faz `*100\|a`+`*100\|b` e VENCE o bN |

## §2 — a rota TIPADA (`T-BN-TIPADO`) — **FECHADO 2026-08-07**

Esta seção media a lacuna da rota tipada, que não consultava o candidato bN.
O `T-BN-TIPADO` foi soldado: `#TCF.8nB<w><n>` — a mesma forma do `#TCF.8bB`
(tag no índice 6, modo no 7), com cast numérico na volta. Os 6 casos que
moravam aqui foram re-pinados de `recusa` para `ativa` no `casos.py`.

A lista abaixo está VAZIA — é assim que se vê que fechou. Se algum caso voltar a aparecer, a rota tipada regrediu.

| caso | família | rota hoje | bytes hoje | estimativa bN | RT da estimativa | Δ |
|---|---|---|---:|---:|:-:|---:|

**Total nesta bateria sintética:** 0 B → 0 B (−0 B em 0 colunas). O número que vale para decidir
o ticket é o de dado real, não este — a bateria é sintética por construção.
