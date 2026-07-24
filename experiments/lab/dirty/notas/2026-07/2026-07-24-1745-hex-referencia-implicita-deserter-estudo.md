# hex no n, referência implícita (índices reservados), canal de exceção — estudo [estudo]

**Data**: 2026-07-24 17:45. Owner pediu evidência (mesmo que matemática) e revisão de 4 exemplos
concretos antes de decidir. Tudo abaixo é verificado contra `src/tcf` real. NÃO decide, NÃO implementa.

## 1. Hex no `n` — CORREÇÃO da nota `1710`: não há ambiguidade (é posicional)

A nota `2026-07-24-1710` alegava que hex colidiria com o namespace de subtipos do `<modo>`. **Errado**:
o parser é posicional puro — `modo_c, ndig = resto[:1], resto[1:]` (`decoder.py:259`). O modo é
**sempre o 1º char**, consumido antes de olhar `n`. Verificado: `#TCF.8ba40` → `modo='a', n='40'`,
sem ambiguidade mesmo com letra no modo. A "questão posicional" do owner procede.

Ganho em bytes (sem a objeção de ambiguidade, que caiu):

| n | dec | hex | ganho |
|---:|---:|---:|---:|
| 64 | 2 | 2 | 0 B |
| 100 | 3 | 2 | 1 B |
| 1000 | 4 | 3 | 1 B |
| 65535 | 5 | 4 | 1 B |

Pequeno (0-1 B), mas agora **sem custo de segurança** — vira só decisão de legibilidade vs bytes.

## 2. Os 4 exemplos do owner (referência implícita / índices)

**A — `*64|false` hoje**: NÃO é referência a índice. É RLE puro. O `^N` (quando aparece) é eid **por
ORDEM DE 1ª APARIÇÃO no dado**, não fixo:
```
['false','true',...] -> false=^1, true=^2
['true','false',...] -> true=^1, false=^2   (INVERTE conforme o dado)
```
A tabela fixa "0=null,1=false,2=true" **não existe no código** — só no plano
`substituicao-indices-especiais-plano.md` (registrado, não soldado).

**B — `*64|1` com tabela reservada (0=null,1=false,2=true; dado real começa em 3)**: ideia correta,
mas NÃO é reaproveitar o core — hoje uma linha dígito-puro é escapada (`\1`) pelo core genérico. Isso
exige uma **gramática NOVA e dedicada** pro corpo tipado: RLE sobre ÍNDICES pequenos em vez de RLE
sobre literais string. **É efetivamente um TERCEIRO modo de corpo** (nem core-literal, nem
denso-base64) — vale registrar como candidato de estudo, não presumir resolvido pelo core existente.

**C — `*64|f` (letra mnemônica)**: via simples, reusa o core sem mudar gramática, só troca o alfabeto
`true/false`→`f/t`. Mesma ressalva já medida na nota `1710`: como o `^N` já deduplica, o ganho é
**constante (3-7B por corpo), não proporcional** a N.

**D — `#TCF.8` sem tag + `false` literal**: CONFIRMADO decodifica `['false','false','false']`
(**string**), não bool. Bate com a distinção já estabelecida: sem tag = tipo default string.

**E — desertor `\true` escapando do domínio bool**: HOJE é fail-loud
(`ValueError: valor fora do dominio bool`). Não há mecanismo de escape. Seria um **canal de
exceção/literal** novo — já cotado no plano `.8` §S1 ("canal de literais/exceções"), nunca
implementado. Permitiria `[False, False, "true"]` (lista MISTA) sob a tag `b`, ao custo de 1 char de
escape por desertor, em vez de falhar.

## Terreno aberto (não decidido, registrado pra quando "der")

- Se B vale a pena: precisa medir "RLE sobre índices" vs os 2 modos já soldados (core-literal, denso-
  base64) — um 3º candidato pro FLOOR do ticket `T-TYPED-SINGLECOL-MODE-HEURISTIC`.
- Canal de exceção (E) generaliza pra além do bool (qualquer coluna tipada com "desertores" raros).
- Ponto 3 (bool vs binário vs low-card) — adiado, ver nota `1710`.

Relaciona: [revisão bool×binário×low-card `1710`](2026-07-24-1710-bool-vs-binario-vs-lowcard-revisao.md)
· [namespace do `<modo>` `0322`](2026-07-24-0322-modo-namespace-largura-e-subtipos.md) ·
[índices especiais](substituicao-indices-especiais-plano.md) · ticket `T-TYPED-SINGLECOL-MODE-HEURISTIC`.
