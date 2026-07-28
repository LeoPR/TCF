# Delimitação do domínio — o espaço completo (2026-07-27-2247)

Você discordou de eu ter tratado **colisão como veredito**. Procede: colisão é **custo condicional** — o escape resolve, e só se paga onde ocorre.

## Quanto o escape custaria, no dado real

Varri **145 colunas categóricas** (`2 ≤ k ≤ 64`) das fixtures do repo, olhando que char inicia cada valor de domínio:

```
chars que iniciam algum valor:   >  <  -  espaço  ,
```

`=`, `|`, `!`, `?`, `#`, `@`, `%` **nunca** iniciam. Um marcador `=` precisaria de escape em **zero** dessas 145 colunas — o custo condicional é, na prática, zero.

## As sete opções

| | como | marcação em | custo típico |
|---|---|---|---|
| **M1** | `\|` — classe que o core nunca emite | corpo | 2 B fixos |
| **M2** | `=` default; `\=` escapa a linha que colide | corpo | **1 B** + 1/colisão |
| **M3** | char eleito do complemento, declarado | ambos | 2 B fixos |
| **M4** | padding a `2^w`; fronteira sai de `w` | corpo | (2^w − k) B, sem seq-RLE |
| **M5** | `L<hex>` contagem de linhas | cabeçalho | 2-3 B |
| **M6** | `:<hex>` bytes — convenção do `.8M` | cabeçalho | 3-5 B |
| **M7** | domínio por último | nenhum | 0 B, **sem streaming** |

## Medição — mesmos dados, sete montagens

| coluna | n | k | M1 | M2 | M3 | M4 | M5 | M6 | M7 | melhor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:-:|
| `str-k2` | 200 | 2 | 57 | 56 | 57 | 55 | 57 | 57 | 55 | **M4** |
| `str-k3` | 200 | 3 | 99 | 98 | 99 | 98 | 99 | 100 | 97 | **M7** |
| `str-k4` | 200 | 4 | 109 | 108 | 109 | 107 | 109 | 110 | 107 | **M4** |
| `str-k5` | 200 | 5 | 150 | 149 | 150 | 151 | 150 | 151 | 148 | **M7** |
| `str-k7` | 200 | 7 | 168 | 167 | 168 | 167 | 168 | 169 | 166 | **M7** |
| `str-k4-null` | 200 | 5 | 146 | 145 | 146 | 147 | 146 | 147 | 144 | **M7** |
| `num-k4` | 200 | 4 | 90 | 89 | 90 | 98 | 90 | 90 | 88 | **M7** |
| `adult-sex` | 100 | 2 | 42 | 41 | 42 | 40 | 42 | 42 | 40 | **M4** |
| `adult-race` | 100 | 5 | 120 | 119 | 120 | 121 | 120 | 121 | 118 | **M7** |
| `adult-workclass` | 93 | 6 | 119 | 118 | 119 | 119 | 119 | 120 | 117 | **M7** |
| `adult-class` | 100 | 2 | 42 | 41 | 42 | 40 | 42 | 42 | 40 | **M4** |
| `cnpj-uf` | 2000 | 28 | 1765 | 1764 | 1765 | 1767 | 1766 | 1766 | 1763 | **M7** |
| `pm25-cbwd` | 100 | 4 | 59 | 58 | 59 | 57 | 59 | 59 | 57 | **M4** |
| **soma** | | | 2966 | 2953 | 2966 | 2967 | 2967 | 2974 | 2940 | |

## Os venenos — agora com o escape explorado

| coluna | M1 | M2 | M3 | M4 | M5 | M6 | M7 | escapes M2 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---:|
| `comeca-com-igual` | OK | OK | OK | OK | OK | OK | OK | 1 |
| `todos-comecam-igual` | OK | OK | OK | OK | OK | OK | OK | 3 |
| `contem-backslash` | OK | OK | OK | OK | OK | OK | OK | 0 |
| `e-o-marcador-m1` | OK | OK | OK | OK | OK | OK | OK | 0 |
| `so-digitos` | OK | OK | OK | OK | OK | OK | OK | 0 |
| `com-linha-vazia` | OK | OK | OK | OK | OK | OK | OK | 0 |
| `faixa-saturada` | OK | OK | — | OK | OK | OK | OK | 0 |

`todos-comecam-igual` é o pior caso do M2: **3 escapes** (um por valor do domínio). Mesmo assim o M2 continua correto — o custo é condicional, não veredito. `faixa-saturada` é o pior caso do M3: um valor usa a FAIXA inteira e não sobra char pra eleger, então ele **recusa** (`—`).

## Os eixos que o tamanho não mostra

| | leitor streama? | **escritor** streama? | pode recusar? | reusa o quê |
|---|:-:|:-:|:-:|---|
| **M1** | sim | **sim** | não | a gramática de escape do core |
| **M2** | sim | **sim** | não | escape, e a técnica de default+desambiguação |
| **M3** | sim | **não** (elege antes) | **sim** (FAIXA cheia) | a eleição da polaridade (ADR-0035) |
| **M4** | sim | **sim** | **sim** (seq-RLE colapsa) | nada; e **desliga** o seq-RLE |
| **M5** | sim | **não** (conta antes) | não | — |
| **M6** | sim | **não** (mede antes) | não | a convenção de tamanho hex do `.8M` |
| **M7** | **não** | sim | não | o tamanho deduzível do b64 |

**Onde jogar o byte importa mais que quantos.** Marcação no corpo (M1/M2) não precisa ser conhecida antes de escrever — o encoder emite cabeçalho → domínio → marcador → bits, sem voltar atrás. Marcação no cabeçalho (M5/M6) obriga a bufferizar o domínio inteiro ou reescrever o campo.

## Sobre reusar o multi-col

O `.8M` já declara tamanho por coluna em hex (`multi/core.py:_serialize`), e o **M6 é essa mesma convenção**. Mas ele é o mais caro dos sete, e o single-col não pode depender do multi para se ler — seria reimplementação, não reuso. O reuso que **de fato** se paga é outro: o M1 usa a gramática de escape do core, e o M3 usa a eleição de char da polaridade. Nenhum dos dois é código novo.

## Veredito

- **M2 é o mais barato** (2953 B somados) e o escape que você defendeu é o que o torna seguro. Em 145 colunas reais o custo condicional foi **zero**.
- **M1 custa 1 B a mais** (2966 B) e é imune **por construção** — não depende de o dado ser bem-comportado.
- **M7 é o mais barato de todos** (2940 B) mas **não streama** — é o modo de lote, como já tínhamos concluído.
- **M4 é elegante** (0 B de declaração) mas **desliga o seq-RLE do domínio** e desperdiça `2^w − k` linhas; empata ou perde.
- **M5/M6 são os mais caros** e ainda impedem o encoder de streamar.

## M1 e M2 são a MESMA família — e isso dissolve o dilema

O escape do M2 é `\=`. Ele funciona pelo **mesmo motivo** que o M1: `\` seguido de char fora de `* 0-9 \ ^ ~` é impossível de o core produzir. Não são duas posturas, são **dois pontos de pagamento da mesma garantia**:

```
M1   paga a garantia ADIANTADO      2 B sempre
M2   paga a garantia SOB DEMANDA     1 B + 1 por colisão
```

Break-even exato em **1 colisão**: com `j = 0` o M2 ganha 1 B; `j = 1` empata; `j ≥ 2` o M1 ganha. E `j` é **contável enquanto o domínio é construído** — o encoder já o percorre. Então não é escolha de postura, é `min(1 + j, 2)`: um FLOOR computável, do mesmo feitio do da polaridade.

O byte que sobra pode declarar qual foi usado, ou a própria grafia distingue (`\|` × `=`) sem custo. Nos dados reais, `j = 0` em 145 de 145 colunas — o M2 seria escolhido sempre, mas **sem depender disso ser verdade**.

RT pelos leitores independentes: **todos OK**

