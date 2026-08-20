# 2026-08-17 — PLANO: grupo × array (H-13-06)

**[plano — nada medido além da sondagem de §1.]** O bloqueador declarado antes de qualquer
weld do combinador de grupo. Pedido do owner: *"mostre o plano do grupo x array"*.

---

## 1. A sondagem que corrige minha premissa

Eu vinha escrevendo que o risco era *"um grupo dentro de array precisa que os N campos
compartilhem a contagem"*. **Olhando o wire real, isso está errado.**

```
[{"v": ["12.50","7.99"]}, {"v": ["3.00"]}]   →   #TCF.8Hv#:6[
   [1] '\2'          ← count: 2 itens no registro 1
   [2] '\1'          ← count: 1 item no registro 2
   [3] '\12.\50'     ┐
   [4] '\7.\99'      ├ coluna de ITENS: densa, achatada entre registros
   [5] '\3.\00'      ┘
```

**A contagem é de nível de ARRAY; os itens são de nível de ITEM.** A coluna de itens já é
uma coluna comum, achatada. Trocar essa **uma** coluna por **N** colunas de grupo não toca
a contagem — ela continua dizendo quantos *itens* cada registro tem, e os N campos ficam
todos alinhados **item a item**.

Ou seja: **a hipótese de partida vira "a composição é ORTOGONAL"**, não "é difícil".

As demais formas, sondadas:

| caso | meta | o que aparece |
|---|---|---|
| array simples | `v#:6[` | count + itens |
| null em elemento | `v#:6?:8[` | count + **emask** + itens densos |
| array vazio | `v#:6[` | count com `\0` |
| campo ausente | `v?:4#:3[` | **máscara de campo ANTES** do count |
| array-em-array | `v#:3[#:6[` | counts encaixados por nível |

---

## 2. A hipótese, agora precisa

**H-13-06 (reformulada)**: substituir a coluna de itens por N colunas de grupo é ortogonal
aos mecanismos de array — `count`, `emask` e máscara de campo permanecem **byte-idênticos**,
e só a(s) coluna(s) de item mudam.

**Corolário testável**: o wire com grupo deve ter o **mesmo** `count`, o **mesmo** `emask` e
a **mesma** máscara de campo que o wire sem grupo. Se algum deles mudar, a hipótese cai.

---

## 3. Os casos — em ordem de risco crescente

| # | caso | por que é o próximo risco |
|---|---|---|
| **A1** | array de estruturados, uniforme | o caso base; se falhar aqui, para tudo |
| **A2** | contagens **variadas** (1, 3, 0, 7 itens) | o alinhamento item-a-item sob contagem irregular |
| **A3** | **array vazio** em alguns registros | zero itens contribuindo; o template ainda se forma? |
| **A4** | **todos** os arrays vazios | **0 itens no total** — não há de onde tirar template. Deve **recusar** (gate), não quebrar |
| **A5** | **null em elemento** (`emask`) | os N campos precisam ficar densos e alinhados ao **mesmo** emask |
| **A6** | **campo ausente** em registros (máscara antes do count) | duas máscaras em níveis diferentes + grupo |
| **A7** | **array-em-array**, grupo na folha | counts encaixados; o grupo mora no nível mais fundo |
| **A8** | template **não-uniforme entre registros** (ex.: `12.50` num, `1.234,56` noutro) | o gate tem de olhar **todos os itens de todos os registros**, não por registro |
| **A9** | **um item só** no dataset inteiro | template de amostra 1 — aceita ou recusa? Decisão a registrar |
| **A10** | grupo × array × `nature` na folha | três mecanismos no mesmo campo |

---

## 4. As medições

Para cada caso, **três wires**, com RT em todos:

1. **`.8H` real de hoje** — a referência do comportamento vigente.
2. **mock sem grupo** — o controle (isola o efeito dos candidatos, lição do D6).
3. **mock com grupo** — o tratamento.

E, por wire, extrair as **colunas de controle separadas** (`count`, `emask`, máscara) para a
comparação byte-a-byte do corolário de §2.

Métricas registradas por caso:

- `count` idêntico entre (2) e (3)? · `emask` idêntico? · máscara de campo idêntica?
- bytes das colunas de item: 1 coluna (sem grupo) × N colunas (com grupo)
- RT: os três wires
- se o gate recusou, **qual** condição disparou

---

## 5. Critérios de falsificação — o que faria a hipótese cair

A hipótese **cai** se qualquer um acontecer:

- **F1** — `count`, `emask` ou máscara de campo **mudam** quando o grupo entra (§2 é o corolário).
- **F2** — algum caso perde o **round-trip** com grupo mas o mantém sem.
- **F3** — o grupo exige uma **coluna de controle nova** (além de template + marcador). Isso
  quebraria a tese do lab 1800 (*"o único item novo é o marcador"*).
- **F4** — a ordem DFS / a regra do "última coluna omite size" deixa de fechar com N colunas
  no lugar de 1.
- **F5** — o gate precisa de estado por-registro (hoje é global por coluna). Seria mecanismo
  novo, não ajuste.

**A4 e A8 não são falsificações** — são o gate funcionando. O que se registra ali é se a
recusa é **limpa** (fail-loud claro ou `None` que cai no fallback), não se ela acontece.

---

## 6. O que este plano NÃO cobre

- **Encode streaming** (H-13-03/04) — o gate segue batch; array só piora, porque o template
  precisa de todos os itens de todos os registros.
- **CPU** — nada desta cadeia mediu.
- **A gramática do marcador** dentro do contexto de array (onde exatamente o `|…|` entra em
  `v#:6[`) — o plano mede a **estrutura**; a grafia é decisão de projeto, reversível.
- **Corpus real com arrays estruturados** — os datasets locais são tabulares; A1–A10 são
  sintéticos de controle. Se a hipótese passar, o passo seguinte é achar array real
  (o `.8H` do JSON de API é o caso de uso, não o corpus SQL).

---

## 7. Sequência sugerida

1. **A1** sozinho. Se F1 ou F2 dispararem, o plano inteiro muda — não gastar o resto.
2. **A2, A3, A5** (o núcleo: contagem irregular + vazio + emask).
3. **A6, A7** (as composições de duas máscaras e de níveis).
4. **A4, A8, A9** (o gate — registrar comportamento, não exigir sucesso).
5. **A10** por último (nature é ortogonal e pode mascarar defeito dos outros).

Custo estimado: um lab, sem tocar `src/tcf` (mock, como 1600/1700/1800).

---

## Conexões

- Hipótese: [roadmap-hipoteses Pacote 13, H-13-06](../2026-05/roadmap-hipoteses.md)
- Mocks que este plano estende: [`1700`](../../2026-08/2026-08-17/2026-08-17-1700-grupo-como-combinador-do-H/)
  (o combinador) · [`1800`](../../2026-08/2026-08-17/2026-08-17-1800-o-que-de-fato-falta/) (a tese do marcador único)
- Memo de decisão: [`1900`](../../2026-08/2026-08-17/2026-08-17-1900-vale-a-pena/)
- Gramática do `.8H`: `src/tcf/hierarchical.py:25-48`
