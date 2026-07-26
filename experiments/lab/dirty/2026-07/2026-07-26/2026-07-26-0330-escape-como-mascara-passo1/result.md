# O escape como máscara — passo 1 (2026-07-26-0330)

O escape responde *literal ou referência?* em cada digit-run. Essa sequência é um **fluxo**, e fluxo o formato já comprime.

`inline` = o que se paga hoje (1 B por literal) · `máscara` = o fluxo L/R com RLE burro (`<count><char>`). **Nenhuma é binária** — as duas cobrem qualquer mistura.

## Passo 1 e 2 — o que é possível, e a regra

A máscara só é **aplicável** onde nenhuma fronteira depende do escape (coluna `adjac.` = 0). Ver a seção do bloqueador.

| forma | corpo | decisões | runs | adjac. | inline | máscara | escolha | Δ |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| `cpf` | 3800 | 800 | 1 | 0 | 800 | 4 | **mascara** | -795 |
| `cartao` | 11960 | 2019 | 39 | 6 | 2000 | 104 | **inline** | +0 |
| `ip` | 2851 | 256 | 1 | 0 | 256 | 4 | **mascara** | -251 |
| `cep` | 5990 | 1000 | 7 | 2 | 997 | 22 | **inline** | +0 |
| `telefone` | 8244 | 1780 | 821 | 410 | 1272 | 1660 | **inline** | +0 |
| `data-iso` | 5513 | 1442 | 661 | 318 | 677 | 1327 | **inline** | +0 |
| `email` | 5743 | 1546 | 464 | 150 | 367 | 959 | **inline** | +0 |
| `texto` | 1807 | 25 | 1 | 0 | 0 | 3 | **inline** | +0 |

- aplicável (adjac. = 0) em **3 de 8** formas
- entre as aplicáveis, a máscara vence em **2**
- reconstrução byte-exata **e** RT pelo `decode` REAL nas aplicáveis: **6/6**
- ganho somado: **-1046 B**

O **CPF é o caso que o owner pediu**: 800 decisões, **1 run** — a máscara inteira é `800L`, 4 bytes contra 800 de escape.

## Passo 5 — a decisão pode ser online, com poucos loops?

A escolha **não precisa materializar as duas formas**. Ela é uma conta:

```
adjacencias   = fronteiras que dependem do escape   (0 -> aplicável)
custo_inline  = número de literais
custo_mascara = comprimento do RLE do fluxo  (≈ 2 × runs)
escolha       = o menor dos dois, se aplicável
```

Os **três** são contadores da mesma passada que já percorre o corpo: literais, trocas L↔R, e fronteiras dígito-encosta-dígito. Nenhum encode extra, nenhuma forma materializada para comparar.

| forma | literais | runs | adjac. | decisão pela conta | medindo os bytes | bate? |
|---|---:|---:|---:|---|---|---|
| cpf | 800 | 1 | 0 | mascara | mascara | sim |
| cartao | 2000 | 39 | 6 | inline | inline | sim |
| ip | 256 | 1 | 0 | mascara | mascara | sim |
| cep | 997 | 7 | 2 | inline | inline | sim |
| telefone | 1272 | 821 | 410 | inline | inline | sim |
| data-iso | 677 | 661 | 318 | inline | inline | sim |
| email | 367 | 464 | 150 | inline | inline | sim |
| texto | 0 | 1 | 0 | inline | inline | sim |

Divergências entre a conta e a medição: **0** (a conta acerta em todas).

## Passo 3 — a regra é genérica?

Ela não conhece CPF, nem tipo, nem formato — só conta literais, trocas e adjacências. Aplica-se a qualquer coluna, e onde não compensa (ou não é reconstruível) ela **escolhe o inline**, que é o comportamento de hoje: custo zero de adoção, nenhum caso de código exclusivo.

Genérica sim; **larga não**: pega 2 de 8 formas aqui. O que a limita não é a conta, é a adjacência.

## Passo 4 — dinâmica?

Sim por construção: a escolha é por coluna, computada do próprio dado. Um flag no cabeçalho diz qual forma foi usada. Ligar/desligar é forçar a escolha.

**Não testado ainda**: outros tipos (a máscara é sobre digit-runs; um fluxo análogo existiria para `*`/`~` se algum dia eles pesarem — hoje são 0).

## O bloqueador — terceira aparição, e desta vez ele tem nome

O seq-RLE **não** é o problema aqui: flip (lab `0038`) e sem-escape (lab `0200`) **apagavam** o escape, e o marcador `*N±d|` localiza o dígito incrementável *pelo escape*. A máscara **reconstrói** o escape antes de tudo — é camada de borda, o core não muda. Verificado: marcadores com corridas divergentes após reconstrução nas colunas aplicáveis: **0**.

O que trava é outra coisa, e é a mesma dos dois labs anteriores vista de frente:

> O escape carrega **duas** informações — o **tipo** (literal × referência) e a **fronteira** entre corridas de dígito. A máscara captura só o tipo.

Onde uma referência encosta num literal-dígito, tirar o escape **funde** as duas corridas e nenhuma máscara reconstrói isso:

```
original   56\033-\0910      (`56` = referência, `033` = literal)
sem escape 56033-0910         <- `56` e `033` fundiram
volta      56033-\0910       <- fronteira perdida, corpo diferente
```

| forma | adjacências |
|---|---:|
| cpf | 0 |
| cartao | 6 |
| ip | 0 |
| cep | 2 |
| telefone | 410 |
| data-iso | 318 |
| email | 150 |
| texto | 0 |

**É por isso que a regra precisa do contador de adjacência** — sem ele o `cartao` daria −1895 B e um wire corrompido. Com ele, a regra recusa sozinha, e recusar é escolher o inline de hoje: custo zero.

Próximo passo natural (não medido): um **delimitador de fronteira** mais barato que o escape, pago só nas adjacências — no `cartao` seriam 39 contra 2000.

