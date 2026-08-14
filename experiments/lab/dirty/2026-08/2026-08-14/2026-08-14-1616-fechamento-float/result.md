# Resultado — FLOAT fechado

12 bordas + 5 colunas reais nos 5 eixos, **0 falhas**. Este lab não mede ganho (já medido:
8% agregado em 30 colunas). Ele verifica conformidade e **declara as peculiaridades**.

## Eixo 5 — o que atravessa, o que é recusado

| borda | resultado | wire |
|---|---|---|
| `float-exato` (`3.0`) — o "`1.`" | **RT ok** | `*3+1,0\|\3.\0` |
| `zero-negativo` (`-0.0`) | **RT ok, sinal preservado** | `-*!0.0` |
| `cientifica-pequena` (`1e-5`) | RT ok | `\1*e-\05` |
| `cientifica-grande` (`1e20`) | RT ok | `\1*e+\20` |
| `max-float` (`1.797…e308`) | RT ok | — |
| `subnormal` (`5e-324`) | RT ok | `5e-324` |
| `precisao-suja` (`0.1+0.2`) | RT ok | `!0.3*0000000000000004` |
| `misto-int-float` (`[1, 2.5, 3]`) | RT ok, **cada tipo preservado** | — |
| `com-nulo` | RT ok | — |
| `nan` · `infinito` · `menos-infinito` | **recusa fail-loud** | — |

## Eixos 1–4 em colunas reais

| coluna | disc | `nature=` | `min_len=` | `IntPadSpec` serve? | RT (tipo+sinal) |
|---|---|---|---|---|---|
| `wine.density` | `n!` | processado, FLOOR recusou | aceito | **não** | ✓ |
| `wine.alcohol` | `nB77d0` | processado, FLOOR recusou | aceito | **não** | ✓ |
| `tpch.l_discount` | `nB47d0` | processado, FLOOR recusou | aceito | **não** | ✓ |
| `tpch.l_quantity` | `nB67d0` | processado, FLOOR recusou | aceito | **não** | ✓ |
| `retail.UnitPrice` | `nB77d0` | processado, FLOOR recusou | aceito | **não** | ✓ |

A porta que o weld de hoje abriu **funciona para float também**: `nature=` é processado e o
FLOOR recusa (comportamento correto), e `min_len=` é aceito. Antes deste weld, ambos eram
`ValueError` na rota tipada.

## O que o float tem em COMUM (o que o owner quer maximizar)

Tudo, exceto o que está na próxima seção:

- **dispatch**: uma linha em `_tipo_single_col`, tag `n` — a mesma do int;
- **candidatos**: percorre o mesmo `min()` — RLE, seq-RLE, polaridade (`n!`, `n!!`) e **bN de
  domínio** (`nB77d0`), que é o mesmo bN de bool, int e string;
- **API**: aceita `nature=` e `min_len=` desde hoje, como os demais;
- **wire**: tag no índice 6, sufixos no 7 — mesma gramática;
- **RT**: preserva o tipo, como todos.

## As PECULIARIDADES do float (declaradas)

1. **É a metade "flutuante" de uma tag-união.** A tag `n` é `int|float` — o `number` do
   JSON. O tipo concreto **não vem da tag**: vem da **grafia**, por elemento. `[1, 2.5, 3]`
   volta `['int','float','int']`. Nenhum outro tipo compartilha tag.
2. **`-0.0` é distinto de `0.0`, e `==` não detecta.** O wire preserva (`-*!0.0`), mas só
   `math.copysign` prova. Qualquer teste de RT para float que use `==` é cego para isso.
3. **NaN e ±Infinito são recusados fail-loud** — ficam fora do JSON (RFC 8259), e aceitar
   seria assimetria (o decode entendendo o que o encode recusa).
4. **A precisão suja quebra a ESCALA, não o RT.** Valores como `10.0333333333333` (médias do
   próprio dataset) impedem uma escala exata `×10^k` — a coluna inteira perde o candidato.
   O round-trip continua perfeito; o que se perde é a otimização.
5. **O `IntPadSpec` não é reaproveitável** — verificado nas 5 colunas reais (`False` em
   todas). Depois de escalar, a largura já fica uniforme e o `int_pad_para` corretamente
   devolve `None`.
6. **A grafia canônica é a do Python.** `1e-5` vira `1e-05`, `1e20` vira `1e+20` — o `render`
   da família `n` é a builtin `str`, e o guard de canonicidade por re-emissão a impõe.

## Veredito

**Float está fechado para o `.8`**: os 5 eixos passam, as bordas estão caracterizadas, o que
é comum é máximo, e as 6 peculiaridades estão declaradas. O spec de escala fica **adiado com
razão escrita** (8% agregado, e a precisão suja o inviabiliza em parte do corpus) — o que é
diferente de adiado sem caracterizar.

Falta na fila: **hora** (sintéticos + eixos) e **datetime** (tudo).
