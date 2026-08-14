# Avaliação: um spec de HORA (sem data) faz sentido?

**2026-08-14** · pedido do owner: *"poderíamos ver a parte de spec de hora, sem data.
avalie"*.

**Resposta curta: não agora — e o caso real que existe já é resolvido por um mecanismo que
o projeto tem, só não na rota certa.**

---

## 1. Hora quase não existe no corpus

Varrendo todos os bancos de `Z:/tcf-data/interim`, **uma única** coluna tem hora — e ela é
`datetime`, não hora pura: `online-retail.InvoiceDate` (`2010-12-01 08:26:00`). Nenhuma
coluna de hora isolada.

Isso não prova que hora pura seja irrelevante no mundo (logs, escalas, telemetria têm), mas
diz que **este corpus não a tem** — e o corpus é quem dita o default.

## 2. A transformação hora→segundos rende pouco em dado real

O candidato óbvio, análogo ao `data-iso`: `HH:MM:SS` → segundos desde meia-noite (0..86399).

| regime | ISO | segundos | ganho |
|---|---:|---:|---:|
| **REAL** (hora do `InvoiceDate`, n=3000) | 15.022 | 14.563 | **1,03×** |
| log `HH:MM:SS` aleatório | 5.425 | 3.530 | 1,54× |
| comercial 8h–18h | 5.448 | 3.597 | 1,51× |
| só `HH:MM` | 3.752 | 3.417 | 1,10× |
| poucos horários (k=8) | 400 | 369 | 1,08× |
| batimento 15 min (cíclico) | 1.457 | 728 | 2,00× |
| **batimento 1 min ordenado** | 199 | **22** | **9,05×** |

No único dado real: **1,03×**. A hora como texto já é bem comprimida pelo OBAT — os `:` são
afixo e os dígitos se repetem. O ganho grande aparece só em **regimes regulares**
(batimentos, telemetria), que existem no mundo mas não neste corpus.

## 3. A diferença estrutural: hora é CÍCLICA

O `data-iso` funciona porque o ordinal é **absoluto e monotônico** — dias desde 0001-01-01,
que crescem sem voltar. A hora **volta a zero todo dia**: o seq-RLE vê um salto negativo a
cada meia-noite. Medido no batimento de 15 min, o corpo sai `*96+900|\00000` — 96 passos
(um dia) e re-âncora.

Ou seja: a hora só é monotônica **dentro de um dia**. É a mesma família do `data-iso`, mas
com uma quebra periódica embutida que a data não tem.

## 4. O caso real é DATETIME — e aí a resposta já existe

Com amostra que atravessa datas (3.000 linhas, 304 datas, 603 horas distintas):

| rota | bytes | vs string |
|---|---:|---:|
| datetime string, single-col | 61.856 | — |
| epoch como **um** inteiro | 26.887 | 2,30× |
| separar à mão (data com spec `dt` + hora em segundos) | 17.559 | 3,52× |
| **split estrutural `%`, multi-col** | **8.675** | **7,13×** |

**O split estrutural já resolve, e melhor que qualquer transformação que eu prototiparia.**
Ele é automático: o `_best_of` do multi-col escolheu `split` sozinho, sem spec, sem
parâmetro, sem nada novo.

E o detalhe que importa: **o split só existe na rota multi-col**. O mesmo dado em single-col
dá 61.856 B; em multi-col com **uma** coluna dá 8.675 B. É o `T-SPLIT-SINGLE-COL`, que já
está registrado — e esta é a evidência mais forte que ele já teve (**7,13×**, contra os
1,35×–2,7× medidos antes em data).

## 5. Uma amostra que quase me enganou

A primeira medição usou `LIMIT 600` e deu "separar é **pior** que epoch" (519 vs 433 B). A
amostra era **degenerada**: 600 linhas seguidas do mesmo dia — **1 data distinta**. Com a
data constante, a parte-data comprime a quase nada e a comparação inverte.

Refeito com amostragem espalhada (`rowid % k`), a conclusão virou o oposto. Fica o registro:
em coluna temporal, `LIMIT` sem espalhamento pega uma janela e mente sobre a distribuição.

## 6. Recomendação

1. **Não abrir spec de hora agora.** 1,03× no único dado real, e o regime onde ele brilha
   (batimento regular) não está no corpus. Se aparecer corpus de telemetria/logs, reavaliar —
   ali o ganho medido é de 2× a 9×.
2. **O que vale de verdade é o `T-SPLIT-SINGLE-COL`**, e esta avaliação lhe dá o melhor
   número que ele tem: **7,13×** num datetime real. O mecanismo está pronto e testado; falta
   a rota single-col consultá-lo — a mesma classe de "o candidato existe e a rota não
   consulta" que já apareceu várias vezes.
3. **Se hora virar spec um dia**, o desenho natural é irmão do `data-iso` (segundos desde
   meia-noite, auto-contido, sem parâmetro), com a ressalva da ciclicidade — e o id na
   família reservada `dt*` do ADR-0041 (`dth`? `dthora`?), não em prefixo novo.
