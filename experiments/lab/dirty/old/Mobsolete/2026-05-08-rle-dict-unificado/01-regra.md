# A regra unificada — sintaxe e algoritmo

---

## Sintaxe

Cada linha de uma coluna é uma das 4 formas:

```
<valor>          ← 1 ocorrência literal (declara dict se 1ª vez)
N*<valor>        ← N ocorrências literais contíguas (declara dict se 1ª vez)
<ref>            ← 1 ocorrência por referência a idx já declarado
N*<ref>          ← N ocorrências contíguas por referência
```

A `<ref>` é um número inteiro que aponta para uma declaração anterior na
mesma coluna. A 1ª declaração recebe idx 1, a 2ª recebe idx 2, etc.

### Discriminação literal vs ref (regra de exclusão por coluna)

Mesma regra das mesas anteriores:

| Domínio dos valores | `<ref>` aparece como |
|---|---|
| Não-numérico (`João`, `Caneta`) | bare integer (`1`, `2`) |
| Numérico com decimal (`1.50`) | bare integer (não colide) |
| Inteiro puro (`5`, `10`) | marcado (`:1`, `:2`) |

A regra de discriminação é coluna-local. Detectada pelo encoder em 1 passada.

### Run-length em refs também segue a regra

```
3*5        ← 3 vezes valor literal 5 (em coluna de inteiros)
3*:5       ← 3 vezes ref a idx 5 (em coluna de inteiros, marcado)
3*5        ← 3 vezes ref a idx 5 (em coluna não-numérica, bare)
```

A interpretação depende do domínio da coluna, declarada implicitamente por
seu conteúdo.

---

## Algoritmo do encoder (por linha)

Para cada posição na coluna, depois de aplicado o sort decidido:

```
posição i, valor v:

  1. Determinar tamanho da run contígua começando em i (chamar de R)
  
  2. Calcular custo de cada alternativa:
     A) emitir como literal: bytes(R, v) = bytes("R*<v>") se R>1, senão bytes("<v>")
     B) emitir como ref (se v já tem idx k): bytes(R, ref) = bytes("R*<ref>") ou bytes("<ref>")
     
  3. Escolher menor (literal ainda é necessário na 1ª aparição de v)
  
  4. Avançar i por R posições
```

A escolha **literal vs ref** acontece a cada linha. A escolha **count=1 vs
N>1** é determinística (R-counting do dado).

### Custo aproximado em bytes

Suponha valor `v` com `len(v)` chars, idx `k` com `digits(k)` chars:

| Forma | Bytes |
|---|---|
| `<v>` | len(v) + 1 |
| `R*<v>` | digits(R) + 1 + len(v) + 1 |
| `<k>` (bare) | digits(k) + 1 |
| `R*<k>` (bare) | digits(R) + 1 + digits(k) + 1 |
| `:<k>` (marcado) | 1 + digits(k) + 1 |
| `R*:<k>` (marcado) | digits(R) + 1 + 1 + digits(k) + 1 |

(O +1 é o `\n`. Ignoro custo do `*` e `:` em alguns lugares — fixo em 1B.)

### Quando ref vence literal (R=1)

- Bare: `digits(k) + 1 < len(v) + 1` ⇔ `digits(k) < len(v)`
  - Para `k=1..9` (1 dígito), ref vence sempre que `len(v) ≥ 2`
  - Para `k=10..99` (2 dígitos), ref vence se `len(v) ≥ 3`
- Marcado: `1 + digits(k) + 1 < len(v) + 1` ⇔ `digits(k) + 1 < len(v)`
  - Para `k=1..9`, ref vence se `len(v) ≥ 3`
  - Para `k=10..99`, ref vence se `len(v) ≥ 4`

### Quando ref RLE vence literal RLE (R≥2)

A diferença é `len(v) - digits(k)` (bare) ou `len(v) - digits(k) - 1` (marcado),
multiplicado pelo tamanho da run R-1 (porque a 1ª ocorrência sempre é
declaração).

→ Em runs longas, ref RLE quase sempre ganha (porque a economia se acumula).
→ Em runs curtas (R=2) com valor curto (`len(v)=1-2`), literal RLE vence.

---

## Exemplo passo-a-passo (simplificado)

Coluna `produto` na ordem `Apontador, Apontador, Caderno, Caderno, Caderno, Caderno, Caderno`:

```
Posição 1: v=Apontador (len=9, novo). R=2. 
   Opções:
     - Literal RLE: "2*Apontador\n" = 12 B (declara idx 1)
     - Não há ref (ainda não declarado)
   → Escolha: "2*Apontador" (12 B)
   
Posição 3: v=Caderno (len=7, novo). R=5.
   Opções:
     - Literal RLE: "5*Caderno\n" = 10 B (declara idx 2)
     - Não há ref
   → Escolha: "5*Caderno" (10 B)
```

Total: 22 B.

E se Caderno tivesse fragmentado (4 + 1 separados por algo):

```
Posição 3: v=Caderno (novo). R=4.
   → "4*Caderno\n" = 10 B (declara idx 2)
   
Posição 7 (após algo no meio): v=Caderno. R=1.
   Opções:
     - Literal: "Caderno\n" = 8 B
     - Ref: "2\n" = 2 B  ← idx 2 = Caderno
   → Escolha: "2" (2 B)
```

Total: 12 B vs RLE puro 18 B (`4*Caderno + Caderno`). Ganho 6 B.

---

## Compatibilidade com C11-híbrido

A regra unificada é um **superset** das escolhas C11-híbrido:
- Se o encoder unificado descobre que toda linha vale a pena ser literal,
  o output = C11 com `encoding=literal`.
- Se toda linha vale RLE puro, output = C11 com `encoding=rle`.
- Se toda linha vale ref (e a 1ª é declaração), output = C11 com `encoding=dict`.
- Quando uma coluna tem mistura, o output mistura — coisa que C11 não
  fazia (escolha era por coluna).

→ **A regra unificada é ≥ qualquer escolha C11-híbrido.** Pelo menos em
teoria. Na prática, há um caso onde perde: quando dict marcado força
overhead que C11 evitava ao escolher literal puro para toda a coluna.
Cobrir em `04-limites.md`.

---

## Header opcional ainda faz sentido?

Com a regra unificada, o decoder consegue inferir tudo da estrutura do
corpo:
- 1ª ocorrência de cada valor é declaração
- Ocorrências subsequentes podem ser ref
- Padrão `N*X` é run

Mas o **modo de discriminação** (`bare` vs `marcado`) pode ser declarado
no header para decoders simples. O header continua opcional, com mesma
filosofia da mesa anterior.

```
# enc-mode: nome=bare, produto=bare, qty=marcado, valor=bare
```

ou compacto:

```
# enc: B, B, M, B
```
