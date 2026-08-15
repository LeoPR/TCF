# Resultado — datetime: 13 grafias × 8 regimes × 9 mecanismos

**0 falhas** de RT. Só datetime, sem réguas de outros tipos. Orienta, não fecha.

---

## 1. O achado que muda o `T-SPLIT-SINGLE-COL`: **o split vive da ORDEM**

O par de contra-prova (mesmos 2000 instantes, mesma cardinalidade — **só a ordem muda**):

| mecanismo | ordenado | embaralhado | delta |
|---|---:|---:|---:|
| `raw` | 39999 | 39999 | 0,0% |
| **`bN`** | 3197 | 3207 | **+0,3%** |
| **`dict`** | 2854 | 2864 | **+0,4%** |
| `core` | 1229 | 3207 | +160,9% |
| `multi (_best_of)` | 852 | 2874 | +237,3% |
| **`split`** | **842** | **6331** | **+651,9%** |
| `campos-6` | 814 | 6303 | +674,3% |

**Embaralhado, o split passa de melhor (842) a pior que todos (6331)** — e o vencedor vira o
`dict`, com 2864.

Isso é material para o ticket: o **7,13×** que sustenta o `T-SPLIT-SINGLE-COL` foi medido na
`InvoiceDate`, que é **100% não-decrescente e tem 95,71% de linhas repetindo a anterior**. Pelo
que este par mostra, **boa parte daquele número é crédito da ordenação, não do split**. O
ticket não cai — mas o número precisa da ressalva, e a régua honesta passa a ser *"o split rende
X **em coluna ordenada**"*.

E o corolário limpo: **os únicos mecanismos imunes à ordem são `bN` e `dict`** — os de
**igualdade pura**. Tudo que explora vizinhança (OBAT, HCC, seq-RLE, split) desaba quando a
vizinhança some. É a distinção *igualdade × proximidade* que o projeto já tem nomeada,
aparecendo agora como propriedade de robustez.

---

## 2. As 13 grafias — o split é robusto à forma, e morre em duas

Regime fixo (comercial, 2000 linhas, 80 distintos). `raw` ≈ 40 KB:

| grafia | core | split | vencedor | nota |
|---|---:|---:|---|---|
| `YYYY-MM-DD HH:MM:SS` (SQLite/MySQL) | 1229 | **842** | campos-6 | a do corpus |
| `...T...` (ISO/JSON) | 1229 | **842** | campos-6 | idêntica à anterior |
| `...T...Z` (RFC 3339) | 1230 | **843** | split | +1 B pelo `Z` |
| `...-03:00` (offset) | 1235 | **878** | split | o offset é constante → afixo |
| `.ffffff` (PostgreSQL) | 1236 | **864** | split | o µs vira 7º campo |
| `.fff` (SQL Server/Java) | 1233 | **861** | split | |
| `YYYY-MM-DD HH:MM` (sem segundo) | 961 | **822** | campos-6 | menos campo, menos bytes |
| `DD/MM/YYYY HH:MM:SS` (pt-BR) | 1207 | **842** | campos-6 | **idêntico ao ISO** |
| **`YYYYMMDDHHMMSS`** (compacta) | 1077 | **✗ não aplica** | campos-6 | **1 grupo de dígito** |
| `YYYYMMDDTHHMMSS` (ISO básica) | 1079 | 974 | campos-6 | o `T` salva: 2 grupos |
| **`MM/DD/YYYY hh:mm:ss AM/PM`** | 1392 | **✗ não aplica** | core | **template não-uniforme** |
| **epoch segundos** | 981 | ✗ não aplica | core | 1 grupo |
| **epoch milissegundos** | 1025 | ✗ não aplica | core | 1 grupo |

Três leituras:

- **A grafia com separador é quase irrelevante para o split** — pt-BR, ISO e SQL dão os
  **mesmos 842 B**. O split lê a estrutura, não a convenção.
- **A grafia compacta mata o split.** `YYYYMMDDHHMMSS` é *um* grupo de dígitos, e o gate exige
  ≥2 campos. Quem economiza 5 chars por linha na origem **perde 235 B por 2000 linhas** no
  formato. O `T` da forma básica ISO salva (2 grupos) mas ainda fica 15% pior que a estendida.
- **`AM/PM` mata o split por outro motivo**: o template exige as partes não-dígito **idênticas**
  em todos os valores, e `AM` ≠ `PM`. Uma coluna de 12h nunca splita — e é a única grafia em
  que o `core` vence.

---

## 3. Os 8 regimes — e um caso em que o núcleo **infla**

Grafia fixa (`YYYY-MM-DD HH:MM:SS`):

| regime | k | core | split | melhor | quem |
|---|---:|---:|---:|---:|---|
| comercial (o do corpus) | 80 | 1229 | 842 | **814** | campos-6 |
| log alta cardinalidade | 2000 | 18185 | 3519 | **3491** | campos-6 |
| batimento 5 min | 2000 | 19786 | 3275 | **58** | **epoch-s** |
| batimento 1 s | 2000 | 590 | 2136 | **48** | **separado** |
| esparso multi-ano | 2000 | **43957** | 9261 | **9233** | campos-6 |
| um dia só | 1763 | 23981 | 6683 | **6655** | campos-6 |
| constante | 1 | 35 | ✗ | **25** | epoch-s |
| comercial embaralhado | 80 | 3207 | 6331 | **2864** | dict |

Dois achados:

**(a) No `esparso-multi-ano` o núcleo produz 43957 B para uma entrada de 39999 B — ele
INFLA 9,9%.** A rota single-col não tem `raw` no `min()` (só core+polaridade e bN); o multi tem
(`min(tcf, raw, dict, split)`). É a mesma causa-raiz do `T-UM-CAMINHO-SO`, agora com um caso em
que o resultado é **pior que não fazer nada**.

**(b) A transformação certa bate o split por ordens de grandeza — mas só no regime certo.**
No batimento de 5 min, `epoch-s` dá **58 B** contra 3275 do split: **56×**. Porque epoch de um
batimento regular é uma **progressão aritmética perfeita**, e o seq-RLE a esmaga. É a mesma lei
do `data-iso` e do ordinal de hora: *deixar a aritmética visível vale mais que qualquer
empacotamento*. No batimento de 1 s, `separado` dá 48 B pela mesma razão.

E o simétrico: no `log-alta-card` e no `esparso`, onde não há aritmética, `epoch-s` fica
**10818** e **20683** — pior que o split. **Nenhuma transformação domina; cada uma serve um
regime.**

---

## 4. Ressalva de comparação — o `campos-6` não é competidor honesto

O `campos-6` decodifica para um **dicionário de 6 colunas**, não para as strings originais: ele
**descarta a grafia**. Seu RT é contra o dict, não contra a coluna.

Então ele **não é uma alternativa ao split** — ele é o **piso teórico dele**. A diferença é o
custo de guardar o template e reconstruir a string:

| regime | `campos-6` (sem grafia) | `split` (reconstrói) | custo do template |
|---|---:|---:|---:|
| comercial | 814 | 842 | **28 B** |
| log alta card | 3491 | 3519 | 28 B |
| esparso | 9233 | 9261 | 28 B |

**28 bytes, constante** — o template viaja uma vez. Ou seja: o split já opera a **28 B do piso**
do seu próprio mecanismo. Não há gordura ali.

---

## 5. O que isto orienta

1. **O `T-SPLIT-SINGLE-COL` precisa da ressalva de ordem.** O split é o melhor candidato para
   datetime **ordenado** — e o pior para embaralhado. Qualquer promoção dele a default tem de
   consultar a ordem, ou o `min()` tem de continuar decidindo (que é o que já faz).
2. **A rota single-col deve ganhar o `raw` no `min()`** antes de qualquer coisa mais fina — há
   um caso medido em que ela infla 9,9%.
3. **A grafia compacta e a de 12h são pontos cegos declarados** — não splitam, por razões
   diferentes (1 grupo; template não-uniforme).
4. **O caminho específico para datetime não é "um spec"** — é escolher **por regime** entre
   split e transformação aritmética, e as duas já existem. O que falta é a rota single-col
   enxergá-las.

O desenho de um mecanismo mais específico para datetime está na nota irmã.
