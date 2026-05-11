# Hipótese — alfabeto do índice como variável de compressão

A regra unificada deixou as referências de dict como `1`, `2`, ... — decimais.
Mas índice é só um **rótulo identificador**: pode ser qualquer caractere ou
sequência, desde que não colida com os valores.

A hipótese: **trocar o alfabeto do índice por outro denso reduz bytes**, e a
escolha pode ser deduzida da própria coluna.

---

## A intuição em termos de bits

Um byte tem 256 valores possíveis. A pergunta é: em quantos bits cabe um
índice de cardinalidade `c`?

| Cardinalidade c | bits/idx | Idx por byte (binário) |
|---|---|---|
| ≤ 2 | 1 | 8 |
| ≤ 4 | 2 | 4 |
| ≤ 16 | 4 | 2 |
| ≤ 256 | 8 | 1 |
| ≤ 65 536 | 16 | ½ (2 bytes) |

Em ASCII puro (1 char = 8 bits, mas só 7 utilizáveis efetivamente):

| Cardinalidade c | chars/idx (decimal) | chars/idx (hex) | chars/idx (base64) | chars/idx (base94) |
|---|---|---|---|---|
| ≤ 9 | 1 | 1 | 1 | 1 |
| ≤ 16 | 2 | 1 | 1 | 1 |
| ≤ 64 | 2 | 2 | 1 | 1 |
| ≤ 94 | 2 | 2 | 2 | 1 |
| ≤ 99 | 2 | 2 | 2 | 2 |
| ≤ 256 | 3 | 2 | 2 | 2 |
| ≤ 4 096 | 4 | 3 | 2 | 2 |

O alfabeto certo depende da cardinalidade da coluna. Em cardinalidades
"do meio" (10-94), os ganhos são reais.

---

## Os 3 eixos da escolha

### Eixo 1 — densidade do alfabeto

Quanto mais símbolos distintos, mais cabe num caractere. Mas a partir de
certo ponto, sai de ASCII-printável e entra em binário (perde
legibilidade).

### Eixo 2 — colisão com valores da coluna

Se a coluna tem inteiros como valores, índices decimais colidem → exigem
marcador `:`. Mas se os índices forem **letras**, não há colisão com
valores numéricos. **Marcador `:` desaparece**.

Idem reverso: coluna de letras pode usar índices numéricos sem marcador
(o que já fazemos). A escolha do alfabeto pode **eliminar** o overhead do
discriminador.

### Eixo 3 — compatibilidade com compressor binário downstream

Se o TCF for passado para gzip/zstd depois:
- Decimal: baixa entropia (lots de '1', '2'), gzip comprime mais
- Base64/hex: entropia média, gzip comprime menos
- Binário pré-empacotado: entropia máxima, gzip não comprime nada extra

Trade-off: pré-empacotar economiza bytes no TCF, mas pode "antecipar"
ganho que gzip já daria sozinho.

---

## A pergunta para a mesa

Igual à mesa de síntese: **qual alfabeto matematicamente domina os outros
em qualquer escala?**

Hipóteses prévias:
- **H-A1**: Para cardinalidade ≤ 9, decimal é ótimo (1 char/idx, sem
  alternativa que melhore).
- **H-A2**: Para 10 ≤ cardinalidade ≤ ~64, alfabetos densos (hex, base64,
  letras) ganham vs decimal por reduzir 2 chars → 1 char.
- **H-A3**: Letras (a-z, A-Z) eliminam o marcador `:` em colunas
  numéricas. Ganho adicional independente da cardinalidade.
- **H-A4**: Acima de cardinalidade ~94, qualquer alfabeto ASCII precisa
  de ≥ 2 chars; binário começa a ter vantagem real.
- **H-A5**: Em qualquer alfabeto não-decimal, o ganho líquido depende de
  se a saída vai passar por gzip ou não.

---

## Conexão com a regra unificada

A escolha do alfabeto é uma **dimensão extra** ortogonal à regra unificada.
Na hierarquia de flags Lxxx, sugere uma nova flag:

```
A = alfabeto adaptativo do índice
```

Com sub-modos possíveis:
- `A` (default off → decimal)
- `Aletters` (letras a-z A-Z, evita colisão numérica)
- `Ahex` (0-9 a-f, denso)
- `Abase64` (62 chars + 2 extra)
- `Abinary` (binário 1 byte/idx, perde legibilidade)

A análise vai mostrar quais sobrevivem.

---

## Plano

1. **`01-espectro.md`** — enumerar alfabetos com fórmula bytes/idx
2. **`02-aplicado.md`** — aplicar ao dataset de 30 linhas
3. **`03-tradeoffs.md`** — legibilidade, gzip downstream, complexidade
4. **`04-proposta.md`** — incorporar à hierarquia Lxxx
