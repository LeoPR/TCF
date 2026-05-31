# Algoritmo — formato normalizado + previsão por camadas

Este experimento não muda o **algoritmo da árvore Patricia**
(idêntico aos exps 02/03). Muda dois aspectos:

1. **Régua de formato unificada** entre as duas serializações.
2. **Função de previsão simbólica** que reproduz o encoder
   contando chars por camada.

## Regra de formato unificada

Aplicada a `encode_separado.py` e `encode_inline.py`:

- **Sem comentários no arquivo** (eliminação da camada 4).
- **Omitir `1x` em count=1**, tanto em decls com ocorrência (inline)
  quanto em refs (ambas).
- **Manter marcadores macro** (`<patricia>`, `<body>`) — registrados
  na camada 3 mas não comparados.

Sintaxe das linhas:

| Tipo | Sintaxe | Onde aparece |
|---|---|---|
| decl folha (separado) | `noN = folha "X"` | header `<patricia>` |
| decl filho (separado) | `noN = filho_de(noP) + "X"` | header `<patricia>` |
| ref count=1 | `ref:noN` | body |
| ref count>1 | `Mx ref:noN` | body |
| decl folha + 1ª occ count=1 (inline) | `noN: folha "X"` | body |
| decl folha + 1ª occ count>1 (inline) | `noN: Mx folha "X"` | body |
| decl filho + 1ª occ count=1 (inline) | `noN: filho_de(noP) + "X"` | body |
| decl filho + 1ª occ count>1 (inline) | `noN: Mx filho_de(noP) + "X"` | body |
| decl tardia folha (inline) | `noN: decl folha "X"` | body, ao final |
| decl tardia filho (inline) | `noN: decl filho_de(noP) + "X"` | body, ao final |

## Decomposição por camada — `formula.decompor`

`decompor(tcf_text) -> (chars_macro, chars_ref, chars_dados)`:

- **chars_macro**: linhas que são exatamente `<patricia>`,
  `</patricia>`, `<body>`, `</body>` (com newline).
- **chars_dados**: caracteres dentro de aspas duplas — os fragmentos
  dos nós.
- **chars_ref**: todo o resto. Inclui as próprias aspas, sintaxe,
  ids, counts, indentação, newlines de linhas não-macro.

Convenção do dirty:
- **Camada 4 (comentários)**: zero, porque o formato normalizado não
  tem comentários.
- **Camada 3 (macro)**: contado em `chars_macro`, registrado mas não
  pesado na comparação intrínseca.
- **Camada 2 (marcadores de ref)**: contado em `chars_ref`. Onde a
  comparação tem sentido.
- **Camada 1 (dados efetivos)**: contado em `chars_dados`. Idêntico
  entre as duas serializações.

## Previsão simbólica — `formula.prever_*`

`prever_separado(nos, body_rle)` e `prever_inline(nos, body_rle)`
retornam `(macro, ref, dados)` calculando os tamanhos sem chamar o
encoder.

Cada função reimplementa o encoder em modo "char-counting":
- Para cada nó (sortado por id em separado, ou alocado por ordem de
  aparição em inline), soma o overhead da decl + len(fragmento).
- Para cada entry do body, soma o overhead do ref ou da decl
  com ocorrência.
- Em inline, fase 2 itera sobre pais Patricia pendentes até
  estabilizar.

**Validação**: para todos os 16 cenários, `prever_*` retorna o mesmo
total que `len(encode_*().encode("utf-8"))`. Se discrepância, o
modelo de camadas e o encoder estão dessincronizados — bug a
investigar.

## Forma fechada aproximada

Para um nó único com eid de 1 char, frag de comprimento `f`:

| Token | Chars (com newline) |
|---|---:|
| decl folha sep | 16 + f |
| decl folha inline c=1 | 15 + f |
| decl folha inline c>1 | 17 + len(c) + f |
| decl tardia folha inline | 20 + f |
| decl filho sep (eid pai 1c) | 28 + f |
| decl filho inline c=1 (eid pai 1c) | 27 + f |
| ref c=1 | 10 |
| ref c>1 | 12 + len(c) |

Diferença separado − inline para um nó único só com count=1 (caso
mais comum):
- separado paga: decl(16+f) + ref(10) = 26+f
- inline paga: decl-com-occ(15+f) = 15+f
- economia: 11

Para um pai Patricia interno (sem ocorrência):
- separado paga: decl(28+f) — entra no header
- inline paga: decl-tardia(20+f + 5 da palavra `decl `) = 25+f
  — quase igual. Custo extra ≈ 5 (palavra `decl `).

Combinando:

```
delta ≈ -11 * N_unique + 5 * N_pat_int  (chars/bytes)
```

A imprecisão (~10-15 chars por dataset) vem de eids com 2 chars,
counts > 1 nas 1ªs ocorrências, etc. A fórmula exata exige varrer a
árvore.

## Por que a ordenação não muda o delta

A serialização inline difere da separada em duas operações:
1. **Funde** cada decl + 1ª ref num único token (uma vez por nó
   único).
2. **Adiciona** decl tardia para cada nó interno Patricia (uma vez
   por pai sem ocorrência).

Ambas operações dependem só de `N_unique` e `N_pat_int`, que são
**propriedades da árvore**, não do body. A ordem do CSV afeta o
body (quantos refs, em que posição, com que count) — mas as duas
serializações pagam o mesmo overhead pela ordem, em proporção igual.
A diferença entre elas se mantém constante.

A pequena variação (±6 bytes em D4) vem de uma sutileza: quando o
RLE produz um run de count > 1 logo na 1ª ocorrência, o número de
chars do `count` aparece dentro da decl-com-ocorrência inline. Para
counts pequenos (1 char, ex: `2x`, `3x`) a variação é negligível;
para counts maiores (2 chars, ex: `10x`) há ~1 char extra por
ocorrência.
