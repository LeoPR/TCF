# Como obter, no TCF, o comportamento que você já conhece

Agrupar tem decisões que não têm resposta única, e cada ferramenta escolheu uma.
[`tcf.view`](../reference/lazy-view.md) segue a **matemática** e deixa a convenção do lado
de fora, o que é uma escolha deliberada: convenção de programação se faz em uma linha
depois, e ela fica visível para quem lê o código.

Esta página traz essa linha, pronta, para cada caso. Toda receita aqui é verificada por
execução contra o que a ferramenta de origem devolveria; nenhuma é aproximação.

A tabela dos exemplos, com as três divergências de uma vez (chave nula, grupo sem valor
aproveitável, chaves fora de ordem):

```python
from tcf import encode, view

blob = encode({"g": ["z", None, "a", "z", "m", None, "a"],
               "v": [ 10,  20,  None, 30,  50,  60,  None]})
v = lambda: view(blob)
```

## O default do TCF

```python
v().group_sum("g", "v")     # {'z': 40.0, None: 80.0, 'a': 0.0, 'm': 50.0}
v().group_min("g", "v")     # {'z': 10.0, None: 20.0, 'a': None, 'm': 50.0}
```

Nulo **forma grupo**. Um grupo sem nenhum valor aproveitável (`a`, cujos dois valores são
nulos) **soma `0.0`**, porque a soma do conjunto vazio é zero, e isso é matemática, não
convenção. Mas `min`, `max` e `avg` devolvem `None` ali, porque não há resposta: o menor de
nenhum valor não existe, e devolver `0.0` inventaria um número que a coluna não contém.

A ordem das chaves é a de **aparição**.

## Como o pandas responderia

O `groupby` do pandas descarta a chave nula por padrão (`dropna=True`) e ordena as chaves.

```python
resultado = v().where("g", pred=lambda x: x is not None).group_sum("g", "v")
dict(sorted(resultado.items(), key=lambda kv: str(kv[0])))
# {'a': 0.0, 'm': 50.0, 'z': 40.0}
```

O filtro faz o papel do `dropna`, e ele custa pouco: numa coluna dicionário o predicado
roda sobre os K únicos, não sobre as N linhas.

## Como o SQL responderia

No SQL, `SUM` de um grupo sem valores dá `NULL`, não zero. O `group_min` marca exatamente
esses grupos, então ele serve de máscara:

```python
somas   = v().group_sum("g", "v")
minimos = v().group_min("g", "v")        # None marca o grupo sem valor
{k: (None if minimos[k] is None else s) for k, s in somas.items()}
# {'z': 40.0, None: 80.0, 'a': None, 'm': 50.0}
```

## Como o polars responderia

É o default do TCF, sem receita nenhuma: nulo forma grupo, ordem de aparição.

```python
v().group_sum("g", "v")     # {'z': 40.0, None: 80.0, 'a': 0.0, 'm': 50.0}
```

## Só os grupos que têm valor

Nem toda pergunta é "como a ferramenta X faz". Às vezes o que se quer é descartar os grupos
vazios:

```python
{k: s for k, s in somas.items() if minimos[k] is not None}
# {'z': 40.0, None: 80.0, 'm': 50.0}
```

## `COUNT(col)` do SQL, que pula `NULL`

O `group_count` do TCF conta **linhas** do grupo, como o `COUNT(*)`. O `COUNT(col)` do SQL
conta só as linhas em que aquela coluna não é nula, e mantém o grupo com zero:

```python
por_grupo = v().where("v", pred=lambda x: x is not None and x != "").group_count("g")
{k: por_grupo.get(k, 0) for k in v().group_count("g")}
# {'z': 2, None: 2, 'a': 0, 'm': 1}
```

O segundo passo reintroduz com zero os grupos que o filtro removeu, que é o que faz a
diferença entre "o grupo não tem valores" e "o grupo não existe".

## Por que não há flags para isso

Cada receita acima é **uma transformação explícita** sobre o resultado. Uma flag
(`dropna=True`, `null_empty=True`) seria mais curta de escrever e esconderia o que está
sendo feito atrás de uma palavra. Quem lê `where(g, pred=lambda x: x is not None)` sabe
exatamente o que foi jogado fora; quem lê `dropna=True` precisa lembrar a convenção.

Há uma consequência de desempenho, e ela está registrada em vez de escondida: hoje a
receita passa por dois caminhos (o filtro e depois a agregação), enquanto uma flag poderia
resolver numa passada só. Se alguma dessas combinações virar caso comum, a fusão dos dois
caminhos é trabalho de otimização do `.9`, registrada como `H-QUERY-04e`. A escolha de
hoje é por clareza; a de amanhã pode ser por caminho curto, e aí a flag entra com um
caminho otimizado atrás dela, não como açúcar sobre o mesmo trabalho.

## Verificação

As receitas desta página são geradas e conferidas por
`experiments/lab/dirty/2026-08/2026-08-25/2026-08-25-0500-grupo-sem-valor/2-receitas.py`,
que compara cada uma com o resultado calculado à mão em Python puro. Uma receita só entra
aqui se aquele script passar.

## Conexões

- Referência de API: [`../reference/lazy-view.md`](../reference/lazy-view.md)
- O que dá para perguntar, com o custo: [`../reference/view-usos.md`](../reference/view-usos.md)
- A matriz completa de divergências: [`DECISAO-GROUPING-SEMANTICA`](../../tickets/DECISAO-GROUPING-SEMANTICA.md)
