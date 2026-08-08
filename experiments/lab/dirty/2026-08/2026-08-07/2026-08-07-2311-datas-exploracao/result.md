# Resultado — DATA como tipo (exploração)

**2026-08-07 · dirty · 90 medições, 4 eixos, RT conferido em todas**

---

## O achado

**O TCF já tem o mecanismo que esmaga data. A grafia ISO é que não alcança ele.**

```
120 datas diárias, ISO      →  97 B      #TCF.8!\n!2026-0*1-*0*1\n1..3!2\n*7+1|6!3\n…
120 datas diárias, ordinal  →  22 B      #TCF.8\n*120+1|\739617
```

O segundo wire é o **seq-RLE multi-delta** (`*N+M|`, ADR-0016 ~ PFOR-DELTA): *120 valores,
passo +1, começando em 739617*. Ele já existe, já está soldado, e resolve o caso inteiro em
uma linha.

Escrita como `2026-01-01`, a mesma sequência vira picotada em fragmentos de afixo do OBAT —
porque **a aritmética some quando o número vira texto com separador**. `2026-01-31` → `2026-02-01`
não é "+1" em nenhum campo isolado.

### E a distância cresce com a irregularidade do passo

| regime (ISO) | n=120 | n=1200 | ordinal (n=1200) | fator |
|---|---:|---:|---:|---:|
| `R1-diario` (passo 1) | 97 B | 829 B | 23 B | **36×** |
| `R2-semanal` (passo 7) | 544 B | 5504 B | 23 B | **239×** |
| `R3-mensal` (passo 30) | 1051 B | 14871 B | 24 B | **620×** |
| `R8-descendente` (passo −1) | 405 B | 892 B | 23 B | **39×** |

O passo diário é o único que a grafia ISO acompanha razoavelmente (o último dígito
incrementa). Semanal e mensal quebram o prefixo com frequência e o custo explode. **O
ordinal é indiferente ao passo** — para o seq-RLE, +1, +7 e +30 são o mesmo trabalho.

---

## Mas não existe representação vencedora

Três hipóteses naive medidas sobre os mesmos dados (`H-split` = campos separados,
`H-delta` = 1ª data + diferenças, `H-epoch` = ordinal):

| regime | TCF hoje | split | delta | epoch | vence |
|---|---:|---:|---:|---:|---|
| `R1-diario` | 829 | 1365 | 36 | **23** | epoch |
| `R2-semanal` | 5504 | 2040 | 36 | **23** | epoch |
| `R3-mensal` | 14871 | 2455 | 37 | **24** | epoch |
| `R4-repetido-k5` | 664 | 1079 | **243** | 635 | delta |
| `R5-agrupado` | 980 | 766 | **241** | 529 | delta |
| `R6-espalhado` | 11052 | **2866** | 5975 | 8232 | split |
| `R7-espalhado-ord.` | 10221 | 2060 | **1117** | 6494 | delta |
| `R8-descendente` | 892 | 1376 | 37 | **23** | epoch |

*(n=1200, ISO)*

- **epoch** ganha quando o passo é regular — e ganha por ordens de grandeza;
- **split** ganha quando as datas estão espalhadas sem ordem: aí cada campo isolado é
  baixa-cardinalidade (12 meses, 31 dias) e o bN/RLE pega cada um;
- **delta** ganha no meio do caminho: repetição e agrupamento;
- **o TCF de hoje não ganha em regime nenhum.**

Isto é exatamente o padrão que o owner descreveu: *várias facetas, registra as duas, escolhe
por compressão*. Data precisa de **mais de uma representação candidata**, não de uma.

---

## Eixo FORMATO — a grafia importa mais que o tamanho

n=120, sequência diária, mesma informação:

| formato | len | bytes | bytes/valor |
|---|---:|---:|---:|
| `ano` | 4 | 18 | 0.15 |
| `epoch-dia` | 6 | **22** | 0.18 |
| `ano-mes` | 7 | 46 | 0.38 |
| `compacto` (`20260101`) | 8 | 89 | 0.74 |
| `us` / `extenso` / `br` / `ponto` / `iso-invertido` | 10-11 | 93–96 | 0.78–0.80 |
| `iso` | 10 | 97 | 0.81 |

O `compacto` (sem separador) é **8% menor** que o ISO com o mesmo conteúdo — o separador
não é só 2 bytes por valor, ele **quebra o afixo**. E o `epoch-dia`, com 6 chars, faz 4,4×
melhor que o ISO com 10.

**A ordem dos campos quase não importa** (`br`, `us`, `ponto`, `iso-invertido` ficam todos
entre 93 e 96 B). O que importa é **haver separador** e **onde fica a parte que varia**.

---

## Eixo PRECISÃO — o que custa é o campo que VARIA

n=120, mesmo instante-base, precisão crescente:

| precisão | k | bytes | Δ |
|---|---:|---:|---:|
| `P1-ano` | 1 | 18 | — |
| `P2-ano-mes` | 1 | 22 | +4 |
| `P3-data` | 1 | 25 | +3 |
| `P4-data-hora` | 120 | **725** | **+700** |
| `P5-+segundos` | 120 | 1322 | +597 |
| `P6-+milissegundos` | 120 | 1802 | +480 |
| `P7-tz-Z` | 120 | 1442 | −360 |
| `P8-tz-offset` | 120 | 1686 | +244 |

O penhasco está entre `P3` e `P4`: **+700 B por acrescentar `T%H:%M`**. Até `P3` a coluna é
constante (`k=1`) e o RLE resolve em 25 B; a partir de `P4` o campo que varia entra e cada
nível a mais custa centenas de bytes.

Não é o **comprimento** que cobra — é a **cardinalidade que o campo novo introduz**. O
`P7-tz-Z` é 1 char maior que o `P5` e sai **360 B menor**, porque o `Z` constante ajuda o
afixo a fechar o valor.

---

## Eixo TIMESTAMP — regularidade vale mais que estrutura

| regime | n=1200 | bytes/valor |
|---|---:|---:|
| `T1-log-mesmo-dia` (segundos correndo) | 372 | **0.31** |
| `T3-varios-dias` (dia+hora regulares) | 1151 | 0.96 |
| `T4-hora-redonda` | 1151 | 0.96 |
| `T2-log-esparso` (mesma data, saltos irregulares) | **14010** | **11.68** |

`T1` e `T2` têm o **mesmo formato, a mesma data e o mesmo comprimento**. A diferença é só a
regularidade do passo — e ela custa **38×**.

---

## O que isso sugere (não são tickets)

1. **Uma natureza de data faria sentido, e o mecanismo de destino já existe.** O padrão é o
   das natures já soldadas (CPF/CNPJ/IP, ADR-0015): pré-transformação que reescreve o valor
   pra uma forma que o core já sabe esmagar. Aqui a forma é o **ordinal**, e o alvo é o
   `*N+M|`.
2. **Uma representação só não resolve.** Nenhuma das três hipóteses ganha em todos os
   regimes. Se virar natureza, ela precisa entrar como **candidato no `min()`**, igual ao bN
   — nunca como substituição.
3. **O split estrutural (`%`, ADR-0026) não alcança single-col.** Ele existe e é candidato do
   `fallback` **multi-col**. No `R6-espalhado` ele seria 3,9× melhor que o wire de hoje e não
   é sequer consultado. Isso é lacuna de **rota**, não de mecanismo — a mesma classe que era
   o `T-BN-TIPADO`.
4. **Os números `H-*` não incluem o custo de declarar o formato.** Converter data→ordinal
   perde a grafia; alguém tem de guardar "isto era ISO". É custo fixo de header, mas não
   está medido aqui — **qualquer decisão precisa medir isso antes**.

## O que este lab NÃO fez

- Não mediu CPU nem memória (é `.9`).
- Não testou datas **inválidas ou ambíguas** (29/02 em ano não-bissexto, `01/02` sendo BR ou
  US, ano de 2 dígitos) — é o eixo de **borda** e falta.
- Não testou **mistura de formatos na mesma coluna**, que é o caso real de dado sujo.
- Não olhou **fuso com transição de horário de verão**, onde o mesmo horário local aparece
  duas vezes.
- `H-split` é estimativa grosseira (soma dos corpos, sem o envelope real do multi-col).
