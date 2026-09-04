# Post para o LinkedIn: TCF 0.8.2

> Texto pronto para publicar, com o link do GitHub no fim. Todo número aqui foi medido e
> está reproduzível no repositório; nada é estimativa.
>
> Versão longa primeiro, versão curta depois. Escolha uma.

---

## Versão longa

**Um formato tabular que você consegue ler, e consultar sem descomprimir.**

Passei os últimos meses num problema específico: quando um serviço manda uma tabela para
outro, o JSON é grande e o gzip resolve o tamanho mas fecha a porta. Para responder
qualquer pergunta sobre o conteúdo, é preciso descomprimir tudo antes.

O TCF é uma tentativa de ocupar o outro canto: continuar sendo **texto legível** e ainda
assim permitir que se pergunte ao arquivo sem expandi-lo.

Uma tabela de 6 linhas e 3 colunas:

```
#TCF.8M@17=cidade,@17=plano,!15N=valor
14
Sao Paulo
Rio
!!"!"!14
Premium
Basic
!"!!"!120
100
170
200
80
80
```

São 106 bytes, contra 170 do JSON compacto. Mas o tamanho não é o ponto principal: o
cabeçalho declara o nome, o modo de compressão e o tamanho de cada coluna, e é isso que
permite fatiar o corpo sem decodificar.

```python
from tcf import encode, view

v = view(encode(tabela))

v.count()                                    # 6, lido da estrutura: materializa 0%
v.where("cidade", "Sao Paulo").sum("valor")  # materializa 2 das 3 colunas
v.group_sum("cidade", "valor")               # GROUP BY sem SQL
```

O `count` não constrói um único valor: a contagem de linhas está declarada na estrutura.
Numa coluna de baixa cardinalidade, o filtro compara contra os valores distintos, e não
contra as N linhas.

**O que aprendi documentando isso é mais interessante que o formato.**

Ao escrever a referência, montei um quadro de "onde ganha e onde não ganha", e ele me
obrigou a medir em vez de afirmar. O resultado tem casos desconfortáveis, e eles estão na
documentação:

Filtrar antes e agregar depois **não** deixa a agregação mais barata. Eu esperava que
sim. Medindo, a coluna é materializada inteira antes de o filtro cortar as linhas, e o
número é idêntico com 1% ou 100% de seletividade. Está escrito lá, com o número, e
registrado como trabalho futuro.

Uma tabela de uma coluna só, com valores todos diferentes, é o caso em que consultar e
descomprimir custam quase o mesmo. Também está escrito.

Acho que documentação técnica melhora quando diz onde a ferramenta **não** ajuda. Um leitor
que descobre o limite sozinho, depois de adotar, fica com uma impressão pior do que aquele
que leu o limite antes de decidir.

**Detalhes práticos:** Python puro, sem dependências, MIT. Está em pré-1.0, o que significa
que o formato ainda pode mudar entre versões. Instalação: `pip install tcf-format`.

Se você trabalha com transporte de dados tabulares entre serviços, ou só gosta de formatos
de arquivo, o código e as medições estão abertos.

https://github.com/LeoPR/TCF

#Python #DataEngineering #OpenSource #Compressao

---

## Versão curta

**Um formato tabular legível, que responde consultas sem descomprimir.**

O gzip resolve o tamanho de um JSON, mas para perguntar qualquer coisa sobre o conteúdo é
preciso expandir tudo antes. O TCF tenta o outro canto: continuar texto legível, e deixar
que se pergunte ao arquivo direto.

```python
v = view(encode(tabela))
v.count()                                    # lido da estrutura: materializa 0%
v.where("cidade", "SP").sum("valor")         # toca 2 das 3 colunas
```

Uma tabela de 6 linhas e 3 colunas sai em 106 bytes, contra 170 do JSON compacto. Mas o
que interessa é o cabeçalho declarar nome, modo e tamanho de cada coluna, o que permite
fatiar o corpo sem decodificar.

O que mais aprendi foi documentando. Montei um quadro de "onde ganha e onde não ganha" e
ele me obrigou a medir em vez de afirmar: descobri que filtrar antes de agregar **não**
barateia a agregação, ao contrário do que eu esperava. Está na documentação, com o número
e o motivo.

Documentação técnica melhora quando diz onde a ferramenta não ajuda.

Python puro, sem dependências, MIT, pré-1.0. `pip install tcf-format`

https://github.com/LeoPR/TCF

#Python #DataEngineering #OpenSource

---

## Notas para você antes de publicar

**Os números conferem**, e são reproduzíveis: 106 B contra 170 B do JSON compacto na tabela
citada; `count()` materializando 0%; o filtro tocando 2 de 3 colunas. Rodei todos antes de
escrever.

**O que evitei de propósito:**

- comparar com Parquet ou Arrow. São binários colunares para outro caso de uso, e a
  comparação daria uma discussão sobre a régua em vez do formato;
- dizer "mais rápido" ou "mais eficiente" sem qualificar. Não há medição de latência
  publicável ainda, e o texto não promete nenhuma;
- superlativo. O gancho é o limite documentado, não a vantagem.

**Um risco que vale saber:** o parágrafo sobre "filtrar antes não barateia" é o mais
interessante do post e também o mais fácil de ler como fraqueza. Acho que ele funciona a
seu favor, porque quem trabalha com isso reconhece o valor de um autor que mede e publica o
resultado desfavorável. Mas a escolha é sua, e o texto continua de pé sem ele: é só cortar
esse parágrafo e o seguinte.

**A tag `#Compressao` sem cedilha** é proposital: acentos em hashtag costumam quebrar a
busca no LinkedIn.
