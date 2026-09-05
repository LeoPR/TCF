**Português** · [English](artigo.en.md)

# TCF: como reduzir dados repetitivos sem esconder sua estrutura

> **Nota de publicação, fora do corpo do artigo.** Texto para a área de artigos do LinkedIn;
> a chamada curta está em [post.pt-BR.md](post.pt-BR.md).
> Fonte técnica: [documento de lançamento](../2026-09-04-lancamento.md).
> Use a imagem `0-capa` de [figuras/pt-BR/](figuras/pt-BR/) na capa e as demais nos pontos
> indicados abaixo. Os exemplos Python são executados pela suíte de documentação.

---

Imagine um cadastro de clientes: nomes, e-mails, cidades e planos contratados. Muitas pessoas
moram na mesma cidade, assinam o mesmo plano ou usam e-mails com o mesmo domínio. Para quem
olha a tabela, essas repetições são fáceis de perceber. A forma de representar os dados,
porém, nem sempre aproveita o que eles têm em comum.

Quando esse cadastro precisa sair de uma aplicação, seja para um arquivo ou para outro
sistema, é necessário escolher uma representação. Duas opções comuns são JSON e CSV.
No JSON organizado como uma lista de objetos, cada registro traz os nomes dos campos,
como `cidade` e `plano`. No CSV com cabeçalho, esses nomes aparecem uma vez, mas os valores
continuam escritos em cada linha: cem clientes da mesma cidade significam cem ocorrências
do nome dela.

Essa repetição sugere uma pergunta: **é possível ocupar menos espaço e ainda deixar parte
da estrutura dos dados visível no resultado?**

O TCF, sigla de *Tabular Compact Format*, explora essa possibilidade. Ele substitui
repetições por referências e agrupamentos, mas mantém uma representação textual que pode
ser aberta em um editor. O resultado exige conhecer alguns marcadores e não é tão imediato
de ler quanto a tabela original. Ainda assim, permite reconhecer valores e padrões sem
reconstruir todos os registros.

A redução tem uma condição: não perder informação. Para as entradas suportadas, codificar
e depois decodificar deve devolver os mesmos dados. É esse compromisso que permite avaliar
o tamanho sem confundir compressão com descarte de conteúdo.

## O mesmo dado, em dois formatos comuns

Para ver a ideia em um caso concreto, considere quatro pessoas com nome, e-mail, cidade,
plano e CPF. Neste exemplo, três moram em São Paulo e todos os e-mails terminam em
`@acme.com.br`.

Em JSON, cada registro repete o nome de todos os campos:

```json
[
  {
    "nome": "Ana Souza",
    "email": "ana@acme.com.br",
    "cidade": "Sao Paulo",
    "plano": "Premium",
    "cpf": "111.111.111-11"
  },
  {
    "nome": "Bruno Lima",
    "email": "bruno@acme.com.br",
    ...
```

Em CSV, os nomes aparecem uma vez, no cabeçalho, e cada linha traz só os valores:

```csv
nome,email,cidade,plano,cpf
Ana Souza,ana@acme.com.br,Sao Paulo,Premium,111.111.111-11
Bruno Lima,bruno@acme.com.br,Sao Paulo,Premium,222.222.222-22
Carla Nunes,carla@acme.com.br,Sao Paulo,Basic,333.333.333-33
Diego Rocha,diego@acme.com.br,Rio de Janeiro,Premium,444.444.444-44
```

O cadastro inteiro ocupa **451 bytes em JSON compacto e 277 em CSV**. O JSON acima está
indentado para leitura; a medida é da forma compacta, sem espaços supérfluos.

O CSV já resolveu a repetição dos nomes de campo. Mas ele ainda escreve `Sao Paulo` três
vezes, `@acme.com.br` quatro vezes e `Premium` três vezes.

## A mesma tabela, depois do TCF

![Representação TCF anotada e comparação com o filtro opcional de CPF](figuras/pt-BR/2-wire.svg)

São **242 bytes**, e o ponto não é só o número: continua sendo texto que você abre e lê. Não
há dump binário, não há ferramenta necessária para inspecionar. Os marcadores que aparecem
ali são o assunto da próxima seção.

![Barras proporcionais comparando JSON, JSONL, CSV e TCF em bytes reais](figuras/pt-BR/1-formatos.svg)

São medidas deste exemplo, não uma proporção garantida para qualquer tabela. A figura inclui
também JSONL, uma representação com um objeto JSON por linha.

## O que fica no lugar da repetição

Na coluna de cidades, as três ocorrências consecutivas de `Sao Paulo` viram uma linha só:

```text
*3|Sao Paulo
```

O marcador significa "repita este valor três vezes". A informação continua ali; o que muda
é a maneira de escrevê-la. Na coluna de planos acontece o mesmo com `Premium`, e a quarta
ocorrência é escrita como `^1`, que significa "igual à primeira linha desta coluna".

Nos e-mails, a economia vem de outro padrão: o trecho `@acme.com.br` é escrito uma vez e
referenciado pelos demais valores.

O TCF combina duas etapas para encontrar essas oportunidades. A primeira, chamada OBAT,
procura começos e finais de texto compartilhados, como o domínio dos e-mails. A segunda,
HCC, reúne fragmentos recorrentes em referências reutilizáveis e agrupa repetições.
Sequências numéricas regulares também podem ser descritas pelo valor inicial, pelo passo
e pela quantidade de itens, em vez de listar cada um deles.

Nem toda coluna, porém, oferece economia. Por isso, o codificador compara as representações
disponíveis e escolhe a menor para cada coluna, incluindo a opção de guardar os valores
sem essa compressão. **Isso não garante um arquivo menor que qualquer JSON ou CSV**:
o cabeçalho e os demais metadados também ocupam espaço.

Há ainda filtros opcionais para estruturas conhecidas, como CPF, CNPJ e IPv4. No CPF,
por exemplo, a pontuação fixa e os dígitos verificadores podem ser reconstruídos quando
o valor atende às regras do filtro. Valores que não se encaixam são preservados literalmente.
Isso não verifica se um CPF existe ou pertence a alguém; apenas aproveita a forma do texto.
É a segunda metade da figura acima: com esse filtro, o tamanho total passa de 242 para
210 bytes, mantendo o round-trip.

## E em Python, como isso se usa

A tabela entra como um dicionário de colunas. A função `encode` produz o texto TCF, e
`decode` reconstrói os dados:

```python
from tcf import decode, encode

tabela = {
    "nome":   ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha"],
    "email":  ["ana@acme.com.br", "bruno@acme.com.br",
               "carla@acme.com.br", "diego@acme.com.br"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plano":  ["Premium", "Premium", "Basic", "Premium"],
    "cpf":    ["111.111.111-11", "222.222.222-22",
               "333.333.333-33", "444.444.444-44"],
}

wire = encode(tabela)

assert decode(wire) == tabela
```

A última linha verifica a igualdade entre a entrada e a saída reconstruída. Essa verificação
é chamada de *round-trip*: o dado faz o caminho de ida e volta, sem alteração.

## Por que manter a estrutura visível importa

Até aqui, o benefício foi ocupar menos espaço. Mas um marcador como `*3|Sao Paulo` também
informa quantos registros aquele grupo representa. Para obter essa contagem, não é
necessário reconstruir três cópias do texto. O mesmo princípio permite aproveitar certas
sequências em operações numéricas.

Essa propriedade é usada pela função `view()`, que permite consultar a representação TCF
sem reconstruir a tabela inteira de saída. Dependendo da consulta, a resposta vem dos
metadados ou dos marcadores; quando isso não basta, os dados necessários são decodificados.

Considere uma tabela de clientes e valores contratados. Podemos contar registros, somar
valores ou filtrar por cidade:

```python
from tcf import encode, view

tabela = {
    "cliente": ["Ana", "Bruno", "Carla", "Diego", "Eva", "Ana"],
    "cidade": ["SP", "SP", "SP", "RJ", "SP", "RJ"],
    "plano": ["Premium", "Premium", "Basic",
              "Premium", "Basic", "Premium"],
    "valor": [120, 100, 170, 200, 80, 80],
}

blob = encode(tabela)
v = view(blob)

assert v.count() == 6
assert v.sum("valor") == 750.0
assert v.group_count("plano") == {"Premium": 4, "Basic": 2}
assert v.where("cidade", "SP").sum("valor") == 470.0
```

Na última consulta, só as colunas `cidade` e `valor` são necessárias: uma identifica os
registros selecionados, a outra fornece os valores para a soma. Não é preciso decodificar
`cliente` nem `plano` para responder a essa pergunta.

![As colunas que a consulta materializa, e as que nunca são tocadas](figuras/pt-BR/3-view.svg)

## E os compressores tradicionais?

Reduzir repetições também é o trabalho de ferramentas como gzip, brotli e zstd. A distinção
é que elas comprimem os bytes de uma representação, enquanto JSON, CSV e TCF definem como
os dados são representados. Portanto, as escolhas podem ser combinadas: um conteúdo em TCF
pode receber gzip, assim como um conteúdo em JSON.

Depois dessa compressão adicional, o conteúdo precisa ser descomprimido para ser
interpretado. Isso pode acontecer em fluxo, sem guardar tudo descomprimido na memória.
O que o gzip não oferece por si só é uma maneira de identificar colunas ou contar registros
a partir da estrutura da tabela.

O interesse do TCF está no que permanece disponível **sem essa camada adicional**, ou depois
que ela é removida: uma representação compacta com valores, referências e agrupamentos que
a aplicação pode inspecionar e consultar.

Essa diferença de propósito não dispensa medir tamanho. No cadastro de quatro pessoas,
com os compressores externos em nível máximo, o resultado é:

![Tabela de compressão de canal: JSON, JSONL, CSV e TCF](figuras/pt-BR/4-tabela.svg)

Sob gzip, JSON, JSONL e TCF ficam praticamente empatados. Com brotli ou zstd, o TCF é menor
que JSON e JSONL, mas o CSV comprimido é o menor dos quatro neste exemplo. Não há, portanto,
base para afirmar que o TCF substitui os compressores tradicionais ou sempre ocupa menos espaço.

## O que as medições permitem concluir

Quatro registros ajudam a explicar o mecanismo, mas não mostram como ele se comporta em
outros dados. O [EXP-019](../../../experiments/lab/clean/EXP-019-consistencia-0-8-4/) avaliou
oito amostras de 800 linhas, incluindo dados reais e gerados. O experimento comparou duas
representações do próprio TCF: uma hierárquica e outra voltada a registros tabulares.
O total passou de 390.863 para 290.949 bytes, uma redução de **25,6%**, com round-trips
verificados. Esse percentual não mede vantagem sobre CSV, JSON ou gzip.

Mesmo nessa comparação interna, a redução variou de 4,1% a 46,6% por amostra. A variação
reforça que a economia depende dos padrões presentes na entrada. O experimento verifica
consistência nessas amostras, não desempenho em grande escala, e seus ganhos não devem
ser tratados como previsão para qualquer aplicação.

O tamanho também é apenas parte da decisão. A busca por padrões concentra trabalho na
codificação; ler tende a custar menos que produzir a representação. Dados preparados uma
vez e reutilizados em muitas leituras são, por isso, um caso de uso a investigar. Se cada
requisição exige codificar dados diferentes, esse custo precisa entrar na avaliação.

O projeto está na versão 0.8.4, ainda anterior à 1.0, sem garantia rígida de compatibilidade
entre versões menores. As medições apresentadas aqui tampouco estabelecem uma comparação
com Parquet ou outros formatos de armazenamento. Para adoção, é necessário medir tamanho,
tempo de escrita e leitura e consumo de memória com os dados e as consultas da aplicação.

## Uma forma de experimentar

O TCF parte de uma observação simples: repetições podem carregar informação útil mesmo
quando são escritas de forma compacta. Seu interesse não se resume a reduzir um arquivo,
mas inclui preservar uma estrutura que permita entender e consultar parte dos dados
sem reconstruir o conjunto inteiro.

A biblioteca é aberta, tem licença MIT, requer Python 3.10 ou mais novo e não possui
dependências de execução. Para experimentar o exemplo deste artigo:

```sh
pip install tcf-format
```

O repositório reúne o código, a documentação e as medições para quem quiser avaliar o
formato no seu próprio contexto:

https://github.com/LeoPR/TCF

#Python #Compressao #DataEngineering #OpenSource #FormatosDeDados
