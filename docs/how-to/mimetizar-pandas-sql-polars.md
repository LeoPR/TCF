# Como obter, no TCF, o comportamento que você já conhece

Agrupar tem decisões que não têm resposta única, e cada ferramenta escolheu uma.
[`tcf.view`](../reference/lazy-view.md) segue a **matemática** e deixa a convenção do lado
de fora, o que é uma escolha deliberada: convenção de programação se faz em uma linha
depois, e ela fica visível para quem lê o código.

Esta página traz essa linha, pronta, para cada caso. As receitas TCF com resultado concreto
são verificadas por execução contra o que a ferramenta de origem devolveria; a tabela
comparativa de contagem abaixo é um mapa de semântica entre APIs, não um benchmark.

As equivalências abaixo são de **semântica da pergunta**, não de nome de método. “Contar
posições”, “contar valores presentes” e “contar strings vazias” são perguntas diferentes,
e cada biblioteca oferece operadores distintos para elas.

A tabela dos exemplos, com as três divergências de uma vez (chave nula, grupo sem valor
aproveitável, chaves fora de ordem):

```python
from tcf import encode, view

blob = encode({"g": ["z", None, "a", "z", "m", None, "a"],
               "v": [ 10,  20,  None, 30,  50,  60,  None]})
v = lambda: view(blob)
```

## Elemento vazio não é ausência

Uma string vazia é um valor presente. Ela ocupa uma posição, pode ser distinta e pode ser
alvo de igualdade. `None`/`NULL` é ausência; o fato de não haver payload útil não apaga a
linha. Para a `view`, a contagem de linhas é a cardinalidade da tabela:

```python
vazio = view(encode(["", "a", ""]))

vazio.count()                  # 3: conta posições, inclusive ""
vazio.where(0, "").count()     # 2: conta as strings vazias
vazio.n_unique(0)              # 2: "" e "a"
```

O caso-limite de uma única posição vazia está registrado em
[`BUG-VIEW-UMA-STRING-VAZIA`](../../tickets/BUG-VIEW-UMA-STRING-VAZIA.md): o contrato é
`count() == 1`, e é o que a implementação faz desde a correção de 2026-08-27.

### A mesma pergunta em outras ferramentas

Não há um `count` universal. Estes operadores mostram como escrever a mesma intenção:

| pergunta | TCF | NumPy | pandas | Polars | SQL |
|---|---|---|---|---|---|
| todas as posições/linhas | `view(blob).count()` | `a.size` | `s.size` | `s.len()` | `COUNT(*)` |
| valores não ausentes | `v().where("x", pred=lambda x: x is not None).count()` | `np.ma.count(np.ma.array(a, mask=missing_mask))` | `s.count()` | `s.count()` | `COUNT(x)` |
| strings vazias | `v().where("x", "").count()` | `np.count_nonzero(a == "")` | `(s == "").sum()` | `(s == "").sum()` | `SUM(CASE WHEN x = '' THEN 1 ELSE 0 END)` |

Nos exemplos externos, pense em `a`, `s` e `x` como a mesma coluna contendo `""`, `"a"`
e, quando aplicável, `None`/`NULL`. Em particular:

- NumPy não escolhe sozinho uma semântica de missing: `size` conta slots, enquanto
    `count_nonzero(a)` conta valores truthy. Para strings vazias, compare explicitamente com
    `""`.
- pandas e Polars contam `""` como valor não nulo. O que eles removem por padrão nessa
    operação é `None`/`NULL`, não a string vazia.
- SQL separa `COUNT(*)` (linhas) de `COUNT(x)` (valores não nulos). Como `""` não é `NULL`,
    `COUNT(x)` também o conta. Para declarar que vazio textual deve ser missing, use
    `COUNT(NULLIF(x, ''))`.

No TCF, para obter essa última convenção, escreva-a no predicado:

```python
v().where("x", pred=lambda x: x is not None and x != "").count()
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
conta só as linhas em que aquela coluna não é nula, **mas conta `""`**, e mantém o grupo
com zero:

```python
por_grupo = v().where("v", pred=lambda x: x is not None).group_count("g")
{k: por_grupo.get(k, 0) for k in v().group_count("g")}
# {'z': 2, None: 2, 'a': 0, 'm': 1}
```

O segundo passo reintroduz com zero os grupos que o filtro removeu, que é o que faz a
diferença entre "o grupo não tem valores" e "o grupo não existe". Se a política desejada
for a de `COUNT(NULLIF(v, ''))`, acrescente `and x != ""` ao predicado; isso é uma escolha
explícita de tratar a string vazia como ausência, não o comportamento matemático de
`count()`.

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
