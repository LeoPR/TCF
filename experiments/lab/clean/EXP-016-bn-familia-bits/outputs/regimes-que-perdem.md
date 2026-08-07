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

## §2 — a rota TIPADA nem consulta o bN (`T-BN-TIPADO`)

Aqui a perda é real e é nossa: `#TCF.8n`/`#TCF.8b` não somam o candidato bN ao seu
`min()`. A coluna `estimativa` é o wire bN **construído de verdade** sobre as grafias
canônicas que o tipado já emite, **com RT conferido**, mais 1 byte para o char de tag
de tipo (índice 6; o modo denso mora no 7, ADR-0029). Não é um wire válido hoje — é a
meta do ticket, ancorada num wire que funciona.

| caso | família | rota hoje | bytes hoje | estimativa bN | RT da estimativa | Δ |
|---|---|---|---:|---:|:-:|---:|
| `int-01` | F1 bool/binário | tipado-n | 608 | 54 | ok | −554 |
| `float-simples` | F8 tipos | tipado-n | 612 | 92 | ok | −520 |
| `float-integral` | F8 tipos | tipado-n+pol | 612 | 58 | ok | −554 |
| `float-neg-zero` | F8 tipos | tipado-n+pol | 614 | 95 | ok | −519 |
| `misto-int-float` | F8 tipos | tipado-n+pol | 610 | 97 | ok | −513 |
| `int-grande` | F8 tipos | tipado-n | 629 | 73 | ok | −556 |

**Total nesta bateria sintética:** 3685 B → 469 B (−3216 B em 6 colunas). O número que vale para decidir
o ticket é o de dado real, não este — a bateria é sintética por construção.
