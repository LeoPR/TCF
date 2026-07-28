# 2026-07-27-2247 — Delimitação do domínio: o espaço completo

Você discordou de eu ter tratado **colisão como veredito**. Procede — colisão é **custo
condicional**, e o escape resolve.

## Quanto o escape custaria, no dado real

Varri **145 colunas categóricas** (`2 ≤ k ≤ 64`) das fixtures do repo, olhando que char inicia
cada valor de domínio:

```
chars que iniciam algum valor:   >  <  -  espaço  ,
```

`=`, `|`, `!`, `?`, `#`, `@`, `%` **nunca** iniciam. Um marcador `=` precisaria de escape em
**zero** dessas 145 colunas.

## As sete, medidas nos mesmos dados

| | como | marcação em | soma (13 colunas) |
|---|---|---|---:|
| **M7** | domínio por último | nenhum | **2940** |
| **M2** | `=` default; `\=` escapa a linha que colide | corpo | **2953** |
| **M1** | `\|` — classe que o core nunca emite | corpo | 2966 |
| **M3** | char eleito do complemento, declarado | ambos | 2966 |
| **M4** | padding a `2^w`; fronteira sai de `w` | corpo | 2967 |
| **M5** | `L<hex>` contagem de linhas | cabeçalho | 2967 |
| **M6** | `:<hex>` bytes — convenção do `.8M` | cabeçalho | 2974 |

Diferença total: **34 B em 13 colunas**. É ruído — o que decide são os outros eixos.

Um detalhe bonito: o **M4 vence exatamente onde `k` é potência de 2** (`k=2`, `k=4`), porque
aí não há slot desperdiçado. Confirma o achado do lab `1647` por outro caminho.

## O que a medição diz, e que o tamanho não mostra

| | leitor streama? | **escritor** streama? | pode recusar? | reusa o quê |
|---|:-:|:-:|:-:|---|
| **M1** | sim | **sim** | não | a gramática de escape do core |
| **M2** | sim | **sim** | não | escape + default-com-desambiguação |
| **M3** | sim | não (elege antes) | **sim** (FAIXA cheia) | a eleição da polaridade (ADR-0035) |
| **M4** | sim | **sim** | **sim** (seq-RLE colapsa) | nada — e **desliga** o seq-RLE |
| **M5** | sim | não (conta antes) | não | — |
| **M6** | sim | não (mede antes) | não | a convenção hex do `.8M` |
| **M7** | **não** | sim | não | o tamanho deduzível do b64 |

**Onde jogar o byte importa mais que quantos.** Marcação no corpo não precisa ser conhecida
antes de escrever — o encoder emite cabeçalho → domínio → marcador → bits, sem voltar atrás.
Marcação no cabeçalho obriga a bufferizar o domínio ou reescrever o campo.

## M1 e M2 são a MESMA família — e isso dissolve o dilema

Eu ia apresentar como "escolha de postura". Não é. O escape do M2 é `\=`, e ele funciona
**pelo mesmo motivo** que o M1: `\` seguido de char fora de `* 0-9 \ ^ ~` é impossível de o
core produzir.

São dois **pontos de pagamento da mesma garantia**:

```
M1   paga ADIANTADO     2 B sempre
M2   paga SOB DEMANDA   1 B + 1 por colisão
```

Break-even exato em **1 colisão**: `j=0` → M2 ganha 1 B; `j=1` → empate; `j≥2` → M1 ganha.

E `j` é **contável enquanto o domínio é construído** — o encoder já o percorre. Logo não é
postura, é `min(1 + j, 2)`: um FLOOR computável, do mesmo feitio do da polaridade. Nos dados
reais `j = 0` em 145 de 145 — o M2 venceria sempre, **sem que a correção dependa disso**.

O veneno mostra o M2 funcionando no pior caso (3 escapes):

```
#TCF.8B278
\=a          ← dado escapado
\=b
\=c
=GGGG…       ← o marcador
```

## Sobre reusar o multi-col

O `.8M` já declara tamanho por coluna em hex (`multi/core.py:_serialize`) — o **M6 é essa
convenção**. Mas é o mais caro dos sete, e o single-col não pode depender do multi para se
ler: seria reimplementação, não reuso.

O reuso que **de fato se paga** é outro, e já está nos vencedores: o M1/M2 usam a gramática de
escape do core, e o M3 usa a eleição de char da polaridade (ADR-0035). Nenhum é código novo.

## Recomendação revisada

| | |
|---|---|
| **default** | `min(M1, M2)` — mesma garantia, ponto de pagamento escolhido por contagem |
| **modo extra** | **M7** (domínio por último): 13 B mais barato no total, para lote fechado |
| **descartados** | M5/M6 (impedem o encoder de streamar e são mais caros); M4 (desliga o seq-RLE e só ganha em `k = 2^w`); M3 (dominado pelo M2 e pode recusar) |

Isso corrige duas conclusões minhas: a do lab `2211` ("F1 default, porque o marcador colide")
e a do `2231` ("F5 default, 2 B fixos"). Nenhuma das duas estava errada nos números — as duas
pararam cedo demais na análise.

## Limites

- **Nada soldado**; `src/tcf` intocado. Os `.tcfp` são proposta.
- A varredura das 145 colunas usa as fixtures do repo; não é amostra do mundo.
- A garantia de `\<char>` vale para o corpo canônico **de hoje** — se `_escape_lit` mudar,
  muda. Vira teste se soldarmos.
- **gzip e CPU não medidos.** Métrica de prefixo não entrou aqui (está no lab `2211`).
- `k=1` continua fora: o core resolve com RLE.

## Rodar

```
python run.py
```
`opcoes.py` tem as sete montagens e os sete **leitores independentes**.
