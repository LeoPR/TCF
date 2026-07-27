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

## Bugs 3 e 4 — achados por auditoria adversarial

Rodei 6 lentes independentes sobre o lab. As 18 hipóteses que elas levantaram **não foram
refutadas por agente nenhum** — a fase de refutação inteira caiu por limite de gasto —
então **verifiquei cada família à mão**, rodando código. Duas eram reais e graves.

### Bug 3 — a `FAIXA` incluía dígitos: o delimitador **funde** com a corrida

```
eleito '0'   canônico  1\22.\33.\44
             V3        1022.33.44
             volta     1022.33.44     ← o scanner engoliu o delimitador
```
Reconstrução deixa de ser exata. Reproduzido com uma coluna de 2 linhas.

### Bug 4 — a `FAIXA` incluía letras: o sufixo V3 pousa no slot do **discriminador**

`#TCF.8` tem 6 chars, então o sufixo cai no índice 6 — exatamente onde vivem `b`, `n`, `s`,
`H`, `M`. Uma coluna de **string** com alfabeto largo elegia `b` e emitia `#TCF.8b`:
**byte-idêntico** ao cabeçalho canônico de uma coluna bool.

**A correção exclui por classe, não por lista** — só pontuação. Fecha os dois de uma vez e
continua fechado quando surgir tag nova:

```
FAIXA = !"#$%&'()+-./:;<=>?@[]_`{}      26 chars (era 88 — caiu 70%)
```

Nas 31 colunas aplicáveis o mínimo de chars livres ficou em **23 de 26**. Margem menor, mas
nenhuma coluna sem opção — em amostra pequena.

### Uma hipótese foi refutada

A lente do seq-RLE afirmou que o corpo V3 destrói o contrato `*N+d|` com corrupção
silenciosa. **Falso**: a reconstrução é byte-exata mesmo com marcadores presentes, e
alimentar um `.tcfp` direto ao `decode` **falha alto** (`ValueError`) — o fail-loud soldado
antes nesta sessão pega.

## O resultado depois das 4 correções

| | |
|---|---|
| **RT com transformação real** (regra ativou, corpo foi e voltou) | **17/17** |
| RT de colunas que recusaram — é **identidade**, não prova | 14 |
| divergência de tipo | **0** |
| N/A (corpo não é declaração) | **3** — bool densas (`b132` + base64) |
| Δ somado | **−1077 B** (observação, não resultado) |

**O decoder real nunca recebe a grafia da proposta** — recebe o canônico reconstruído. Esse é
o desenho (camada de borda), mas precisa ser dito: o que está provado é a **reconstrução**.
Reportar "30/30" antes misturava 17 transformações com 14 identidades.

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
recusa por um teste de 1 linha. Os bugs 1 e 2 foram para **remover** esperteza minha; os 3 e
4, para trocar uma faixa permissiva por uma **regra de classe**.

### O par crítico só passou a ser exercido depois da auditoria

Eu tinha escrito que `str-zero-e-null` e `binario-01-null` provavam o conserto do bug 1. Não
provavam: nelas o FLOOR **recusa**, então o RT era **identidade**. A coluna `zero-null-ATIVO`
foi construída depois para fechar isso — `"0"` como dado, `null`, e corridas de dígito
suficientes para a regra ativar. Ela ativa (**−99 B**) e o RT passa.

## Limites

- **Nada soldado.** `src/tcf` intocado.
- Até 50 linhas por coluna (2 fixtures reais têm menos — a tabela diz o `n` real). Bom para
  achar bug, **inútil para medir ganho**. Os Δ são observação.
- Denso e hierárquico saem como N/A — recusados, **não testados por dentro**.
- Multi-col não testado.
- A `FAIXA` caiu de 88 para 26 chars. Nas 31 colunas aplicáveis sobraram no mínimo 23, mas
  uma coluna de texto pesada em pontuação pode apertar isso. **Não medido em escala.**
- As 18 hipóteses da auditoria foram verificadas **por mim, à mão** — a fase de refutação
  automática não rodou (limite de gasto), então o "descartadas" que ela reportou não vale
  nada. 4 famílias confirmadas, 1 refutada; as de higiene do lab (leitor mudo, `zip` sem
  guarda de comprimento, escala declarada errada, magic não conferido) foram corrigidas.
- Continua aberto desde o `1913`: se o delimitador virar grafia **canônica**, o seq-RLE ainda
  localiza o dígito incrementável pelo escape.

## Rodar

```
python run.py
```
`cruzado.py` tem o mecanismo; os dois bugs estão documentados no docstring das funções onde
moravam (`_opaca` e `decide`).
