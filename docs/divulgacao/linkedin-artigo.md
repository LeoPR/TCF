# Comprimir uma tabela e ainda conseguir perguntar coisas a ela

*Artigo técnico. Cada número aqui tem um comando que o reproduz no repositório, e nenhum foi
escrito sem o roundtrip fechar antes. Onde a biblioteca não ajuda, o texto diz que não ajuda.*

Fonte: [`2026-09-04-fonte-0.8.4.md`](2026-09-04-fonte-0.8.4.md). Reproduz com
`python scripts/verifica_divulgacao.py`.

---

Quando dois sistemas trocam uma tabela, o formato mais usado repete o nome de cada campo em
toda linha. É uma escolha que faz sentido, porque cada registro fica autônomo e legível
sozinho, e é também a razão de o payload crescer com a redundância em vez de crescer com a
informação.

Num cadastro de quatro pessoas e cinco campos, o JSON compacto dá 451 bytes e o CSV dá 277. A
diferença de 174 bytes é quase inteiramente nome de campo repetido.

O TCF ocupa uma faixa entre os dois e o compressor binário. Ele fatora o que se repete,
referencia o resto, e o resultado continua sendo texto ASCII que você abre e lê. O mesmo
cadastro dá 242 bytes.

Este texto trata de três coisas: por que a comparação com gzip costuma ser mal colocada, o que
o formato garante sobre tamanho antes de você chamar, e onde ele não compensa.

## A comparação com gzip está no lugar errado, e isso tem consequência prática

A objeção que aparece primeiro é "e por que não só ligar o gzip?". Ela merece medição em vez
de defesa, e a medição tem duas partes.

**Em transmissão, o compressor é invisível.** O `Content-Encoding` é negociado pelo transporte,
não pelo seu código. Quando o seu handler lê o corpo, ele já foi inflado, e você raramente
chega a ver que houve compressão. Não existe escolher TCF contra brotli nessa camada, porque
os dois nem aparecem no mesmo ponto do fluxo. A pergunta que sobra é outra: **o que o meu
processo segura e faz parse depois que o canal terminou o trabalho invisível dele.**

Isso não torna o canal grátis. Ele gasta memória e CPU para inflar, a cada requisição, e a
conta só é paga uma camada abaixo. É parte do total, não algo fora dele.

**Em disco, o compressor vira decisão visível, e aí ele cobra opacidade.** O blob comprimido é
a coisa que você tem, e para ler qualquer parte dele você infla o todo. Não existe ler uma
coluna, contar um valor, ou filtrar uma linha antes de o payload inteiro voltar a existir.

## O que muda quando o comprimido continua legível

```python
from tcf import encode, view

wire = encode(tabela)           # 242 B
v = view(wire)                  # nada foi decodificado ainda

v.columns                       # ['nome', 'email', 'cidade', 'plano', 'cpf']
v.nrows                         # 4
v.distinct('cidade')            # ['Rio de Janeiro', 'Sao Paulo']
v.group_count('plano')          # {'Premium': 3, 'Basic': 1}
v.where('plano', 'Premium')     # 3 linhas, sem materializar as outras
v.column_bytes('cpf')           # 59 B de 193 B
```

Nenhuma dessas chamadas decodifica a tabela inteira. A última é a que costuma surpreender quem
está dimensionando: dá para perguntar quanto cada coluna está custando, dentro do próprio
artefato, sem desmontar nada.

E o wire é o dado. Não é um dump hexadecimal, é isto:

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
111.111.111-11
222.222.222-22
333.333.333-33
444.444.444-44
```

Os nomes das colunas aparecem uma vez, no cabeçalho, e não uma vez por linha. No corpo,
`*3|Sao Paulo` é RLE: o valor se repete em três linhas adjacentes e é escrito uma vez. E `^1`
é referência de linha: em vez de gravar `Premium` pela terceira vez, aponta para a ocorrência
anterior. A coluna de e-mail usa composição por afixos, que é o mecanismo do tokenizador e
está descrito na [spec do formato](../algorithms/TCF-format.pt-BR.md).

Nada disso é decoração. É o mesmo dado, e ele volta idêntico.

## O contrato de tamanho, que é avaliável antes da chamada

A biblioteca faz uma afirmação verificável, e não uma promessa de marketing.

> Para cada coluna, o codificador gera as candidatas e grava a **menor**:
> `min(tcf, cru, dicionário, split)`. O resultado é **nunca pior por construção**.

O que faz disso um contrato é a segunda metade. Não é "costuma ser menor", é uma propriedade
da estrutura do codificador: ele não tem como emitir a candidata pior, porque escolhe pelo
mínimo. O pior caso é empatar com a representação crua, e o custo do empate é o cabeçalho.

Na prática isso muda quanto custa experimentar. Não é preciso rodar um piloto para descobrir
se o formato inchou o seu dado, porque ele não pode inchar.

O `sort_by` mostra a regra funcionando quando algo novo entra. Ordenar a tabela por uma chave
ajuda quando as outras colunas são função dela, e atrapalha quando são independentes, porque a
permutação agrupa os iguais da chave e desarruma todo o resto. Medido numa tabela de 60 linhas:
**−43,0%** no primeiro caso e **+52,1%** no segundo.

A solução não foi escolher um lado. O `sort_by` deixou de ordenar e passou a **propor** uma
ordenação, e o FLOOR decide se ela entra. Nos sete casos medidos, isso evita 734 bytes de
perda, e o usuário não precisa saber em qual dos dois regimes o dado dele está.

## Como o contrato é verificado

Três mecanismos, e nenhum deles é a suíte passando.

**A regra §RT**, que é de processo e não de código. Está escrita como invariante no guia do
projeto: `decode(encode(x)) == x` vem antes de qualquer número, e sem roundtrip o número não
entra em prosa, nem em tabela, nem em commit. Todo tamanho deste artigo passou por ela, e o
script que os reproduz sai com erro se um roundtrip falhar.

**Os gates byte-canônicos**, que fixam a saída esperada de conjuntos conhecidos e falham
vermelho se um único byte mudar. É o que impede uma otimização de alterar o wire sem ninguém
perceber.

**O baseline de performance pinado**, com a matriz de casos travada por hash. Ele se recusa a
comparar duas rodadas quando a matriz ou o plano diferem, em vez de casar o que não casa. Isso
custou caro uma vez, e de um jeito instrutivo: um hook do próprio repositório acrescentou uma
quebra de linha no arquivo de casos, o hash mudou, e os três planos ficaram dez dias
inexecutáveis sem ninguém notar, porque ninguém rodou. Um instrumento que ninguém roda não
avisa que quebrou.

## Escrever é caro, ler é barato, e isso decide onde usar

O trabalho está concentrado no `encode`. O `decode` é leitura quase sem laço, e a `view` é
menos ainda, porque acessa por aritmética em vez de percorrer.

Numa tabela de 3000 por 15 com baixa cardinalidade, o encode leva 934,6 ms e o decode 83,7 ms,
uma razão de 11,2×. A razão **não é constante**: medida sobre a 0.8.4, ela varia de 3,6× a
1.060× conforme a forma do dado, então o honesto é dizer que é uma faixa de duas ordens de
grandeza, e não um número.

Isso importa mais do que parece, porque a decisão não é cliente contra servidor, é a topologia
do dado. Se o dado é **cacheável**, você paga o encode uma vez e distribui muitas, e a
assimetria trabalha a seu favor. Se ele é **personalizado por requisição**, você paga o encode
toda vez, e a conta muda de sinal.

## Os números em conjunto maior

O cadastro de quatro registros é bom para explicar e ruim para dimensionar. Em conjuntos
reais:

Nos 8 datasets do EXP-019, o conjunto caiu de 390.863 para 290.949 bytes, ou **−25,6%**, com a
faixa indo de −4,1% a −46,6% conforme o dado. Em multi-coluna real, 9 tabelas do Adult e do
TPC-H somando 136 mil linhas, são **−33,02% ponderado** contra o CSV cru.

E o formato lê estrutura aninhada desde a 0.8. Ele consome o **dataset** que a sua linguagem
monta a partir do JSON, não o texto do JSON, então objeto aninhado, lista, `null` e
`true`/`false` tipados voltam byte a byte. Dois registros com uma lista dentro: 184 bytes em
JSON compacto contra 144 no TCF.

## Onde isto não se aplica hoje

**Sob `gzip`, o TCF não ganha.** No cadastro pequeno os três formatos empatam dentro de 1 byte:
206, 205 e 206. Onde ele ganha é cru, sob `br` e sob `zstd`.

**No tamanho minúsculo, o CSV passa.** 162 bytes contra 185 sob brotli. Vale a ressalva de que
CSV raramente é payload de API e de que ele não tem `view`, mas o número é o número.

**A otimização de algoritmo ainda não aconteceu.** O ciclo atual fechou funcionalidade, com as
quatro famílias de wire soldadas e publicadas. O ciclo seguinte é o de desempenho, então os
tempos acima são de código não otimizado. Eles estão pinados justamente para haver contra o
que comparar depois.

**Comparação com formato de armazenamento não foi feita.** Parquet, ORC e afins ocupam um lugar
diferente, e medir contra eles exige um desenho próprio que ainda não existe. Dizer qualquer
coisa sobre isso agora seria chute.

**É pré-1.0.** O dígito do meio ainda pode mexer no que sai, e cada mudança entra no changelog
com a medição atrás.

Vale uma última: cada número desta página é medido, o que não é o mesmo que provado. É razoável
supor que exista um caso desfavorável que eu ainda não medi.

## Prático

Python 3.10 ou mais novo, zero dependências, MIT, pré-1.0. A superfície pública são 18 nomes, e
a suíte tem 2005 testes passando.

```
pip install tcf-format
```

O código, as medições e a documentação do que não funciona estão abertos.

https://github.com/LeoPR/TCF

#Python #Compressao #DataEngineering #OpenSource #FormatosDeDados
