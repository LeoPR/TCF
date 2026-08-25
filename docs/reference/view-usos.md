# O que dá para perguntar a um blob TCF

Mapa de uso de [`tcf.view`](../../src/tcf/view.py): as perguntas que ele responde, o que
cada uma custa, e onde estão os limites. A referência de API está em
[`lazy-view.md`](lazy-view.md); aqui o recorte é por **pergunta**, não por método.

Todo número desta página vem de `experiments/lab/.../2026-08-24-0800-view-capacidades/`,
medido em n=1000 e conferido contra `decode()` célula a célula.

## A ideia em uma linha

O header do TCF já diz, por coluna, o nome, o modo e o tamanho. Dá para fatiar o corpo
sem decodificar nada, e descomprimir só a coluna que a pergunta toca. Quando o modo da
coluna é dicionário, dá para ir além: responder pela estrutura, sem tocar os valores.

```python
from tcf import encode, view

blob = encode({"uf": ["SP", "SP", "RJ"], "valor": [120, 80, 200]})
v = view(blob)                         # conecta: não descomprime nada
v.count()                              # 3, sem materializar valor nenhum
v.where("uf", "SP").sum("valor")       # 200.0, tocando só uf e valor
```

## As perguntas, da mais barata para a mais cara

### Quantas linhas tem? (`count`, `nrows`)

**Custo: 0,0% a 0,4% do wire**, com uma exceção. Contar não precisa dos valores, e a
estrutura já diz: as rotas densas escrevem o número no cabeçalho em hex; o corpo core
traz contadores (`*N|`) que declaram quantas linhas cada um vale; o corpo raw é uma
linha por valor; e no dicionário o número é `len(stream) // width`.

Nesses casos nenhum objeto de valor é construído, e depois de um `count()` puro
`report()["materialized_bytes"]` é 0.

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
v.where("uf", "SP").where("plano", "Premium").sum("valor")
```

### Qual o total, o mínimo, o máximo? (`sum`, `min`, `max`, `avg`)

**Custo: 1,6% a 48,6%,** conforme o modo da coluna **numérica** (não o da coluna do
filtro). Vazios são ignorados; valor não-numérico levanta, de propósito, para não
silenciar dado sujo.

### Quantos por valor? (`group_count`)

| modo | custo |
|---|---:|
| dicionário | **0,4%** |
| raw | 26,1% |
| core | 39,7% |
| split | 95,4% |

No dicionário a contagem por grupo sai de contar os índices do stream, sem expandir as
linhas. Nos demais modos cai em decodificar a coluna e contar.

### Soma por grupo? (`group_sum`)

**Custo: 52% a 97%, o mais caro da superfície.** Ele materializa as duas colunas
inteiras e cruza linha a linha, sem usar a estrutura de nenhuma das duas.

```python
v.group_sum("uf", "valor")     # {'SP': 200.0, 'RJ': 200.0}
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

## Como escolher a coluna

Em toda a superfície: `str` é **nome**, `int` é **posição**. A mesma regra do `schema=`
([ADR-0047](../adr/0047-schema-parametro-unico-de-spec.md)). Uma coluna *chamada* `"2"` é
achada pelo `str`; a posição 2, pelo `int`.

## O que o view não faz

**Não escreve.** Nenhuma operação altera o blob.

**Não é SQL.** Não há parser, joins, `OR`, `ORDER BY`, `LIMIT`, expressões calculadas ou
plano multi-tabela. O que existe são caminhos de consulta que lembram SQL.

**Não lê o que não é tabela.** Aninhado, ragged e campo opcional não são tabela
retangular, e a view recusa com uma mensagem que manda usar `decode()`. Vale um aviso: no
`#TCF.8H`, um `None` explícito marca a coluna como opcional, então
`encode([{"a": 1}, {"a": None}])` produz um blob que a view recusa, apesar de a coluna
existir em todas as linhas.

**Não lê formato legado.** `#TCF.6` e `#TCF.7` foram cortados
([ADR-0032](../adr/0032-tcf8-default-format.md)); para blobs antigos, `git checkout` de
uma versão anterior.

## O que a estrutura permitiria, e ainda não existe

Isto não é promessa de release, é o mapa do que foi medido como possível. O registro
completo, com o que foi **refutado**, está nos labs de 2026-08-24.

| oportunidade | onde | situação |
|---|---|---|
| `group_sum` pela estrutura do dicionário | cruzar os dois streams de índices sem materializar valor | medido em protótipo: 71,8% menos bytes |
| `sum`/`min`/`max`/`avg` sobre dicionário | somar os K únicos ponderados pela frequência | medido: 99,6% menos bytes; `min`/`max` são exatos por construção |
| responder "existe?" sem montar a lista de índices | exige um `Filtered` preguiçoso | não implementado |

E o que **não** é possível, por razão estrutural e não por falta de trabalho:

- **Resolver o valor de uma linha do corpo core sem replay.** Os ids de fragmento não
  viajam no wire; encoder e decoder mantêm contadores espelhados. Pular uma declaração
  devolve valor errado **sem erro**.
- **Prefiltrar por substring no corpo core.** O OBAT fragmenta o valor, então a forma
  escapada de um valor presente não é substring do corpo: dá falso negativo.
- **`min`/`max` no bit-pack denso.** O domínio é ordenado por primeira aparição, não por
  valor.

## Estabilidade

A superfície L1 a L4 (introspecção, agregadores, `where`, `select`) é **estável**.
`group_ranges` e `agg_by` são **experimentais** e podem evoluir no `.9`; os dois exigem a
tabela já ordenada por `sort_by` e levantam se ela não estiver.

## Conexões

- Referência de API: [`lazy-view.md`](lazy-view.md)
- Knobs do encode (`fallback`, `sort_by`): [`encode-knobs.md`](encode-knobs.md)
- Formato e modos: [`../algorithms/TCF-format.md`](../algorithms/TCF-format.md)
