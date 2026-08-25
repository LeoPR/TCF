<!-- l10n: doc_id=lazy-view · lang=pt-BR · source_lang=en · translation_of=lazy-view.en.md · synced=2026-08-25 -->
[English](lazy-view.en.md) · **Português**

> Tradução de [`lazy-view.en.md`](lazy-view.en.md). Se houver divergência, o original em inglês prevalece.

# Referência: `tcf.view` (consulta sob demanda)

`view(blob)` conecta a um blob TCF e responde perguntas sobre ele, descomprimindo só o que
cada pergunta precisa. É somente leitura: nada aqui muda o blob, o `encode` ou o `decode`.

Você chama `view()` uma vez e depois chama métodos no que ele devolve. Filtrar devolve
outro objeto com os mesmos métodos, então os filtros encadeiam.

**O que ela lê**: `#TCF.8M` (multi-coluna), `#TCF.8H` quando é tabela retangular, e a rota
de coluna única em todas as suas formas (`#TCF.8`, `#TCF.8n`, `#TCF.8b`, `#TCF.8bB`,
`#TCF.8 :spec`, e as densas `B`/`C`). Na coluna única o nome é `"0"`, como em qualquer
coluna anônima ([ADR-0029](../adr/0029-version-format-identification-semi-implicit.md)).
`#TCF.6` e `#TCF.7` não são aceitos no pacote `0.8` (compatibilidade histórica via git).

## A superfície inteira em quatro linhas

Uma tabela pequena o bastante para ler, todas as operações sobre ela, e a saída real de
cada uma.

```python
from tcf import encode, view

tabela = {"uf":    ["SP", "SP", "RJ", "MG"],
          "valor": [  10,   20,   30,   40],
          "ativo": [True, False, True, True]}

blob = encode(tabela)         # 70 bytes
```

Esse blob, linha a linha:

```
#TCF.8M!b=uf,aN=valor,11B=ativo   header: nome, modo e tamanho por coluna.
                                  `N` e `B` são as tags de tipo, um byte cada.
SP                                corpo de `uf`: modo raw, uma linha por valor
SP
RJ
MG*4+10|\10                       corpo de `valor`: modo core. `*4+10|` é um contador:
                                  4 linhas, passo 10, começando em 10
true                              corpo de `ativo`
false
*2|^1                             `*2|` repete duas vezes; `^1` referencia o `true`
```

Agora as consultas. Repare no `report()["pct"]`, a fração do blob já materializada:

```python
v = view(blob)                        # conecta: NÃO descomprime nada

v.columns                             # ['uf', 'valor', 'ativo']    pct: 0.0
v.count()                             # 4                           pct: 0.0
v.distinct("uf")                      # ['SP', 'RJ', 'MG']          pct: 28.9
v.n_unique("uf")                      # 3                           pct: 28.9
v.sum("valor")                        # 100.0                       pct: 55.3

v.where("uf", "SP").count()           # 2
v.where("uf", "SP").sum("valor")      # 30.0
v.group_count("uf")                   # {'SP': 2, 'RJ': 1, 'MG': 1}
v.group_sum("uf", "valor")            # {'SP': 30.0, 'RJ': 30.0, 'MG': 40.0}
v.select("uf")                        # [{'uf': 'SP'}, {'uf': 'SP'}, ...]
```

`columns` e `count` leem só a estrutura, então nada é materializado. O `distinct` traz o
`uf`, o `sum` traz o `valor`, e o `ativo` nunca é tocado. É a ideia inteira desta camada.

O resto desta página é uma seção por pergunta, e depois os detalhes que só importam quando
você esbarra neles.

## Conhecer a tabela

Tudo aqui sai do header, sem custo.

| chamada | devolve | nota |
|---|---|---|
| `v.columns` | `list[str]` | nomes na ordem do header |
| `v.count()` | `int` | número de linhas |
| `v.nrows` | `int` | o mesmo número, como propriedade |
| `v.column_bytes(nome)` | `int` | tamanho **comprimido** da coluna, útil para decidir o que consultar antes de consultar |
| `v.total_bytes` | `int` | soma dos corpos |
| `v.report()` | `dict` | `{total_bytes, materialized_bytes, pct, touched, n_cols}` |

O `count` nunca materializa valor, em nenhum modo: a estrutura já declara a contagem. A
única exceção é uma tabela em que **toda** coluna é `split`, que não declara contagem em
lugar nenhum; ali ele decodifica a menor (medido: 49,7% numa tabela de 2 colunas).

## Filtrar

```python
v.where("uf", "SP")                              # por igualdade
v.where("valor", pred=lambda x: x > 20)          # por predicado
v.where("uf", "SP").where("ativo", True)         # encadeado: AND
v.where("uf", None)                              # None casa nulo
```

O `where` devolve um objeto com os mesmos métodos de consulta, restrito às linhas que
casaram. Você pode contar, agregar, agrupar, projetar ou filtrar de novo sobre ele.

Ele descomprime **só a coluna do filtro**. Numa coluna dicionário compara contra os K
valores únicos e varre um stream de índices, sem decodificar as N linhas, e os dois
extremos nem chegam a varrer: quando nenhum único casa a resposta é vazia, e quando todos
casam a resposta é todas as linhas.

## Agregar

```python
v.sum("valor")                       # 100.0
v.min("valor")                       # 10.0
v.max("valor")                       # 40.0
v.avg("valor")                       # 25.0
v.where("uf", "SP").sum("valor")     # 30.0, só sobre as linhas que casaram
```

Vazio (`""`) e nulo (`None`) são ignorados. Valor não-numérico levanta `ValueError`, de
propósito: dado sujo não é silenciado. Sem nenhum valor numérico, `min`/`max`/`avg`
levantam e `sum` devolve `0`, que é o `sum([])` do Python e portanto um `int`.

## Valores distintos

```python
v.distinct("uf")      # ['SP', 'RJ', 'MG'], na ordem de aparição
v.n_unique("uf")      # 3
```

O `SELECT DISTINCT` e o `COUNT(DISTINCT col)`. Numa coluna dicionário os dois saem da
tabelinha de únicos que o corpo já carrega, em O(K). Eles custam coisas diferentes:
`n_unique` só precisa do tamanho dessa tabela e não constrói valor, enquanto `distinct`
constrói os K únicos, porque é isso que ele devolve.

## Agrupar

```python
v.group_count("uf")                        # {'SP': 2, 'RJ': 1, 'MG': 1}
v.group_sum("uf", "valor")                 # {'SP': 30.0, 'RJ': 30.0, 'MG': 40.0}
v.group_min("uf", "valor")                 # também group_max, group_avg

v.group_sum(["uf", "ativo"], "valor")      # GROUP BY uf, ativo: a chave é uma tupla
v.where("ativo", True).group_sum("uf", "valor")   # o WHERE ... GROUP BY
```

A família inteira também funciona depois de um `where`, e a chave de agrupamento aceita
lista de colunas.

Nulo e string vazia **formam grupo**, como em SQL e polars, diferente do default do pandas
que descarta. A chave sai no **tipo da coluna**, então numa coluna `N` as chaves são
números e numa `B` são booleanos.

Um grupo sem nenhum valor aproveitável soma `0.0`, porque a soma do conjunto vazio é zero.
Mas `min`, `max` e `avg` devolvem `None` ali, porque não há resposta, e devolver `0.0`
inventaria um valor que a coluna não contém. O grupo aparece nos dois casos, em vez de
sumir.

Se você espera o que o pandas, o SQL ou o polars responderiam,
[o guia de equivalências](../how-to/mimetizar-pandas-sql-polars.md) traz a linha de código
de cada um.

## Pegar as linhas

```python
v.select("uf")                  # uma coluna
v.select(["uf", "valor"])       # duas
v.select()                      # todas, equivalente ao decode()
v.where("uf", "SP").select()    # só as linhas que casaram
```

As linhas voltam alinhadas como dicts: a i-ésima posição de cada coluna é a linha `i`, e é
assim que um filtro numa coluna consegue agregar outra. Aqui materializar a coluna **é** o
trabalho, não overhead, porque o `select` devolve os valores. Um escalar (`str` ou `int`)
significa uma coluna; `[]` significa nenhuma.

---

As seções abaixo são detalhes. Importam quando você esbarra neles, não antes.

## Como nomear a coluna

`str` é **nome**, `int` é **posição**. A mesma regra do `schema=`
([ADR-0047](../adr/0047-schema-parametro-unico-de-spec.md): `0 <= pos < n`, sem negativo).
Uma coluna *chamada* `"2"` é achada pelo `str`; a posição 2, pelo `int`.

## Tipos, e comparar contra eles

A tabela declara o tipo de cada coluna no header (uma letra: `N` número, `B` bool, ausente
= texto), e os valores voltam no tipo em que entraram. Então a comparação é nesse tipo:

```python
v.where("valor", 30).count()     # 1   int, porque a coluna é `N`
v.where("ativo", True).count()   # 3   bool, porque a coluna é `B`
```

Uma coluna tipada **não** tira a tabela do `.8M`: o tipo custa a tag de 1 byte no header.

### Soft por padrão, strict quando você quiser

O arquivo é sempre texto, e o tipo é a leitura que o header declara. Então
`where(col, "true")` numa coluna booleana é uma intenção clara, não um erro: o valor do
filtro é lido no tipo da coluna, e a conversão fica registrada em `v.coercoes`.

```python
blob = encode({"ativo": [True, False, True], "n": [1, 2, 3]})

view(blob).where("ativo", "true").count()            # 2, com aviso
view(blob).strict().where("ativo", "true")           # TypeError
view(blob).strict().where("ativo", True).count()     # 2, sem aviso
```

O cast é sempre do **lado barato**: converte o único valor do filtro, nunca as N linhas da
coluna.

O `.strict()` vale para a view inteira e é mão única: não existe `.soft()` de volta. Ele
afeta só o `where` (e o `where` encadeado); `select`, `sum` e a família `group_*` ignoram a
flag, porque nenhum deles recebe valor do usuário para converter.

É a política de Polars e DuckDB (que apertou na 0.10, removendo o cast implícito para
`VARCHAR`), com o padrão invertido: aqui a conveniência é o default e o rigor é opt-in,
porque no TCF o texto é o meio, não um descuido do usuário.

### As grafias de bool, e uma inconsistência

As grafias de bool em **texto** são uma lista fechada (`true/1/t/yes/sim` e
`false/0/f/no/nao/não`, ignorando caixa e espaços), no espírito do PostgreSQL. String
não-vazia **não** vira `True` por truthiness, que é a armadilha clássica do `astype(bool)`
no pandas, e o que não tem leitura possível (`"banana"` numa coluna bool) levanta
`TypeError`.

Um `int` numa coluna bool é outra história: ele passa por `bool(value)`, então `0` é
`False` e **qualquer outro inteiro** é `True`, incluindo `5` e `-1`. É a regra do Python,
não a do PostgreSQL, e é uma inconsistência com o parágrafo acima: a proteção contra
truthiness vale para texto e não vale para número.

## O que ela não faz

Não é SQL. Não há parser, joins, `ORDER BY`, `LIMIT`, expressões calculadas ou plano
multi-tabela. `OR` não existe **entre** colunas, porque encadear `where` é sempre AND, mas
dentro de uma coluna o predicado expressa OR:
`where("uf", pred=lambda x: x in ("SP", "RJ"))`.

Não lê o que não é tabela. Aninhado, ragged e campo opcional fazem a view recusar com uma
mensagem que manda usar `decode()`. Um aviso: no `#TCF.8H` um `None` explícito marca a
coluna como opcional, então `encode([{"a": 1}, {"a": None}])` produz um blob que a view
recusa, apesar de a coluna existir em todas as linhas.

## Como ler o `report()`

O `materialized_bytes` é **grosso de propósito**: conta o corpo inteiro de uma coluna assim
que ela é tocada. Então um `where` num dicionário, que constrói só os K únicos, mostra o
mesmo número de um `select`, que constrói as N linhas. Use `touched` para ver *quais*
colunas uma consulta alcançou; para o custo fino de cada caminho, as medições por operação
estão em [`view-usos.md`](view-usos.md). O ajuste está registrado para o `.9`.

## O custo depende do modo da coluna

Uma coluna em modo `tcf` (OBAT+HCC entrelaçados) faz `group_count` e agregação caírem em
decodificar a coluna inteira, porque suas referências são resolvidas em sequência. O ganho
estrutural limpo vive em `@dict` e raw.

`fallback=True` no `encode` (o default do 0.8) põe colunas de baixa cardinalidade em
`@dict` automaticamente, que é o que habilita os caminhos estruturais. Ver
[encode-knobs.md](encode-knobs.md).

No `.8H` cada coluna usa o pipeline core, sem a competição `min(tcf, raw, dict, split)` do
`.8M`: o blob fica 38,3% maior na mesma tabela de 2 000 linhas por 5 colunas, e
`group_count` cai em fallback. A laziness continua de pé nas duas, e o `count()` custa 0,0%
também ali.

## Onde ela ganha, e onde ela apenas funciona

Duas vantagens diferentes se confundem se não forem separadas:

- **Entre colunas**: a view nunca toca as colunas que a pergunta não pede. Isso vale em
  todo modo, e cresce com a largura da tabela.
- **Dentro da coluna**: a view responde sem materializar nem a coluna consultada, lendo a
  estrutura do corpo. Isso só acontece onde a estrutura permite.

A segunda é o que separa um ganho real de "funciona". Se a coluna consultada é
materializada inteira, o que sobra é um filtro pós-decode sobre ela, e a economia vem só
das colunas que não foram tocadas.

Medido em n=2000, três colunas. "estrutura" significa que a operação construiu **menos
valores do que há linhas**:

| operação | `@dict` | `%split` | core |
|---|---|---|---|
| `count`, `nrows` | estrutura | estrutura | estrutura |
| `n_unique`, `distinct` | **estrutura** | materializa | materializa |
| `where` (igualdade ou predicado) | **estrutura** | materializa | materializa |
| `group_count` | **estrutura** | materializa | materializa |
| `group_sum` e família | materializa | materializa | materializa |
| `sum`/`min`/`max`/`avg` | materializa | materializa | materializa |
| `select` | materializa | materializa | materializa |

Em palavras:

**`count` é a única que ganha sempre.** Todo modo declara a contagem de linhas em algum
lugar da estrutura.

**Cinco operações ganham só em coluna dicionário**: `n_unique`, `distinct`, `where`,
`group_count`. Ali o corpo carrega uma tabela de K únicos e um stream de índices, então a
pergunta é respondida sobre os K, não sobre os N. Nos outros modos a mesma chamada
materializa a coluna, e se comporta como um filtro pós-decode.

**Os agregadores e o `select` sempre materializam a coluna**, em todo modo, e para o
`select` isso não é defeito: devolver os valores *é* o trabalho. Para o `sum` e a família
`group_*` é um limite real, e o protótipo que o removeria em dicionários está medido mas
não soldado (ver [`view-usos.md`](view-usos.md)).

O que isso significa na prática: uma tabela com uma coluna de baixa cardinalidade e várias
largas é o formato para o qual a view foi feita. Uma tabela de uma coluna só, de alta
cardinalidade, é o formato em que `view()` e `decode()` custam quase o mesmo, e o honesto é
dizer isso.

Este é o retrato do `.8`. Os protótipos que moveriam `group_*` e os agregadores para a
coluna "estrutura" estão medidos e registrados para o `.9`.

## Layout ordenado · **experimental**

Para um blob **já ordenado** por uma chave (`encode(table, sort_by=chave)`), onde os grupos
ficam contíguos. Os dois podem evoluir no H-QUERY-04 (0.9).

```python
blob = encode({"cliente": ["Ana","Bruno","Ana","Bruno"],
               "qtd": ["1","2","3","4"]}, sort_by="cliente")
view(blob).agg_by("cliente", "qtd", "sum")     # {'Ana': 4.0, 'Bruno': 6.0}
```

| chamada | devolve | nota |
|---|---|---|
| `group_ranges(chave)` | `dict[str,(ini,fim)]` | intervalos contíguos por grupo; `ValueError` se a coluna não está agrupada |
| `agg_by(chave, col=None, op="count")` | `dict` | group-by por slice; `op` ∈ `count/sum/min/max/avg` |

A pré-condição é **contiguidade**, não o `sort_by` em si: uma tabela que por acaso está
contígua funciona sem ter sido ordenada. E o `sort_by` reordena as linhas, então o `decode`
devolve a tabela na ordem do blob. Trade-off documentado em
[encode-knobs.md](encode-knobs.md).

## Estabilidade

Tudo acima, exceto o layout ordenado, é **estável**: `columns`, `count`, `nrows`,
`column_bytes`, `total_bytes`, `report`, `where`, `select`, os agregadores, `distinct`,
`n_unique` e a família `group_*`. `group_ranges` e `agg_by` são **experimentais**.

Os objetos que `view()` e `where()` devolvem (`LazyTCF` e `Filtered`) não são para ser
construídos diretamente; o ponto de entrada é `view(blob)`.

Compat: `from tcf_lazy import view` (shim) ainda funciona, re-exportando daqui.

## Ver também

- O que dá para perguntar, com o custo medido de cada pergunta: [`view-usos.md`](view-usos.md)
- Obter o comportamento de pandas, SQL ou polars: [`../how-to/mimetizar-pandas-sql-polars.md`](../how-to/mimetizar-pandas-sql-polars.md)
- Knobs do encode (`fallback`/`sort_by`): [encode-knobs.md](encode-knobs.md)
- Formato (modos `!`/`@`/`%`): [../algorithms/TCF-format.md](../algorithms/TCF-format.md)
- Implementação: [`src/tcf/view.py`](../../src/tcf/view.py)
- Design da expansão 0.9 (decode-DAG, índices): [`hquery01-decode-dag-indices-design.md`](../../experiments/lab/dirty/notas/2026-06/hquery01-decode-dag-indices-design.md)
