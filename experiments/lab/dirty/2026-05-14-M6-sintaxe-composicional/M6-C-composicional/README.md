# M6.C — Sintaxe composicional

**Tecnica**: markers entre refs sao OPERADORES com semantica:
- `,` entre refs: concat sem criar ref (efemero)
- `~` entre refs: concat + **cria novo ref auto-nomeado**
- `a..b` (range): cria novo ref auto-nomeado (caso particular)
- Reuso: bare `N` (ref id, sem prefixo `&`)

## Design

### Pairwise (binary, left-assoc)

Chain `a~b~c` cria 2 refs:
- `a~b` → ref X (pos atomico_count + 1)
- `X~c` → ref Y (pos atomico_count + 2)

Reuso `Y` (a chain inteira) = `Y` (1 char se id 1-digit).

### Range cria ref

`3..5` cria ref que e' atalho de `3~4~5` (pairwise). Cria 2 refs
intermediarios (3~4, 3~4~5). Reuso futuro do range usa o ref final.

### Algebra (vs M4.C1' atual)

```
M1.E:        Lr_inline                    | Lr_inline           | savings = 0
M4C1p atual: Lr_inline + 2 (`~tupla~`)    | 1+len(N) (`&N`)     | savings = Lr_inline - 1 - len(N)
M6.C:        Lr_inline (`a~b~c`)          | len(N) (bare id)    | savings = Lr_inline - len(N)
```

Para R reusos: **R bytes/composicao** a favor de M6.C vs M4.C1' atual.

D1 estimativa: ~125 bytes (M4.C1' atual: 138).
Total D1-D4 estimativa: ~615 (M4.C1' atual: 636).

## Sintaxe (gramatica)

Body chars:
- `*` separador (lit-lit, lit-ref boundary)
- `,` concat efemera de refs
- `~` composicao com criacao de ref
- `..` range (entre dois ints)
- `\` escape (literal digit, `*`, `\`, `~`)
- digits = ref id
- letters/symbols = literal char

Reservado em literais: `*`, `\`, `~`. Escapados `\*`, `\\`, `\~`.

Decoder:
1. Mantem `frags` (dict por id) crescendo
2. Linear pass sobre body
3. Lit char inicia ou continua texto literal (cria frag id auto na 1a aparicao)
4. Digit char inicia parse de refs/composicao
5. `~` entre refs: cria 2 novos frags (pairwise pra chain de tamanho 2; para K>2, cria K-1)
6. `,` entre refs: nao cria
7. `a..b` cria K-1 frags (idem chain)

## Limitacao

Detector deve decidir `~` vs `,` por composicao. Custos:
- Composicao com `~`: usa 1 id slot (pra full chain) + K-2 intermediarios
- Composicao com `,`: nao usa nenhum

Reuso da composicao economiza R*(Lr - len(N)) - 0 (ja' que 1a aparicao
e' free overhead).

Limite: muitas composicoes inflacionam ids (1-digit → 2-digit → 3-digit),
reduzindo savings.

## Esperado

D1-D4 estimativa: ~615 bytes (vs M4.C1' atual 636 = -21).
