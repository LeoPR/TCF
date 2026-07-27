# 2026-07-26-2126 — Polaridade × tipos: bool, binário, null

> *"faça uma avaliação com o que já temos, combinado com os dados booleanos, binários, null
> até o momento (…) escala pequena, não é teste de resistência nem benchmark, é só pra ver
> comportamento e pequenos bugs."*

**33 colunas × 50 linhas** (18 sintéticas + 15 reais). Achou **2 bugs**, os dois meus, e os
dois só apareceram porque o RT compara **valor e tipo, elemento a elemento**.

## Bug 1 — a string `"0"` virando `null` (corrupção silenciosa)

Eu escrevi uma regra "esperta": tratar a linha `0` como **opaca**, porque é o slot nulo. Errado
— e polaridade-cega.

Sob polaridade `L` o `0` cru **já é o literal** `"0"`; é o **null** que precisa da troca. A
regra fazia o literal `\0` voltar como `0`:

```
canônico   *2|\0        <- a string "0", duas vezes
proposta   *2|0
volta      *2|0         <- virou null
```

Um RT frouxo não veria: o tamanho da lista bate, o tipo `list` bate. Só a comparação
elemento a elemento pega. As colunas `str-zero-e-null`, `str-zero-misto`, `binario-01` e
`real-adult-capgain-int` (real!) falharam.

**A correção foi tirar a regra especial.** O null é referência ao slot 0, e a máquina de
polaridade já classifica dígito nu como `R` = referência. Ela acerta sozinha:

```
#TCF.8n                    #TCF.8n!!
0        <- null           !0        <- troca p/ referência = null
\8729                      8729      <- literal, polaridade L
\24894                     24894
```
(`outputs/int-null-wire-normal.tcf` × `outputs/int-null-wire-V3.tcfp`)

## Bug 2 — o FLOOR não contava o próprio prefixo

`int-ordenado-null`: 7 escapes, 6 transições → a regra ativava e o wire **crescia 1 byte**,
porque o prefixo V3 custa 2. O FLOOR tem de incluir tudo que a proposta paga — é o mesmo
padrão do `seq-RLE` e do `min(tcf, raw, dict, split)` do multi-col. Corrigido; empate agora
fica com a grafia de hoje.

## O resultado depois das correções

| | |
|---|---|
| RT estrito (valor **e** tipo) | **30/30** |
| divergência de tipo | **0** |
| delimitador ativa | **16 de 30** aplicáveis |
| N/A (corpo não é declaração) | **3** — as colunas bool densas (`b132` + base64) |
| Δ somado | **−993 B** (observação, não resultado — 50 linhas é pouco) |

### Como cada tipo se comportou

| tipo | comportamento |
|---|---|
| **bool denso** (`b132`) | **N/A** — o corpo é base64, o mecanismo recusa antes de olhar |
| **bool esparso** (`b` + `true`/`false`/`0`) | recusa: 0 escapes de dígito, nada a economizar |
| **null puro / quase tudo** | recusa: 0 escapes |
| **null esparso** | ativa, −46 B |
| **int/float tipados** (`n`) com null | ativa em 3 de 4, até −80 B |
| **binário `"0"`/`"1"`** | recusa — 2 escapes não pagam o prefixo |
| **formatadas com null** | ativa, o maior ganho (`cartao-null` −171 B, `cpf` −132 B) |
| **texto real com null** | recusa (`email`, `nome_fantasia`: 0 escapes) |

O null com RLE fica legível: `*24|!0` = 24 nulls seguidos, uma troca só.

## O que isto diz sobre o mecanismo

Ele **não precisou de caso especial para tipo nenhum**. As tags `b`/`n`/`s` seguem o fluxo
normal, o null segue como referência, e onde o corpo não é declaração (`b<N>`, `H`) a regra
recusa por um teste de 1 linha. As duas correções foram para **remover** esperteza minha, não
para adicionar tratamento.

E o par crítico que eu tinha inventado de propósito — `"0"` como dado **e** como slot nulo na
mesma coluna — hoje **recusa sozinho**, porque 1 ou 12 escapes não pagam o prefixo. Não é
sorte: é o FLOOR fazendo o trabalho dele.

## Limites

- **Nada soldado.** `src/tcf` intocado.
- 50 linhas: bom para achar bug, **inútil para medir ganho**. Os Δ são observação.
- Denso e hierárquico saem como N/A — recusados, **não testados por dentro**.
- Multi-col não testado.
- Continua aberto desde o `1913`: se o delimitador virar grafia **canônica**, o seq-RLE ainda
  localiza o dígito incrementável pelo escape.

## Rodar

```
python run.py
```
`cruzado.py` tem o mecanismo; os dois bugs estão documentados no docstring das funções onde
moravam (`_opaca` e `decide`).
