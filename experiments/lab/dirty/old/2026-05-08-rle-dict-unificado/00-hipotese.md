# Hipótese — RLE + DICT como regra única, com deduções implícitas

**Dataset:** o mesmo das 2 mesas anteriores (30 linhas, 4 colunas).

---

## A ideia

Em vez de o encoder escolher entre {literal, RLE puro, dict puro, dict+RLE}
por coluna, **usar uma única regra unificada**: cada linha é, sempre, uma
sequência `[N*]<valor-ou-ref>` — onde:

- `N` é implícito 1 quando ausente
- `<valor>` literal vira automaticamente declaração de dict (1ª aparição)
- `<ref>` é referência a um índice já declarado
- O encoder escolhe **por linha** (não por coluna) entre emitir literal ou
  emitir ref — quem for mais curto vence

### Como isso reproduz nossos modos antigos

| Modo antigo | Equivalente na regra única |
|---|---|
| Literal puro (`João`) | `João` (count=1, declaração implícita se 1ª vez) |
| RLE puro (`4*João`) | `4*João` (count=4, declaração implícita) |
| Dict-bare (declaração + ref) | `João` na 1ª, `1` (ou `:1`) nas seguintes |
| Dict + RLE em refs (`3*1`) | `3*1` ou `3*:1` para 3 refs contíguas |

Tudo é a mesma regra. O modo "antigo" emerge da escolha local do encoder.

### Predição da hipótese

> Para a coluna do primeiro sort: encoder sempre usa RLE puro (cada valor
> aparece em um único bloco contíguo, refs não são necessárias).
>
> Para as outras colunas: encoder mistura RLE quando há run + refs quando o
> valor reaparece longe da 1ª aparição.

→ A regra unificada **dominará** o C11-híbrido (que escolhe por coluna)
sempre que houver fragmentação intra-coluna — ou seja, quando o mesmo
valor aparece em múltiplos blocos disconectos.

---

## Quando a regra unificada deve ganhar

Quando uma coluna tem **fragmentação**: mesmo valor em ≥2 blocos separados.
Caso típico: sort secundário corta um bloco em pedaços.

Exemplo no nosso dataset (sort `valor, produto, qty`):
- `Caderno` aparece em 4 ocorrências (3.00) + 1 ocorrência (5.00), com
  `Marcador` entre eles.
- RLE puro: `4*Caderno + Caderno` = 18 B
- Regra unificada: `4*Caderno + 6` (ref a Caderno) = 12 B
- Ganho: 6 B

## Quando a regra unificada deve empatar

Quando não há fragmentação, ou quando a coluna é o sort primário com runs
perfeitos. Aí RLE puro já é o melhor possível e a regra unificada degenera
para ele.

## Quando a regra unificada deve perder

Quando refs precisam de marcador (`:N`) por colisão com valores literais
(coluna de inteiros puros). O marcador adiciona 1 B por ref e em coluna de
cardinalidade média a economia some.

→ Predição: para coluna `quantidade` (inteiros 1, 2, 3, ..., 30), regra
unificada empata ou perde para RLE-local puro.

---

## Plano

1. **`01-regra.md`** — formalizar a sintaxe e o algoritmo de escolha por linha
2. **`02-aplicado.md`** — aplicar ao dataset, sort `(valor, produto, qty)`
3. **`03-comparacao.md`** — comparar com C11-híbrido das mesas anteriores
4. **`04-limites.md`** — encontrar onde a regra unificada não basta
