<!-- l10n: doc_id=consultar-sem-decodificar · lang=pt-BR · source_lang=en -->
[English](consultar-sem-decodificar.en.md) · **Português**

> Tradução de [`consultar-sem-decodificar.en.md`](consultar-sem-decodificar.en.md). Se houver divergência, o original em inglês prevalece.

# O que dá para perguntar a um blob TCF

Mapa de uso de [`tcf.view`](../../src/tcf/view.py): as perguntas que ele responde, o que
cada uma custa, e onde estão os limites. A referência de API está em
[`lazy-view.md`](../reference/lazy-view.md); aqui o recorte é por **pergunta**, não por método.

Todo número desta página vem de `experiments/lab/.../2026-08-24-0800-view-capacidades/`,
medido em n=1000 e conferido contra `decode()` célula a célula.

## A ideia em uma linha

O header do TCF já diz, por coluna, o nome, o modo e o tamanho. A `view` usa essa informação
de forma oportunista: responde pelo header ou pela estrutura compacta quando isso basta, e
só então avança para índices, posições selecionadas, uma coluna inteira ou o fallback de
correção. No modo dicionário, muitas respostas saem dos K únicos e do stream de índices sem
construir os N valores.

A rota muda o custo, não o significado. Todo atalho precisa concordar com a resposta
materializada; um atalho ainda não provado vai para lab em vez de ser adivinhado. A regra
completa está na [referência de API](../reference/lazy-view.pt-BR.md#princípio-oportunista-no-custo).

```python
from tcf import encode, view

table = {"uf":    ["SP", "SP", "RJ", "MG", None],
         "plano": [ "A",  "B",  "A",  "A",  "B"],
         "valor": [ 100,   80,  200,   50,   30]}

blob = encode(table)                   # 71 bytes
v = view(blob)                         # conecta: não descomprime nada
v.count()                              # 5, sem materializar valor nenhum
v.where("uf", "SP").sum("valor")       # 180.0, tocando só uf e valor
```

## As perguntas, da mais barata para a mais cara

### Quantas linhas tem? (`count`, `nrows`)

**Custo: 0,0% a 0,4% do wire**, com uma exceção. Contar não precisa dos valores, e a
estrutura já diz: as rotas densas escrevem o número no cabeçalho em hex; o corpo core
traz contadores (`*N|`) que declaram quantas linhas cada um vale; o corpo raw é uma
linha por valor; e no dicionário o número é `len(stream) // width`.

Nesses casos nenhum objeto de valor é construído, e depois de um `count()` puro
`report()["materialized_bytes"]` é 0.

`count` é cardinalidade de linhas, não contagem de payloads não vazios. Uma string vazia é
um valor real e ocupa uma linha:

```python
vazio = view(encode(["", "a", ""]))    # coluna própria, não a tabela acima
vazio.count()                  # 3
vazio.where(0, "").count()     # 2
vazio.n_unique(0)              # 2: "" e "a"
```

O caso-limite `view(encode([""])).count() == 1` é o contrato semântico, e é o que a
implementação faz. A distinção
entre contar linhas, valores não nulos e strings vazias em TCF, NumPy, pandas, Polars e
SQL está em [`mimetizar-pandas-sql-polars.md`](../how-to/mimetizar-pandas-sql-polars.md).

**A exceção é o modo `split`**, que não declara a contagem em lugar nenhum. Basta a
tabela ter **uma** coluna em outro modo para o `count` sair barato, porque todas as
colunas têm o mesmo número de linhas e ele usa a mais barata. Mas numa tabela em que
*toda* coluna é `split`, não há de onde ler, e o `count` decodifica a coluna menor:
medido, 49,7% numa tabela de 2 colunas.

### Que colunas existem, e quão grandes são? (`columns`, `column_bytes`, `report`)

**Custo: 0%.** Sai tudo do header.

`column_bytes` dá o tamanho **comprimido** da coluna, útil para decidir o que consultar
antes de consultar. `report()` mostra quanto já foi materializado, e serve para conferir
se uma consulta foi tão seletiva quanto se esperava.

### Quais linhas casam? (`where`)

| modo da coluna | custo |
|---|---:|
| dicionário (`@`) | **0,4%** |
| raw (`!`) | 26,1% |
| core | 39,7% |
| split (`%`) | 95,4% |
| coluna única | 100% |

No dicionário o filtro compara o valor contra os K únicos e varre um stream de índices,
sem decodificar as N linhas. Nos outros modos a coluna é materializada, porque não há
como saber o valor de uma linha sem reconstruí-la.

Dois casos nem chegam a varrer o stream: quando **nenhum** único casa a resposta é vazia,
e quando **todos** casam a resposta é todas as linhas. A tabela de únicos é a lista
fechada do que a coluna contém, então ela decide os dois extremos sozinha.

O filtro aceita igualdade (`where(col, valor)`) ou predicado
(`where(col, pred=lambda x: ...)`), e encadear é AND:

```python
v.where("uf", "SP").where("plano", "A").sum("valor")   # 100.0
```

### Qual o total, o mínimo, o máximo? (`sum`, `min`, `max`, `avg`)

**Custo: 1,6% a 48,6%,** conforme o modo da coluna **numérica** (não o da coluna do
filtro). Vazios são ignorados; valor não-numérico levanta, de propósito, para não
silenciar dado sujo.

### Quais valores existem nessa coluna? (`distinct`, `n_unique`)

O `SELECT DISTINCT` e o `COUNT(DISTINCT col)`. Numa coluna dicionário saem da tabelinha
de únicos, que o corpo já carrega pronta, em O(K):

```python
v.distinct("uf")      # ['SP', 'RJ', 'MG', None], na ordem de aparição
v.n_unique("uf")      # 4
```

Os dois custam coisas diferentes, e vale saber: `n_unique` só precisa do **tamanho** da
tabelinha, então não constrói valor nenhum e `report()` fica em zero. `distinct` constrói
os K únicos, porque é isso que ele devolve. Os K, não os N: numa coluna de 600 linhas com
3 valores distintos, três.

Aceitam lista de colunas e funcionam depois de um `where`, como o resto da família.

### Quantos por valor? (`group_count`)

| modo | custo |
|---|---:|
| dicionário | **0,4%** |
| raw | 26,1% |
| core | 39,7% |
| split | 95,4% |

No dicionário a contagem por grupo sai de contar os índices do stream, sem expandir as
linhas. Nos demais modos cai em decodificar a coluna e contar.

### Soma, mínimo, máximo, média por grupo? (`group_sum`, `group_min`, `group_max`, `group_avg`)

**Custo: 52% a 97%, o mais caro da superfície.** Materializa as colunas envolvidas e
cruza linha a linha, sem usar a estrutura de nenhuma delas.

```python
v.group_sum("uf", "valor")            # {'SP': 180.0, 'RJ': 200.0, 'MG': 50.0, None: 30.0}
v.group_avg("uf", "valor")            # {'SP': 90.0, 'RJ': 200.0, 'MG': 50.0, None: 30.0}
v.group_sum(["uf", "plano"], "valor") # GROUP BY uf, plano: a chave vira tupla
```

**Nulo na chave forma grupo**, como em SQL e polars. O pandas descarta por padrão
(`dropna=True`), e não há uma flag equivalente aqui de propósito: descartar o nulo é um
filtro, e o filtro já existe.

```python
v.group_count("uf")                     # {'SP': 2, 'RJ': 1, 'MG': 1, None: 1}
v.where("uf", pred=lambda x: x is not None).group_count("uf")   # o "dropna", sem o None
```

Escrever o filtro deixa à vista o que está sendo jogado fora, e uma flag esconderia isso
atrás de uma semântica. Numa coluna dicionário o predicado ainda roda sobre os K únicos,
não sobre as N linhas, então a alternativa explícita não custa mais caro: medido, três
avaliações para 600 linhas.

Um grupo sem nenhum valor aproveitável (todos nulos ou vazios) soma `0.0`, porque a soma
do conjunto vazio é zero, e isso é definição e não convenção. Mas `min`, `max` e `avg`
devolvem `None` ali, porque não há resposta: o menor de nenhum valor não existe, e
devolver `0.0` inventaria um número que a coluna não contém. O grupo aparece nos dois
casos, em vez de sumir, para não esconder que a chave estava lá.

O `group_sum` sozinho não distingue um grupo que somou zero de verdade de um sem valores,
mas a informação não se perde: `group_min` devolve `0.0` no primeiro e `None` no segundo.
Para obter o `NULL` do SQL, e o comportamento das outras ferramentas em geral, veja
[como mimetizar pandas, SQL e polars](../how-to/mimetizar-pandas-sql-polars.md).

### Filtrar e agrupar (`where(...).group_*`)

O `WHERE … GROUP BY`. A agregação roda nas linhas que casaram:

```python
v.where("plano", "A").group_sum("uf", "valor")   # {'SP': 100.0, 'RJ': 200.0, 'MG': 50.0}
v.where("plano", "A").group_count("uf")         # {'SP': 1, 'RJ': 1, 'MG': 1}
```

### As linhas em si (`select`)

**Custo: proporcional ao que se pede,** e aqui isso não é desperdício: `select` devolve
os valores, então materializar a coluna é o trabalho. O número que importa é a
comparação: no dicionário, `select` de uma coluna custa 49,1% e de todas custa 99,1%.

```python
v.select("uf")                 # só a coluna uf
v.select(["uf", "valor"])      # duas
v.select()                     # todas, equivalente a decode()
```

## O contrato

Esta página é sobre **qual pergunta fazer**. O contrato de cada chamada, como nomear uma
coluna, o que a view recusa a ler e o que é estável vivem num lugar só:
[`../reference/lazy-view.md`](../reference/lazy-view.md).

## O que a estrutura permitiria, e ainda não existe

Isto não é promessa de release, é o mapa do que foi medido como possível. O registro
completo, com o que foi **refutado**, está nos labs de 2026-08-24.

Os caminhos óbvios já fechados na superfície atual são introspecção pelo header, contagem
estrutural de linhas, `distinct`/`n_unique`/`group_count` por dicionário, extremos de filtro
sem-casa/todos-casam e pruning de colunas. Em `0.8.x`, o trabalho óbvio restante é de
correção, como a contagem de uma única string vazia, não um novo planejador de consultas.

| oportunidade | como | evidência | classificação |
|---|---|---|---|
| `group_*` pela estrutura, sem materializar | cruzar os streams de índices das duas colunas sem construir valor de linha | protótipo medido: 71,8% menos bytes | otimização direta do `.9`; preservar semântica de nulo/vazio |
| `sum`/`min`/`max`/`avg` sobre dicionário | agregar os K únicos ponderados pela frequência | medido: 99,6% menos bytes; `min`/`max` são exatos por construção | candidato direto do `.9`; casos filtrados e tipados ainda são gate |
| responder “existe?” sem montar a lista de índices | adiar a construção dos índices dentro do resultado do `where` | não implementado | desenho de resultado latente; lab antes da API |
| emitir um TCF filho filtrado/projetado | recortar corpos raw, dicionário e split; fallback no core | mecanismo `.8M` e oráculo diferencial provados | API `.9`; [`T-CODE-VIEW-SUBTCF-RECORTE`](../../tickets/T-CODE-VIEW-SUBTCF-RECORTE.md) |

E o que **não** é possível, por razão estrutural e não por falta de trabalho:

- **Resolver o valor de uma linha do corpo core sem replay.** Os ids de fragmento não
  viajam no wire; encoder e decoder mantêm contadores espelhados. Pular uma declaração
  devolve valor errado **sem erro**.
- **Prefiltrar por substring no corpo core.** O OBAT fragmenta o valor, então a forma
  escapada de um valor presente não é substring do corpo: dá falso negativo.
- **`min`/`max` no bit-pack denso.** O domínio é ordenado por primeira aparição, não por
  valor.

## Conexões

- Referência de API: [`lazy-view.md`](../reference/lazy-view.md)
- Knobs do encode (`fallback`, `sort_by`): [`encode-knobs.md`](../reference/encode-knobs.md)
- Formato e modos: [`../algorithms/TCF-format.md`](../algorithms/TCF-format.md)
