---
title: "Os defaults: o que cada caso de borda responde, e de onde o default veio"
type: explanation
parent: tres-blocos
subsystem: presenca-nulo-ausencia
---

# Os defaults, e de onde cada um vem

> **Nada aqui está implementado.** Esta nota registra a proposta de comportamento, com a
> origem de cada default, para que a discussão não precise ser refeita. O critério é: o caso
> comum manda; a borda ganha um default herdado de quem já resolveu, ou o comportamento
> matemático quando existe; ambiguidade equilibrada ganha flag; o obscuro ganha aviso na
> telemetria em vez de bloqueio.

## A regra que gera todas as respostas

Uma só, e as outras saem dela:

```
todo critério fornecido INTERSECTA
```

`block=` restringe o conjunto de linhas, `value=` e `pred=` filtram dentro dele, e o
encadeamento de `where` já é AND. Nada tem precedência sobre nada, e por isso não existe o
caso "quem vence": a resposta é sempre a interseção. A combinação contraditória, como pedir
um valor não nulo dentro do bloco do nulo, é decidível só pelos argumentos e responde vazio.

## A tabela

| caso | default | origem |
|---|---|---|
| `block=A` onde `A` é vazio | conjunto vazio, em silêncio | PostgreSQL prova o vazio em coluna `NOT NULL` e chega a eliminar o scan, sem `NOTICE`; Mongo devolve result set vazio |
| `block=~A` (existe) no mesmo blob | todas as linhas, em silêncio | complemento do vazio é o universo |
| `block=V` numa coluna 100% nula | vazio, em silêncio | simétrico, e alcançável **hoje**, sem ragged nenhum |
| `block=` omitido | equivale a `V \| N \| A`, o total | o default do parâmetro novo tem que ser o comportamento velho, exato |
| `block=` com `value=`/`pred=` | interseção | pandas, polars e SQL compõem máscara com predicado por AND, e ninguém levanta erro |
| ordem e repetição (`N \| V`, `A \| A`) | irrelevantes, canonizadas | união é comutativa e idempotente |
| grafia ilegível (`"X"`, `"V \|"`, `"v"`) | `ValueError` nomeando as três letras e os dois operadores | bloco **vazio** responde vazio; bloco **ilegível** levanta. É a única fronteira onde o fail-loud ganha |
| o universo do `~` | sempre `[n]` | complementar dentro de `dom(c)` fecharia `A` fora do universo, e as oito uniões virariam quatro |
| `""` (string vazia) | pertence a `V` | a chave existe e o valor não é nulo. O bloco é definido pela máscara, nunca por vacuidade semântica |

## O que o `A` vazio significa, e por que ele entra na API mesmo assim

Hoje a `view` recusa ragged no header, então `A` é vazio em todo blob que ela abre. Isso não
é motivo para deixar o bloco de fora: é o **caso total**, em que a resposta degenerada é a
resposta certa.

O precedente é o Arrow, e ele é ponto a ponto. A especificação permite **omitir** o buffer
de validade quando não há nulo, e mesmo assim `is_valid(i)` continua respondendo verdadeiro
para todo `i`: *"Arrays having a 0 null count may choose to not allocate the validity
bitmap"*, e *"Consumers of Arrow arrays should be ready to handle those two possibilities"*.
O que o Arrow deixa cair é o **buffer**, nunca a **pergunta**.

A consequência prática é o motivo de aceitar `block=A` agora: o dia em que a `view` passar a
abrir ragged não pode ser um dia de mudança de API. O mesmo código passa a devolver linhas,
sem trocar de grafia.

E há um efeito que vale sozinho. Hoje `where(k, None)` responde `N`, mas ninguém escreveu em
lugar nenhum se ele responderia `N ∪ A` quando a ausência existir. Adotar a grafia dos blocos
**pina isso antes de a ambiguidade existir**: `where(k, None)` continua sendo `N`, e quem
quiser a união pede `block=~V`.

## A precondição que a verificação encontrou

A composição por interseção **não é implementável sozinha**, e isso foi medido, não
argumentado. A assinatura de hoje é `where(col, value=None, *, pred=None)`, com `None` vivo
como default. Com a regra de interseção aplicada sobre ela, `where(k, block=V)` significaria
`N ∩ V`, que é vazio em toda coluna.

A correção é uma sentinela privada no slot do valor, distinguindo "não passei valor" de
"passei `None`", em `where` e em `Filtered.where`. Medido na suíte: sem a sentinela, 14
testes pinados caem; com ela, 273 passam, zero falham.

Registrado como precondição para que ninguém tente a composição sem ela.

## As duas cardinalidades de `V`, que não são contradição

Numa coluna `['1', '', None, '3']`, uma seleção do que não é nulo tem `count()` igual a 3,
e o `avg()` divide por 2. Isso não invalida o bloco, e a frase que resolve é:

> `V` conta **linhas** (a chave existe e o valor não é nulo). Um agregado numérico opera
> sobre o multiconjunto dos valores que **são números**, e a string vazia é uma linha de `V`
> que não é um número: por isso `count()` diz 3 onde `avg()` divide por 2, sem contradição.

São dois conjuntos, e os dois estão certos: **cardinalidade do bloco** contra **domínio da
agregação**. É a definição ANSI de função de agregação, que opera sobre valores e não sobre
posições. O que muda é a justificativa escrita na docstring do agregador: o `""` não sai da
conta por ser nulo, o que contradiria `V`, e sim por não ser coercível a número.

## A única flag, e o que ela não é

Só um caso ficou com ambiguidade equilibrada: `value=` e `pred=` na mesma chamada, que hoje
resolve calado, com o `pred` vencendo e o `value` ignorado.

As duas leituras são defensáveis. Ou são dois **critérios** e a matemática manda intersectar,
ou são duas **grafias do mesmo slot** e portanto excludentes, que é o que o pandas faz ao
recusar mais de um argumento em `DataFrame.filter(items=, like=, regex=)`.

A saída não é knob novo: é o `.strict()` que a `view` já tem, generalizando o que ele
significa de "o valor do filtro tem de vir no tipo da coluna" para "o que o modo soft resolve
por convenção, o strict recusa". No soft, compõe por AND e avisa na telemetria nomeando os
dois critérios. No strict, levanta. **O que não sobrevive em modo nenhum é o silêncio de
hoje.**

## O que ainda não se pode afirmar

A regra pinada do repo é que *"a flag entra com um caminho otimizado atrás dela, não como
açúcar sobre o mesmo trabalho"*. O caminho existe no papel: no `.8H`, o nulo mora numa
coluna separada (a emask, declarada no header), então `block=N` pode ler a máscara e ignorar
a coluna de dados. Em várias rotas o header ou o domínio **provam** zero nulos sem tocar o
payload.

Mas o ganho **não está medido**, e há dois motivos concretos para não afirmá-lo:

1. no único wire gerado na verificação, a emask tinha 23 B contra 8 B de corpo de dados,
   porque o corpo comprimiu e a máscara não. A proporção depende da fração de nulos e do
   padrão deles, e sem corpus não dá para afirmar nem o **sinal** do ganho;
2. o corpus commitado do projeto não exercita o caso: 268 colunas, zero nulos.

Além disso, a contabilidade do `report()` hoje não enxerga a emask, que fica fora de
`_body`, então uma medição feita antes de corrigir isso mediria errado.

Conclusão honesta: a **semântica** está fechada e é o que esta nota registra. O **portão de
desempenho** depende de uma medição que ainda não foi feita, e ela precisa de corpus com
nulos e da contabilidade corrigida.

## O que nenhum framework e nenhuma matemática resolveram

Nada, nesta lista. As quatro frentes de triagem devolveram a mesma resposta: para cada caso
de borda havia precedente ou havia teorema. O que sobrou de aberto é medição, que é trabalho,
não impasse.
