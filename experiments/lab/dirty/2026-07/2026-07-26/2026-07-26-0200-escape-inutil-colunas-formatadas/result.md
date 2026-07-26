# Escape inútil em colunas formatadas (2026-07-26-0200)

Regra testada: **se o corpo não emite referência de fragmento**, o cabeçalho declara isso e, dentro da declaração, todo dígito é literal — sem escape. Binário por coluna, decidido pelo encoder.

Validação por **leitor independente**, não por inversa (lição do lab `0038`).

## n = 500

| forma | corpo | escapes | refs | seq-RLE quebra | modo vale? | sem-escape | Δ | leitor |
|---|---:|---:|---:|---:|---|---:|---:|---|
| `cpf-mascara` | 9383 | 1950 | 30 | 0 | não | — | +0 | — |
| `cnpj-mascara` | 9774 | 1714 | 774 | 0 | não | — | +0 | — |
| `cep` | 5990 | 997 | 3 | 1 | não | — | +0 | — |
| `telefone` | 8244 | 1272 | 508 | 0 | não | — | +0 | — |
| `cartao` | 11960 | 2000 | 19 | 0 | não | — | +0 | — |
| `placa` | 4908 | 920 | 47 | 0 | não | — | +0 | — |
| `data-iso` | 5513 | 677 | 765 | 0 | não | — | +0 | — |
| `hora` | 5135 | 978 | 340 | 0 | não | — | +0 | — |
| `ip` | 2851 | 256 | 0 | 0 | **sim** | 2595 | -256 | OK |
| `moeda` | 6234 | 1036 | 136 | 0 | não | — | +0 | — |
| `coord` | 6495 | 986 | 0 | 7 | não | — | +0 | — |
| `isbn` | 9224 | 1660 | 736 | 0 | não | — | +0 | — |

- o modo vale em **1 de 12** formas
- economia somada: **-256 B** (-9% do corpo dessas colunas)
- leitor independente: **todas OK**

**Duas razões distintas para o modo não valer**, e a segunda é o achado:

1. a coluna **usa referência de fragmento** — aí o escape está fazendo o trabalho dele, e a regra corretamente recusa;
2. a coluna tem **marcador seq-RLE** — e tirar o escape o quebra em silêncio, porque ele localiza os dígitos incrementáveis PELO escape.

A razão (2) é **o mesmo bloqueador que derrubou o flip** (lab `0038`). Não é específico do flip: atinge **qualquer** esquema que remova o escape de dígito. É o obstáculo comum.

## Variação — o modo depende de `n` e da unicidade?

| forma | n | únicos | refs | modo vale? |
|---|---:|---:|---:|---|
| cpf-mascara | 20 | 20 | 8 | não |
| cpf-mascara | 100 | 100 | 3 | não |
| cpf-mascara | 500 | 500 | 30 | não |
| cpf-mascara | 2000 | 2000 | 421 | não |
| cep | 20 | 20 | 1 | não |
| cep | 100 | 100 | 0 | sim |
| cep | 500 | 500 | 3 | não |
| cep | 2000 | 2000 | 40 | não |
| telefone | 20 | 20 | 3 | não |
| telefone | 100 | 100 | 42 | não |
| telefone | 500 | 500 | 508 | não |
| telefone | 2000 | 2000 | 3048 | não |
| ip | 20 | 20 | 0 | sim |
| ip | 100 | 64 | 0 | sim |
| ip | 500 | 64 | 0 | sim |
| ip | 2000 | 64 | 0 | sim |

É onde a regra mostra o limite: quanto mais valores, mais chance de o HCC achar composição e emitir referência — e aí o modo deixa de valer. **Não é uma propriedade do formato do dado, é do conteúdo.** Por isso tem que ser decidido pelo encoder a cada coluna, não por tipo declarado.

