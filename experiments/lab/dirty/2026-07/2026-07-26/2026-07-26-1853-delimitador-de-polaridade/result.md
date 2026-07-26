# O delimitador de polaridade (2026-07-26-1853)

O delimitador marca uma **troca de estado**, não um valor. Custa por **transição**, não por ocorrência — e, por estar *entre* as duas corridas, carrega também a **fronteira**.

```
hoje       56\033-\0910-\4383      1 escape por LITERAL
proposta   56/033-0910-4383        1 byte por TRANSIÇÃO
```

## Medição — as 8 formas do lab `0330` + 2 que contêm `/`

`hoje` = escapes de dígito · `transições` por polaridade inicial · `char` e `início` são o `min` sobre candidatos × polaridade.

| forma | corpo | hoje | transições (R) | transições (L) | char | início | custo | Δ corpo |
|---|---:|---:|---:|---:|:-:|:-:|---:|---:|
| `cpf` | 3800 | 800 | 200 | 0 | `/` | L | 0 | -800 |
| `cartao` | 11960 | 2000 | 513 | 25 | `/` | L | 25 | -1975 |
| `ip` | 2851 | 256 | 64 | 0 | `/` | L | 0 | -256 |
| `cep` | 5990 | 997 | 500 | 5 | `/` | L | 5 | -992 |
| `telefone` | 8244 | 1272 | 504 | 824 | `/` | R | 504 | -768 |
| `data-iso` | 5513 | 677 | 458 | 689 | `/` | R | 458 | -219 |
| `email` | 5743 | 367 | 472 | 788 | `/` | R | 472 | +105 |
| `texto` | 1807 | 0 | 0 | 25 | `/` | R | 0 | +0 |
| `data-br` | 4905 | 726 | 457 | 681 | `!` | R | 457 | -269 |
| `cnpj-mascara` | 9774 | 1714 | 975 | 515 | `!` | L | 515 | -1199 |

- reconstrução byte-exata da grafia canônica **e** RT pelo `decode` REAL: **20/20**
- ganho somado nas 10 formas: **-6373 B**
- formas em que a proposta perde: **1**

## Contra a máscara (lab `0330`)

A máscara cobria 3 de 8 formas — travava na **adjacência**, porque capturava só o TIPO e perdia a FRONTEIRA. O delimitador carrega as duas.

| forma | escapes hoje | máscara (0330) | delimitador | quem vence |
|---|---:|---|---:|---|
| `cpf` | 800 | 4 | 0 | **delimitador** |
| `cartao` | 2000 | n/a (adjacência) | 25 | **delimitador** |
| `ip` | 256 | 4 | 0 | **delimitador** |
| `cep` | 997 | n/a (adjacência) | 5 | **delimitador** |
| `telefone` | 1272 | n/a (adjacência) | 504 | **delimitador** |
| `data-iso` | 677 | n/a (adjacência) | 458 | **delimitador** |
| `email` | 367 | n/a (adjacência) | 472 | hoje |
| `texto` | 0 | 3 | 0 | **delimitador** |
| `data-br` | 726 | — (não estava no `0330`) | 457 | — |
| `cnpj-mascara` | 1714 | — (não estava no `0330`) | 515 | — |

O `cpf` é o caso que motivou tudo: a coluna é **toda literal**, então começar em `L` custa **0 transições** — os 800 escapes somem por completo, sem canal separado e com a linha auto-contida.

## O delimitador é mais expressivo que o escape de hoje

Hoje `literal` seguido de `referência` **não tem grafia**: `\03356` lê tudo como um literal só. Com o delimitador tem — `/033/56`. Foi essa fronteira inexistente que travou a máscara e o flip.

## Passo 5 — a escolha é online?

```
hoje        = corridas literais
transicoes  = trocas de estado (por polaridade inicial, 2 contadores)
ocorrencias = quantas vezes o char candidato já está no dado
escolha     = min sobre (candidato x polaridade)
```

Todos são contadores da **mesma passada** que já percorre o corpo. Nenhuma forma é materializada para comparar.

Candidatos varridos: `/`, `!`, `?`, `&`, `%`, `#`. A tabela abaixo mostra por que o char não pode ser fixo:

| forma | ocorrências no dado, por candidato |
|---|---|
| cpf | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| cartao | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| ip | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| cep | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| telefone | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| data-iso | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| email | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| texto | `/`=0 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| data-br | `/`=116 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |
| cnpj-mascara | `/`=25 · `!`=0 · `?`=0 · `&`=0 · `%`=0 · `#`=0 |

Onde o candidato aparece no dado, cada ocorrência passa a custar escape — por isso ele entra na conta e o `min` decide por coluna.

## O seq-RLE

Como no lab `0330`, o corpo canônico é **reconstruído** antes de qualquer coisa — o delimitador é camada de borda, o core não muda. Verificado com `find_escape_digit_runs` do próprio core: marcadores `*N±d|` com corridas divergentes após reconstrução: **0**.

**Aberto**: se o delimitador virar grafia canônica (e não camada de borda), o seq-RLE precisa localizar o dígito incrementável pela polaridade em vez de pelo escape. Não medido aqui.

