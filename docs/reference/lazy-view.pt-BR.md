<!-- l10n: doc_id=lazy-view · lang=pt-BR · source_lang=en · translation_of=lazy-view.en.md · synced=2026-08-25 -->
[English](lazy-view.en.md) · **Português**

> Tradução de [`lazy-view.en.md`](lazy-view.en.md). Se houver divergência, o original em inglês prevalece.

# Referência: `tcf.view` (consulta sob demanda)

Referência da camada de consulta somente leitura [`tcf.view`](../../src/tcf/view.py): conecta a um
blob TCF e responde consultas (`count/sum/min/max/avg`, `where`, group-by),
**descomprimindo só o necessário**. Os filtros registrados no cabeçalho são reaplicados
quando a coluna é lida, e colunas anônimas continuam posicionais. A consulta não muda
`encode`, `decode` nem o formato.

**O que ela lê**: `#TCF.8M` (multi-coluna), `#TCF.8H` quando é tabela retangular, e a
rota de coluna única em todas as suas formas (`#TCF.8`, `#TCF.8n`, `#TCF.8b`, `#TCF.8bB`,
`#TCF.8 :spec`, e as densas `B`/`C`). Na coluna única o nome é `"0"`, como em qualquer
coluna anônima ([ADR-0029](../adr/0029-version-format-identification-semi-implicit.md)).
`#TCF.6` e
`#TCF.7` não são aceitos no pacote `0.8` (compatibilidade histórica via git).

```python
from tcf import encode, view

blob = encode({"cidade": ["SP", "SP", "RJ"], "valor": ["120", "80", "200"]})
v = view(blob)                       # conecta: NÃO descomprime nada
v.where("cidade", "SP").sum("valor") # toca só cidade + valor
```

> **Estabilidade**: a superfície L1–L4 (abaixo) é **estável**. `group_ranges`/`agg_by`
> (L5) são **experimentais**: podem evoluir no H-QUERY-04 (0.9). Marcado por método.

## Modelo

- **Lazy**: `view(blob)` só parseia o header (nome/modo/tamanho por coluna). Nenhum
  corpo é decodificado até uma query pedir aquela coluna; cada coluna é decodificada
  **no máximo uma vez** (cache interno).
- **Row-aligned por posição**: a i-ésima posição de cada coluna é a linha `i`.
  `where()` devolve os índices das linhas que casaram; agregação/`select` em **qualquer
  outra** coluna usam os mesmos índices. É assim que "a linha de uma coluna é a mesma
  linha na outra".
- **Contrato numérico** (`sum/min/max/avg`): **ignora** vazio (`""`) e nulo (`None`);
  valor não-numérico levanta `ValueError` (intencional: não silencia dado sujo). Sem
  nenhum valor numérico, `min`/`max`/`avg` levantam e `sum` devolve `0`, que é o `sum([])`
  do Python e portanto um `int`, não um `float`.
- **Só leitura**: nenhuma operação muda o blob.

## Consulta SQL-like, sem SQL

`view()` oferece caminhos de consulta que lembram uma execução SQL, mas não
interpreta uma string SQL nem tenta reproduzir todas as semânticas de um banco:

Coluna, em toda a superfície da view: `str` = **nome**, `int` = **posição**. A mesma regra
do `schema=` ([ADR-0047](../adr/0047-schema-parametro-unico-de-spec.md): `0 <= pos < n`, sem
negativo; coluna *chamada* `"2"` é achada pelo `str`, a posição pelo `int`).

**Tipo do dado**: a tabela declara o tipo de cada coluna no header (uma letra: `N` número,
`B` bool, ausente = texto), e os valores voltam no tipo em que entraram:

```python
v = view(encode({"cidade": ["SP", "SP", "RJ"], "valor": [120, 80, 200]}))
# shebang: '#TCF.8M!8=cidade,!aN=valor'  (multi-col, com a tag de tipo na 2ª coluna)
v.where("valor", 120).count()      # 1: compare com int, que é o tipo da coluna
v.sum("valor")                     # 400.0
```

Uma coluna tipada **não** tira a tabela do `.8M`: o tipo custa a tag de 1 byte no header.
O `#TCF.8H` é outra rota, a de `encode(list[dict])`, e a view também a lê quando ela é
retangular.

### Comparar: soft por padrão, strict quando você quiser

O arquivo é sempre texto, e o tipo é a leitura que o header declara. Então
`where(col, "true")` numa coluna booleana é uma intenção clara, não um erro: o **valor do
filtro** é lido no tipo da coluna, e a conversão fica registrada.

```python
v.where("ativo", "true")     # coluna bool: 'true' é lido como True, com aviso
v.where("ativo", True)       # tipo certo: nenhuma conversão, nenhum aviso
v.coercoes                   # o que foi convertido nesta view, e como
```

O cast é sempre do **lado barato**: converte o único valor do filtro, nunca as N linhas da
coluna. Numa tabela de 5 000 linhas, uma conversão.

As grafias de bool em **texto** são uma lista fechada (`true/1/t/yes/sim` e
`false/0/f/no/nao/não`, ignorando caixa e espaços), no espírito do PostgreSQL. String
não-vazia **não** vira `True` por truthiness, que é a armadilha clássica de
`astype(bool)` no pandas, e o que não tem leitura possível (`"banana"` numa coluna bool)
levanta `TypeError`: converter é ler a intenção, não adivinhar.

Um `int` numa coluna bool é outra história, e vale saber: ele passa por `bool(value)`,
então `0` é `False` e **qualquer outro inteiro** é `True`, incluindo `5` e `-1`. É a
regra do Python, não a do PostgreSQL, e é uma inconsistência com o parágrafo acima:
a proteção contra truthiness vale para texto e não vale para número.

Para código que se quer rígido, `.strict()` troca a conversão automática por erro:

```python
v = view(blob).strict()
v.where("ativo", "true")     # TypeError: a view está em modo STRICT
v.where("ativo", True)       # passa igual
```

É a política de Polars e DuckDB (que apertou na 0.10, removendo o cast implícito para
`VARCHAR`), com o padrão invertido: aqui a conveniência é o default e o rigor é opt-in,
porque no TCF o texto é o meio, não um descuido do usuário.

Uma diferença que vale saber: no `.8H` cada coluna usa o pipeline core, sem a competição
`min(tcf, raw, dict, split)` do `.8M`. O blob fica **38,3% maior** na mesma tabela de
2 000 linhas por 5 colunas, e `group_count` cai em fallback porque não há modo dicionário
nessa rota. A laziness continua de pé nas duas, e o `count()` custa 0,0% também ali.

O custo de cada operação, por modo de coluna, está medido em
[`view-usos.md`](view-usos.md).

Fora de alcance: aninhado, ragged e campo opcional não são tabela, e a view recusa com uma
mensagem que manda usar `decode()`.

| capacidade | API | observação |
|---|---|---|
| projeção | `select(cols)` | materializa apenas as colunas pedidas; escalar (`str`/`int`) = 1 coluna; `[]` = nenhuma |
| filtro | `where(col, value=...)` ou `where(col, pred=...)` | igualdade/predicado; encadeamento é AND; `value` é lido no tipo da coluna (soft), ou exigido nele com `.strict()`; `None` casa nulo |
| agregação | `count`, `sum`, `min`, `max`, `avg` | vazio e nulo são ignorados nos agregadores numéricos |
| valores distintos | `distinct(col)` · `n_unique(col)` | o `SELECT DISTINCT` e o `COUNT(DISTINCT)`; em `@dict` saem da tabelinha de únicos, em O(K) |
| agrupamento | `group_count(col)` | caminho estrutural em `@dict` sem filtro; fallback nos demais casos |
| agregação por grupo | `group_sum`, `group_min`, `group_max`, `group_avg` `(por, col)` | o `GROUP BY x AGG(y)`; materializa só as colunas envolvidas |
| agrupar por várias colunas | `group_*(["a","b"], col)` | o `GROUP BY a, b`: a chave é a tupla dos valores |
| filtrar e agrupar | `where(...).group_*(...)` | o `WHERE ... GROUP BY`: a agregação roda nas linhas que casaram |
| layout agrupado | `group_ranges`, `agg_by` | experimental; requer ordem contígua de `sort_by` |
| alinhamento | índices posicionais | a linha `i` de cada coluna é a mesma linha |

Não há parser SQL, joins, `ORDER BY`, `LIMIT`, expressões calculadas ou plano
multi-tabela. `OR` não existe **entre** colunas (o encadeamento de `where` é sempre AND),
mas `pred=` expressa OR dentro de uma coluna:
`where("uf", pred=lambda x: x in ("SP", "RJ"))`.

Uma coluna em modo `tcf` pode exigir materialização completa porque suas referências são
entrelaçadas. Para ver quais colunas uma consulta alcançou, use `touched`; para o custo
fino de cada caminho, as medições por operação estão em [`view-usos.md`](view-usos.md),
porque `materialized_bytes` é grosso demais para isso (ver a nota na tabela abaixo).

A evolução de `QueryPlan`/`execute()` e índices locais pertence ao trabalho posterior de
query, não ao formato `.8`.

## `view(blob) -> LazyTCF`  · estável

Conecta a um blob TCF. Aceita multi-coluna, tabela retangular e coluna única; `ValueError`
com mensagem que manda usar `decode()` quando o blob não é tabela (aninhado, ragged, campo
opcional) ou é de um formato legado.

## `LazyTCF`: introspecção (barata, só header) · estável

| membro | retorno | nota |
|---|---|---|
| `columns` | `list[str]` | nomes na ordem do header |
| `nrows` | `int` | nº de linhas pelo caminho mais curto: `n` declarado no cabeçalho → raw (conta `\n`) → dict (`len(stream)//width`) → contadores do core. Nenhum desses materializa valor. O modo `split` não declara contagem: se **toda** coluna da tabela for `split`, cai em decodificar a menor (medido: 49,7% numa tabela de 2 colunas) |
| `column_bytes(name)` | `int` | tamanho do corpo **comprimido** da coluna (sem decodificar) |
| `total_bytes` | `int` | soma dos corpos |
| `materialized_bytes` | `int` | soma dos corpos das colunas em `touched`. **Grosso de propósito**: conta o corpo INTEIRO da coluna assim que ela é tocada, então um `where` em `@dict`, que constrói só os K únicos, aparece com o mesmo número de um `select`, que constrói as N linhas. Serve para ver QUAIS colunas a consulta alcançou, não o custo fino de cada caminho. O ajuste está registrado para o `.9` |
| `report()` | `dict` | `{total_bytes, materialized_bytes, pct, touched, n_cols}` (seletividade) |

## `LazyTCF`: agregadores · estável

`idx` é interno (usado por `Filtered`); o uso normal é sem argumento ou via `where(...)`.

| método | retorno | contrato |
|---|---|---|
| `count(idx=None)` | `int` | nº de linhas (ou do filtro) |
| `sum(col, idx=None)` | `float` | soma; ignora vazio e nulo. Sem nenhum numérico devolve `0` (`int`, o `sum([])` do Python) |
| `min(col, idx=None)` | `float` | mínimo; `ValueError` se sem numéricos |
| `max(col, idx=None)` | `float` | máximo; idem |
| `avg(col, idx=None)` | `float` | média; idem |
| `group_count(col)` | `dict` | `{valor: n}` **sem expandir** a coluna quando ela é dicionário (`@`) e não há filtro; senão fallback (decode + Counter). A chave sai no **tipo da coluna**, então numa coluna `N` as chaves são `int`/`float` e numa `B` são `bool`, não `str` |
| `distinct(col)` | `list` | valores distintos, na ordem de aparição; em `@dict` sai da tabelinha (constrói os K, não os N) |
| `n_unique(col)` | `int` | quantos distintos; em `@dict` é o tamanho da tabelinha, sem construir valor |
| `group_sum(por, col)` | `dict` | soma por grupo; grupo sem valor aproveitável dá `0.0` |
| `group_min/max/avg(por, col)` | `dict` | idem; grupo sem valor aproveitável dá `None`, porque não há resposta (devolver `0.0` inventaria um valor que a coluna não contém) |

Em todos, `por` aceita uma coluna ou uma lista, e com lista a chave é a tupla dos valores.
Nulo e string vazia **formam grupo** (como SQL e polars, diferente do default do pandas,
que descarta); a ordem das chaves é a de aparição. Não há flag `dropna`: descartar o nulo
é um filtro, e `where(col, pred=lambda x: x is not None)` já faz, deixando à vista o que
foi jogado fora. Em coluna dicionário esse predicado roda sobre os K únicos, então a forma
explícita não custa mais caro. As divergências de semântica com o
mercado estão levantadas em
[`DECISAO-GROUPING-SEMANTICA`](../../tickets/DECISAO-GROUPING-SEMANTICA.md).

## `LazyTCF.where(col, value=None, *, pred=None) -> Filtered` · estável

Filtra por igualdade (`value`) ou predicado (`pred`), descomprimindo **só a coluna do
filtro**. Em coluna dicionário (`@`) varre o stream de índices sem decodificar os N
valores (avalia `value`/`pred` sobre os K únicos). Devolve [`Filtered`](#filtered).

Nessa coluna, os dois extremos nem chegam a varrer o stream. A tabela de únicos é a
lista fechada do que a coluna contém e toda linha aponta para algum único, então:
quando **nenhum** único casa, nenhuma linha pode casar e a resposta é `[]`; quando
**todos** casam, toda linha casa e a resposta é `range(n)`. Filtrar por um valor que a
coluna não tem passou de varrer as N posições para não ler o stream. O caso do meio
continua varrendo, porque aí a resposta depende de quais linhas apontam para quê.

## `LazyTCF.select(cols=None, idx=None) -> list[dict]` · estável

Linhas alinhadas como dicts; decodifica só as colunas pedidas (`cols=None` = todas).

## `Filtered` · estável

Resultado de `where()`. Opera só nas linhas que casaram (alinhadas).

| método | nota |
|---|---|
| `count()` | nº de linhas filtradas |
| `sum/min/max/avg(col)` | agrega `col` nas linhas filtradas |
| `select(cols=None)` | linhas filtradas como dicts |
| `distinct(col)` · `n_unique(col)` | distintos **nas linhas filtradas** |
| `group_count(col)` · `group_sum/min/max/avg(por, col)` | agrega **nas linhas filtradas**: o `WHERE ... GROUP BY` |
| `where(col, value=None, *, pred=None)` | **encadeia** (AND): restringe os índices atuais |

```python
v.where("cidade", "SP").where("plano", "Premium").sum("valor")   # AND
```

## L5: layout para baixa latência · **experimental**

Pensados pra um blob **já ordenado** por uma chave (`encode(table, sort_by=key)`), onde
os grupos ficam contíguos. Podem evoluir no H-QUERY-04 (0.9).

| método | retorno | nota |
|---|---|---|
| `group_ranges(key)` | `dict[str,(ini,fim)]` | intervalos contíguos por grupo; `ValueError` se a coluna não está agrupada |
| `agg_by(key, col=None, op="count")` | `dict` | group-by por slice; `op` ∈ `count/sum/min/max/avg` |

```python
blob = encode({"cliente": ["Ana","Bruno","Ana","Bruno"],
               "qtd": ["1","2","3","4"]}, sort_by="cliente")
v = view(blob)
v.agg_by("cliente", "qtd", "sum")     # {'Ana': 4.0, 'Bruno': 6.0}  ("qtd por cliente")
```

## Exemplo medido

```python
from tcf import encode, view
blob = encode({
    "cliente": ["Ana","Bruno","Carla","Diego","Ana","Bruno"],
    "cidade":  ["SP","SP","RJ","SP","RJ","SP"],
    "valor":   ["120","80","200","120","80","150"],
})
v = view(blob)
v.count()                                  # 6
v.group_count("cidade")                    # {'SP': 4, 'RJ': 2}
v.where("cidade", "SP").sum("valor")       # 470.0
v.report()                                 # {... 'pct': 55.6, 'touched': ['cidade','valor'], ...}
```

`report()['pct']` mostra a fração do blob materializada, a "venda" do lazy: a query
acima tocou ~56% (2 de 3 colunas) em vez de 100% que um `decode()` faria.

## Notas / limites

- **Coluna em modo `tcf`** (OBAT+HCC entrelaçados): `group_count`/agregação caem em
  **fallback** (decode da coluna inteira). O ganho estrutural limpo vive em `@dict`/raw.
  Ligar `fallback=True` no `encode` (default 0.8) põe colunas low-card em `@dict`
  automaticamente, habilitando as queries sem expandir. Ver
  [encode-knobs.md](encode-knobs.md).
- `sort_by` (para L5) é **order-free** mas reordena as linhas: `decode` devolve a tabela
  na ordem do blob. Trade-off de compressão documentado em [encode-knobs.md](encode-knobs.md).
- Compat: `from tcf_lazy import view` (shim) ainda funciona, re-exportando daqui.

## Conexões

- Implementação: [`src/tcf/view.py`](../../src/tcf/view.py)
- O que dá para perguntar, com o custo de cada pergunta: [`view-usos.md`](view-usos.md)
- Knobs do encode (`fallback`/`sort_by`): [encode-knobs.md](encode-knobs.md)
- Formato (modos `!`/`@`/`%`): [../algorithms/TCF-format.md](../algorithms/TCF-format.md)
- Design da expansão 0.9 (decode-DAG, índices): [`hquery01-decode-dag-indices-design.md`](../../experiments/lab/dirty/notas/2026-06/hquery01-decode-dag-indices-design.md)
- Ticket: [T-DOC-LAZY-REFERENCE](../../tickets/T-DOC-LAZY-REFERENCE.md) · promoção: [T-CODE-LAZY-VIEW-PROMOTE](../../tickets/T-CODE-LAZY-VIEW-PROMOTE.md)
