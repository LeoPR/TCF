# Espectro de alfabetos para índices

Lista enumerada das opções, com formulação de bytes/idx e nota de
colisão.

---

## Decimal (`0-9`, base 10)

**Caracteres:** `0` a `9` (10 símbolos).

**Chars/idx por cardinalidade:**

| c | chars |
|---|---|
| ≤ 9 | 1 |
| 10–99 | 2 |
| 100–999 | 3 |

**Colisão:** com **qualquer valor numérico inteiro**. Em colunas
numéricas, exige marcador `:` (overhead +1 char/ref).

**Status:** default histórico. Sem ganho fora de cardinalidade ≤ 9 (e
mesmo aí, só por inércia).

---

## Hexadecimal (`0-9 a-f`, base 16)

**Caracteres:** 16 símbolos (`0123456789abcdef`).

**Chars/idx por cardinalidade:**

| c | chars |
|---|---|
| ≤ 16 | 1 |
| 17–256 | 2 |
| 257–4 096 | 3 |

**Colisão:** com valores que sejam números hexadecimais "puros" — raríssimo
em dados de aplicação. Letras a-f podem colidir com valores que sejam
single-letter (improvável) ou strings curtas tipo `ab`.

**Status:** ganho moderado em cardinalidade 10-16 vs decimal. Pouco
relevante para cardinalidade média (≥ 17 e ≤ 99, decimal e hex empatam
em 2 chars).

---

## Letras (`a-z` ou `a-z A-Z`, base 26 ou 52)

**Caracteres:** alfabeto Latin (26) ou Latin com maiúsculas (52).

**Chars/idx por cardinalidade:**

| c | chars (a-z) | chars (a-z A-Z) |
|---|---|---|
| ≤ 26 | 1 | 1 |
| ≤ 52 | 2 | 1 |
| ≤ 676 | 2 | 2 |

**Colisão:** com **valores que comecem por letra**. Em colunas puramente
numéricas, **zero colisão** — não precisa marcador `:`. Em colunas com
strings (nomes, produtos), a primeira aparição é literal e ocuparia o
"alfabeto" do dict; mas como a 1ª aparição **não é referência**, não há
ambiguidade.

**Status muito interessante:** em colunas numéricas, letras ELIMINAM o
marcador. Ganho de 1 byte por ref independente da cardinalidade.

Exemplo na coluna `quantidade` do dataset:
- Decimal com marcador: `:2\n` = 3 B
- Letra: `b\n` = 2 B
- Ganho: 1 B/ref

---

## Base 64 (`a-z A-Z 0-9 + _`, base 64)

**Caracteres:** 64 símbolos (versão URL-safe).

**Chars/idx:**

| c | chars |
|---|---|
| ≤ 64 | 1 |
| 65–4 096 | 2 |

**Colisão:** com qualquer valor que tenha esses 64 chars. Em strings
mistas, possível.

**Status:** ganho real para cardinalidades 17-64 (1 char vs 2 em hex/decimal).

---

## Base 94 — printable ASCII

**Caracteres:** todos os printáveis ASCII (33-126), excluindo espaço e
talvez alguns sintaticamente reservados (`*`, `:`, `\n`, `,`).

**Chars/idx:**

| c | chars |
|---|---|
| ≤ ~88 (excluindo reservados) | 1 |
| até ~7 700 | 2 |

**Status:** denso ao máximo possível em ASCII puro. Custo: visualmente
pouco legível (caracteres como `~`, `\``, `^`).

---

## Binário (1 byte por idx, base 256)

**Caracteres:** todos os 256 valores possíveis de byte.

**Chars/idx:**

| c | chars |
|---|---|
| ≤ 256 | 1 |
| ≤ 65 536 | 2 |

**Colisão:** com qualquer byte da coluna. Em coluna textual, a maioria
dos bytes 0-31 nunca aparecem como valor (controle), então parser pode
distinguir por "byte de controle = ref".

**Trade-off forte:** perde legibilidade ASCII. LLM pode não conseguir
processar. **Conflita com objetivo do TCF**.

**Status:** rejeitado para o formato base. Pode ser modo opt-in
exoticíssimo, mas não é prioridade.

---

## Bit-packing (vários idx por byte)

Para cardinalidades muito baixas, é possível compactar múltiplos índices
no mesmo byte:

| c | bits/idx | idx/byte |
|---|---|---|
| ≤ 2 | 1 | 8 |
| ≤ 4 | 2 | 4 |
| ≤ 16 | 4 | 2 |

**Status:** mesmo problema do binário (perde legibilidade), mais
complexo. Útil só em colunas com cardinalidade ≤ 4 ou ≤ 16. Marginal.

---

## Tabela síntese — chars/idx em função da cardinalidade

| Cardinalidade c | decimal | hex | letras (52) | base64 | base94 |
|---|---|---|---|---|---|
| 1–9 | 1 | 1 | 1 | 1 | 1 |
| 10–16 | 2 | **1** | 1 | 1 | 1 |
| 17–26 | 2 | 2 | 1 | 1 | 1 |
| 27–52 | 2 | 2 | **1** | 1 | 1 |
| 53–64 | 2 | 2 | 2 | **1** | 1 |
| 65–94 | 2 | 2 | 2 | 2 | **1** |
| 95–99 | 2 | 2 | 2 | 2 | 2 |
| 100–256 | 3 | **2** | 2 | 2 | 2 |
| 257–676 | 3 | 3 | **2** | 2 | 2 |
| 677–4 096 | 4 | 3 | 3 | **2** | 2 |
| 4 097–8 836 | 4 | 4 | 3 | 3 | **2** |
| 8 837 + | 4+ | 4+ | 3+ | 3+ | 3+ |

**Negrito** = onde o alfabeto vira o vencedor relativo aos anteriores.

---

## Ranking por densidade (sem considerar colisão)

1. Bit-packing / binário (rejeitado por legibilidade)
2. Base94 (denso, mas ilegível visualmente)
3. Base64 (bom equilíbrio)
4. Letras a-zA-Z (52)
5. Hex (16)
6. Decimal (10)

## Ranking quando há colisão (coluna numérica)

1. **Letras a-zA-Z** — sem marcador
2. Base64 — sem marcador (a-z, A-Z, 0-9 podem colidir com numérico mas
   maioria das colisões fica em letras → também sem marcador)
3. Hex — colide pouco (raros valores hexadecimais puros), parser precisa
   mais cuidado
4. Decimal — exige marcador `:` ⇒ +1B/ref

## Ranking quando há colisão (coluna alfabética)

1. **Decimal** — sem colisão (nomes não começam com dígito)
2. Hex — pode colidir se nome curto for "abc"
3. Letras — colide direto (nome literal vs idx é a mesma classe)
4. Base64 — colide

→ A escolha de alfabeto deve ser **per-coluna**, baseada no domínio dos
valores. Dual com a regra de exclusão da mesa anterior.
