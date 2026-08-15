# Resultado — `agg="soma"` tem três implementações, e elas diferem em streaming

3 formas × 3 casos, **0 falhas**. Orienta, não fecha.

## A tabela

`retail.UnitPrice`, 2000 valores, `d=1`, baseline 3685 B:

| forma | bytes | soma exata? | erro máx/linha | **lidos antes do 1º** | prefixo decoder |
|---|---:|---|---:|---:|---:|
| **maior resto** (Hamilton) | 3028 | **sim** | 5,0e−2 (½ passo) | **2000** | 19 B |
| **difusão de erro** (1 passe) | 3090 | **sim** | 9,0e−2 (~1 passo) | **1** | 19 B |
| **âncora** (soma à parte) | **2955** | não *(nas linhas)* | 5,0e−2 | 1 | 19 B |

O mesmo padrão se repete no rateio sintético e em `d=0`.

## A resposta à sua pergunta

**Sim, depende de como você pede — e a diferença é grande.**

O **maior resto precisa da coluna inteira** antes de decidir o primeiro valor: ele soma tudo,
tira os pisos, ordena por resíduo e distribui. Com 2000 valores, são **2000 leituras antes de
emitir um**. É o oposto de streaming.

**A difusão de erro entrega o mesmo contrato sendo streamável.** Ela carrega o resíduo para o
próximo valor (`carry = x − round(x)`), então lê **um** valor, emite **um**, e mantém **um
float** de estado. E a soma sai **exata na escala de `d`** nos três casos medidos — o mesmo que
o maior resto promete.

**O preço é 62 bytes (2,0%) e o dobro do erro por linha.** O maior resto errou até meio passo;
a difusão, até um passo inteiro — porque o carry pode empurrar um valor a mais. É um trade
declarável, não um defeito.

## Duas correções a coisas já escritas

1. **A ressalva do PoC de junho estava invertida na prática.** Registrei antes que "o maior
   resto erra até 1 passo por linha, o ingênuo até 0,5". Medido: o maior resto erra **meio
   passo** neste dado. Motivo — ele ordena por resíduo decrescente e incrementa os `falta`
   primeiros; quando `falta` ≈ (nº de valores com resíduo > ½), ele se comporta quase como
   `half-up`, e o pior caso teórico de 1 passo não se realiza. **Quem erra 1 passo aqui é a
   difusão.**
2. **Streaming não é uma coisa só.** O prefixo do **decoder** ficou em 19 B nas três formas —
   idêntico. A diferença é toda do lado do **encoder**. Um mecanismo pode ser ótimo numa noção
   e péssimo na outra, e misturá-las esconde exatamente o que você perguntou.

## A âncora é um contrato diferente, não uma terceira opção do mesmo

Ela é a mais barata (**2955 B**, abaixo das duas) porque arredonda cada valor por si — os
valores ficam mais regulares e o núcleo comprime melhor. Mas **as linhas não somam ao total**:
o total exato viaja à parte.

Isso não é pior nem melhor — é **outro contrato**, e o consumidor precisa saber qual recebeu.
Se ele soma as linhas, dá diferente da âncora. É o caso mais forte para o aviso obrigatório.

E há uma sutileza de streaming nela: **âncora em cabeçalho exige a coluna inteira** (é preciso
somar antes de escrever o cabeçalho); **âncora em trailer é streamável**, mas aí o decoder só
pode verificar no fim.

## Onde isso encaixa no parâmetro

O `Tolerancia(agg="soma")` do lab `…-2110` usa maior resto. Este lab mostra que `agg` precisa
de um **segundo eixo**, não de um valor só:

```python
Tolerancia(agg="soma", agg_forma="exata")      # maior resto  — não streamável
Tolerancia(agg="soma", agg_forma="streaming")  # difusão      — 1 passe, +2% bytes
Tolerancia(agg="soma", agg_forma="ancora")     # à parte      — mais barato, contrato distinto
```

Porque "preservar a soma" **não determina** como, e o como decide se cabe num pipe.

## O que isto orienta

1. **`agg="soma"` é compatível com streaming** — mas só na forma de difusão, e pagando ~2% em
   bytes e o dobro do erro por linha.
2. **A âncora é o mais barato e o mais perigoso**: as linhas não somam ao que o cabeçalho diz.
   Sem aviso, o consumidor lê errado sem nenhum sinal.
3. O parâmetro precisa declarar **a forma**, não só o agregado.
