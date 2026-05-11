# Aplicação ao dataset — coluna `data` em vários cenários

Foco: comparar a coluna `data` em diferentes ordens e codificações. As
demais colunas são equivalentes às mesas anteriores.

---

## Cenário 1 — Ordem cronológica (== ordem original), absoluto literal

Sequência (30 datas):
```
2026-01-05, 2026-01-06, ..., 2026-01-11,
2026-01-15 (×6),
2026-01-22, 2026-01-23 (×2), 2026-02-01 (×2), 2026-02-02,
2026-02-15 (×2), 2026-02-16,
2026-03-03, 2026-03-10, 2026-03-12, 2026-03-20, 2026-03-25,
2026-04-01, 2026-04-05, 2026-04-15
```

Bytes: 30 × 11 = **330 B** (mais 6 do header `data:\n` = 336)

---

## Cenário 2 — Ordem cronológica, regra unificada (sem delta)

Aplicando RLE+dict sobre os absolutos:

```
data:
2026-01-05
2026-01-06
2026-01-07
2026-01-08
2026-01-09
2026-01-10
2026-01-11
6*2026-01-15
2026-01-22
2*2026-01-23
2*2026-02-01
2026-02-02
2*2026-02-15
2026-02-16
2026-03-03
2026-03-10
2026-03-12
2026-03-20
2026-03-25
2026-04-01
2026-04-05
2026-04-15
```

22 linhas (cada data única ou seu RLE). Bytes:
- 18 absolutos únicos × 11 B = 198
- 4 RLE (`6*...`, `2*...`, `2*...`, `2*...`): 13 + 13 + 13 + 13 = 52
- Header: 6
- Total: **256 B**

(Refs a dict não ajudam aqui — cada data aparece em UM bloco contíguo
após sort cronológico.)

---

## Cenário 3 — Ordem cronológica, delta puro (sem RLE/dict)

```
data:
2026-01-05
+1
+1
+1
+1
+1
+1
+4
+0
+0
+0
+0
+0
+7
+1
+0
+9
+0
+1
+13
+0
+1
+15
+7
+2
+8
+5
+7
+4
+10
```

Bytes:
- 1 absoluto: 11
- 29 deltas: cada `+N\n` ou `+0\n` = 3 a 4 B; somando: 6×3 (+1×6) + 3 (+4) + 5×2 (+0×5)... vamos contar todos:
  - `+1\n`×9 = 27
  - `+0\n` = 0\n? proposta usa `0` ou `+0`. Vamos `+0\n` = 3B × 8 = 24. (Ou `0\n` = 2B × 8 = 16.)
  - `+4\n` = 3 × 2 = 6 (aparece 2×: pos 7 e pos 28)
  - `+5\n` = 3 × 1 = 3
  - `+7\n` = 3 × 3 = 9
  - `+8\n` = 3 × 1 = 3
  - `+9\n` = 3 × 1 = 3
  - `+10\n` = 4 × 1 = 4
  - `+13\n` = 4 × 1 = 4
  - `+15\n` = 4 × 1 = 4
  - `+2\n` = 3 × 1 = 3

Soma deltas (com `+0\n` = 3B): 27 + 24 + 6 + 3 + 9 + 3 + 3 + 4 + 4 + 4 + 3 = **90 B**

Com `0\n` = 2B (sem o `+`): 27 + 16 + 6 + 3 + 9 + 3 + 3 + 4 + 4 + 4 + 3 = **82 B**

→ **Decisão**: usar `0` sem `+` (mais curto, sem ambiguidade — `0` sozinho
não é absoluto válido em coluna de datas).

Total cenário 3: 11 (absoluto) + 82 (deltas) + 6 (header) = **99 B**.

Já uma redução enorme: 256 → 99 = -61% só pelo delta puro.

---

## Cenário 4 — Ordem cronológica, delta + RLE local

Aplicar RLE sobre os deltas:

Delta sequence:
`+1, +1, +1, +1, +1, +1, +4, 0, 0, 0, 0, 0, +7, +1, 0, +9, 0, +1, +13, 0, +1, +15, +7, +2, +8, +5, +7, +4, +10`

Runs ≥ 2:
- `6*+1` (pos 1-6)
- `5*0` (pos 8-12)
(Demais são singles ou pares isolados que não compensam RLE pra 1-3 chars)

```
data:
2026-01-05
6*+1
+4
5*0
+7
+1
0
+9
0
+1
+13
0
+1
+15
+7
+2
+8
+5
+7
+4
+10
```

Bytes:
- 1 absoluto: 11
- `6*+1\n` = 5 (vs 6×3=18, save 13)
- `+4\n` = 3
- `5*0\n` = 4 (vs 5×2=10, save 6)
- `+7\n` = 3
- `+1\n` = 3
- `0\n` = 2
- `+9\n` = 3
- `0\n` = 2
- `+1\n` = 3
- `+13\n` = 4
- `0\n` = 2
- `+1\n` = 3
- `+15\n` = 4
- `+7\n` = 3
- `+2\n` = 3
- `+8\n` = 3
- `+5\n` = 3
- `+7\n` = 3
- `+4\n` = 3
- `+10\n` = 4

Soma deltas+RLE: 5+3+4+3+3+2+3+2+3+4+2+3+4+3+3+3+3+3+3+4 = **63 B**
Total: 11 + 63 + 6 (header) = **80 B**

Vs cenário 3 (delta sem RLE): -19B. RLE ajudou na repetição contígua de
`+1` e `0`.

---

## Cenário 5 — Ordem cronológica, delta + regra unificada (RLE + dict refs)

A regra unificada também identifica refs onde elas são mais curtas que
literais. Para deltas como `+1`, `+7`, `+4`:
- Literal `+1\n` = 3B; ref bare `1\n` = 2B → **ref ganha 1B**
- Literal `0\n` = 2B; ref bare `<idx>\n` = 2B → **empate**
- Literal `+13\n` = 4B; ref bare `<idx>\n` = 2B → **ref ganha 2B**

Mas precisa que o delta tenha aparecido antes (foi declarado).

Dict de deltas (em ordem de 1ª aparição):
- `+1` → idx 1 (na 1ª RLE `6*+1`)
- `+4` → idx 2
- `0` → idx 3 (na RLE `5*0`)
- `+7` → idx 4
- `+9` → idx 5
- `+13` → idx 6
- `+15` → idx 7
- `+2` → idx 8
- `+8` → idx 9
- `+5` → idx 10
- `+10` → idx 11

Linhas com ref onde for mais curto que literal:

```
data:
2026-01-05
6*+1            ← declara idx 1 (= +1)
+4              ← declara idx 2
5*0             ← declara idx 3
+7              ← declara idx 4
1               ← ref +1 (em vez de "+1") — empate? Não, "+1\n"=3 vs "1\n"=2. Ref ganha 1.
3               ← ref 0
+9              ← declara idx 5
3               ← ref 0
1               ← ref +1
+13             ← declara idx 6
3               ← ref 0
1               ← ref +1
+15             ← declara idx 7
4               ← ref +7
+2              ← declara idx 8
+8              ← declara idx 9
+5              ← declara idx 10
4               ← ref +7
2               ← ref +4
+10             ← declara idx 11
```

Bytes:
- 1 absoluto: 11
- `6*+1\n` = 5
- `+4\n` = 3
- `5*0\n` = 4
- `+7\n` = 3
- `1\n` = 2 (ref +1)
- `3\n` = 2 (ref 0) — empate com `0\n` literal, mas vamos manter ref para consistência
- `+9\n` = 3
- `3\n` = 2 (ref 0)
- `1\n` = 2 (ref +1)
- `+13\n` = 4
- `3\n` = 2 (ref 0)
- `1\n` = 2 (ref +1)
- `+15\n` = 4
- `4\n` = 2 (ref +7) — vs `+7\n` = 3, ref ganha
- `+2\n` = 3
- `+8\n` = 3
- `+5\n` = 3
- `4\n` = 2 (ref +7)
- `2\n` = 2 (ref +4)
- `+10\n` = 4

Soma: 5+3+4+3+2+2+3+2+2+4+2+2+4+2+3+3+3+2+2+4 = **57 B**
Total: 11 + 57 + 6 = **74 B**

Vs cenário 4: -6B. Refs adicionaram economia onde delta+RLE não pegava.

---

## Cenário 6 — Sort por nome, datas espalhadas

Após sort por nome, as datas ficam mas dentro de cada nome em ordem
cronológica (porque os rows estão originalmente em ordem cronológica
e sort é estável):

Ana: 01-08, 01-15, 02-01, 03-25
Beto: 01-06, 01-11, 01-23, 03-10
Carlos: 01-09, 01-15, 02-15, 04-05
Diana: 01-07, 01-15, 02-15, 04-01
Eduardo: 01-10, 01-22, 02-16, 04-15
Fernanda: 01-15, 02-01, 03-12
Gabriel: 01-15, 02-02, 03-20
Helena: 01-05, 01-15, 01-23, 03-03

Sequência completa (concatenando por nome):
01-08, 01-15, 02-01, 03-25, 01-06, 01-11, 01-23, 03-10, 01-09, 01-15,
02-15, 04-05, 01-07, 01-15, 02-15, 04-01, 01-10, 01-22, 02-16, 04-15,
01-15, 02-01, 03-12, 01-15, 02-02, 03-20, 01-05, 01-15, 01-23, 03-03

### Sub-cenário 6a — absoluto literal

30 × 11 + 6 = 336 B (mesmo do cenário 1; conteúdo, não ordem).

### Sub-cenário 6b — regra unificada sobre absolutos

22 declarações + 8 refs (as datas que se repetem entre nomes).
Refs custam ~3B cada (cardinalidade 22 → idx 10-22 são 2 chars; 1-9 são
1 char; média ~2B + \n = 3B).

Estimativa: 22 × 11 (declarações) + 8 × 3 (refs) + 6 (header) = 242 + 24 + 6 = **272 B**

(Pior que cenário 2 = 256 porque sem sort por data, RLE não pega o
`6*01-15` em bloco.)

### Sub-cenário 6c — delta com sort por nome

Deltas dentro do bloco de cada nome são positivos (já em ordem
cronológica intra-nome). Mas entre blocos de nomes, deltas são
**negativos** (volta no tempo: do último Ana para o primeiro Beto).

Sequência de deltas (computada das datas acima):
01-08 → 01-15: +7
01-15 → 02-01: +17
02-01 → 03-25: +52
03-25 → 01-06: -78  ← negativo (volta para o ano de 2026 mas mês anterior)
01-06 → 01-11: +5
... (continua)

Deltas extremamente espalhados, alguns negativos com 2-3 dígitos. RLE
não rende. Dict marginal (alguns deltas repetem mas com baixa
frequência).

Estimativa: 11 (absoluto) + 29 × 4 (delta médio 4B incluindo sinal) + 6
≈ 133 B

→ **Delta com sort errado vence absoluto literal (336) mas perde
significativamente para delta+sort cronológico (74).**

---

## Tabela síntese da coluna `data`

| Cenário | Sort | Codificação | Bytes |
|---|---|---|---|
| 1 | cronológico | absoluto literal | 336 |
| 2 | cronológico | unified rule (RLE+dict abs) | 256 |
| 3 | cronológico | delta puro | 99 |
| 4 | cronológico | delta + RLE | 80 |
| **5** | **cronológico** | **delta + unified rule** | **74** |
| 6a | nome | absoluto literal | 336 |
| 6b | nome | unified rule (abs) | 272 |
| 6c | nome | delta puro | ~133 |

### Conclusões empíricas

1. **Cenário 5 é o ótimo (74 B)** — delta + unified em ordem cronológica.
   Confirma H-δ4.
2. **Delta sozinho já é grande ganho** (336 → 99, -71%) — confirma H-δ1.
3. **RLE+dict sobre deltas adiciona ganho secundário** (-25B vs delta
   puro) — confirma H-δ2.
4. **Delta com sort errado ainda ajuda** (336 → ~133, -60%) por
   representação curta — confirma H-δ3.
5. **Padrão B (mesmo dia) é onde o delta+RLE mais brilha** (`5*0` é a
   linha mais densa do cenário 5).

---

## Total do arquivo TCF (todas as colunas, sort cronológico)

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto | unified (RLE + 1 ref Caderno) | 81 |
| quantidade | RLE local | 55 |
| valor_unitario | RLE puro | 65 |
| **data** | **delta + unified** | **74** |
| headers (5 colunas) | — | 5×~7 ≈ 36 |
| **total** | | **≈ 409 B** |

Comparação: sem coluna data = 342 B (mesa anterior). Com data + delta =
**409 B**. Adicionar uma coluna inteira só custou +67 B porque o delta
empacotou bem.

Sem o delta (data como absolutos com unified): 342 + 256 = **598 B**.

→ Delta economizou **189 B (-32%)** vs alternativa sem delta.

---

## O que valida e o que rejeita das hipóteses

| Hipótese | Resultado |
|---|---|
| H-δ1: delta vence absoluto sempre que ordem temporal | **CONFIRMADA** (-71% no cenário 5) |
| H-δ2: delta+RLE arrasa em padrões A e B | **CONFIRMADA** (`6*+1` e `5*0` são as linhas mais eficientes) |
| H-δ3: delta sem sort ainda ganha | **CONFIRMADA** (60% mesmo com sort errado) |
| H-δ4: sort por data antes do delta é ótimo | **CONFIRMADA** |
| H-δ5: delta não ajuda em datas únicas e não-monotônicas | **NÃO TESTADA** — datasets com pattern D (esparso) ainda tinham monotônico ascendente. Para testar, precisa dataset com datas embaralhadas aleatoriamente. Ticket aberto. |

Próximo arquivo: `04-conclusoes.md` para integração com Lxxx.
