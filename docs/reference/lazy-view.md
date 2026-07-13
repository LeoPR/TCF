# Reference — `tcf.view` (view lazy/consultável)

Referência da camada **read-only** [`tcf.view`](../../src/tcf/view.py): conecta a um blob
TCF multi-coluna e responde consultas (`count/sum/min/max/avg`, `where`, group-by)
**descomprimindo só o necessário**. Lê `#TCF.8M` (self-describing: natures revertidas
LAZY ao materializar a coluna + colunas anônimas posicionais); `#TCF.6` e `#TCF.7` não são
aceitos no pacote `0.8.0` (compatibilidade histórica via git);
**não muda encode/decode/formato**. Promovida do gadget `scripts/tcf_lazy/` (A4, plano 0.8).

```python
from tcf import encode, view

blob = encode({"cidade": ["SP", "SP", "RJ"], "valor": ["120", "80", "200"]})
v = view(blob)                       # conecta — NÃO descomprime nada
v.where("cidade", "SP").sum("valor") # toca só cidade + valor
```

> **Estabilidade**: a superfície L1–L4 (abaixo) é **estável**. `group_ranges`/`agg_by`
> (L5) são **experimentais** — podem evoluir no H-QUERY-04 (0.9). Marcado por método.

## Modelo

- **Lazy**: `view(blob)` só parseia o header (nome/modo/tamanho por coluna). Nenhum
  corpo é decodificado até uma query pedir aquela coluna; cada coluna é decodificada
  **no máximo uma vez** (cache interno).
- **Row-aligned por posição**: a i-ésima posição de cada coluna é a linha `i`.
  `where()` devolve os índices das linhas que casaram; agregação/`select` em **qualquer
  outra** coluna usam os mesmos índices. É assim que "a linha de uma coluna é a mesma
  linha na outra".
- **Contrato numérico** (`sum/min/max/avg`): **ignora** valores vazios (`""`); valor
  não-numérico levanta `ValueError` (intencional — não silencia dado sujo).
- **Só leitura**: nenhuma operação muda o blob.

## Consulta SQL-like, sem SQL

`view()` oferece caminhos de consulta que lembram uma execução SQL, mas não
interpreta uma string SQL nem tenta reproduzir todas as semânticas de um banco:

| capacidade | API | observação |
|---|---|---|
| projeção | `select(cols)` | materializa apenas as colunas pedidas |
| filtro | `where(col, value=...)` ou `where(col, pred=...)` | igualdade/predicado; encadeamento é AND |
| agregação | `count`, `sum`, `min`, `max`, `avg` | valores vazios são ignorados nos agregadores numéricos |
| agrupamento | `group_count(col)` | caminho estrutural em `@dict`; fallback nos demais modos |
| layout agrupado | `group_ranges`, `agg_by` | experimental; requer ordem contígua de `sort_by` |
| alinhamento | índices posicionais | a linha `i` de cada coluna é a mesma linha |

Não há parser SQL, joins, `OR`, `NULL` SQL, `ORDER BY`, `LIMIT`, expressões
calculadas ou plano multi-tabela. Uma coluna em modo `tcf` pode exigir
materialização completa porque suas referências são entrelaçadas; o relatório
`touched`/`materialized_bytes` deve ser usado para observar esse custo. A
evolução de `QueryPlan`/`execute()` e índices locais pertence ao trabalho
posterior de query, não ao formato `.8`.

## `view(blob) -> LazyTCF`  · estável

Conecta a um blob TCF multi-coluna. `ValueError` se o blob não for multi-coluna
(`#TCF.6 M` / `#TCF.7 M`).

## `LazyTCF` — introspecção (barata, só header) · estável

| membro | retorno | nota |
|---|---|---|
| `columns` | `list[str]` | nomes na ordem do header |
| `nrows` | `int` | nº de linhas pelo caminho mais curto (raw=conta `\n`, 0 decode; senão dict; senão coluna mais barata) |
| `column_bytes(name)` | `int` | tamanho do corpo **comprimido** da coluna (sem decodificar) |
| `total_bytes` | `int` | soma dos corpos |
| `materialized_bytes` | `int` | bytes já descomprimidos (corpos tocados) |
| `report()` | `dict` | `{total_bytes, materialized_bytes, pct, touched, n_cols}` — seletividade |

## `LazyTCF` — agregadores · estável

`idx` é interno (usado por `Filtered`); o uso normal é sem argumento ou via `where(...)`.

| método | retorno | contrato |
|---|---|---|
| `count(idx=None)` | `int` | nº de linhas (ou do filtro) |
| `sum(col, idx=None)` | `float` | soma; ignora vazios |
| `min(col, idx=None)` | `float` | mínimo; `ValueError` se sem numéricos |
| `max(col, idx=None)` | `float` | máximo; idem |
| `avg(col, idx=None)` | `float` | média; idem |
| `group_count(col)` | `dict[str,int]` | `{valor: n}` **sem expandir** a coluna quando ela é dicionário (`@`); senão fallback (decode + Counter) |

## `LazyTCF.where(col, value=None, *, pred=None) -> Filtered` · estável

Filtra por igualdade (`value`) ou predicado (`pred`), descomprimindo **só a coluna do
filtro**. Em coluna dicionário (`@`) varre o stream de índices sem decodificar os N
valores (avalia `value`/`pred` sobre os K únicos). Devolve [`Filtered`](#filtered).

## `LazyTCF.select(cols=None, idx=None) -> list[dict]` · estável

Linhas alinhadas como dicts; decodifica só as colunas pedidas (`cols=None` = todas).

## `Filtered` · estável

Resultado de `where()`. Opera só nas linhas que casaram (alinhadas).

| método | nota |
|---|---|
| `count()` | nº de linhas filtradas |
| `sum/min/max/avg(col)` | agrega `col` nas linhas filtradas |
| `select(cols=None)` | linhas filtradas como dicts |
| `where(col, value=None, *, pred=None)` | **encadeia** (AND): restringe os índices atuais |

```python
v.where("cidade", "SP").where("plano", "Premium").sum("valor")   # AND
```

## L5 — layout para baixa latência · **experimental**

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
v.report()                                 # {... 'pct': 55.6, 'touched': ['valor','cidade'], ...}
```

`report()['pct']` mostra a fração do blob materializada — a "venda" do lazy: a query
acima tocou ~56% (2 de 3 colunas) em vez de 100% que um `decode()` faria.

## Notas / limites

- **Coluna em modo `tcf`** (OBAT+HCC entrelaçados): `group_count`/agregação caem em
  **fallback** (decode da coluna inteira) — o ganho estrutural limpo vive em `@dict`/raw.
  Ligar `fallback=True` no `encode` (default 0.8) põe colunas low-card em `@dict`
  automaticamente, habilitando as queries sem expandir. Ver
  [encode-knobs.md](encode-knobs.md).
- `sort_by` (para L5) é **order-free** mas reordena as linhas — `decode` devolve a tabela
  na ordem do blob. Trade-off de compressão documentado em [encode-knobs.md](encode-knobs.md).
- Compat: `from tcf_lazy import view` (shim) ainda funciona, re-exportando daqui.

## Conexões

- Implementação: [`src/tcf/view.py`](../../src/tcf/view.py)
- Knobs do encode (`fallback`/`sort_by`): [encode-knobs.md](encode-knobs.md)
- Formato (modos `!`/`@`/`%`): [../algorithms/TCF-format.md](../algorithms/TCF-format.md)
- Design da expansão 0.9 (decode-DAG, índices): [`hquery01-decode-dag-indices-design.md`](../../experiments/lab/dirty/notas/hquery01-decode-dag-indices-design.md)
- Ticket: [T-DOC-LAZY-REFERENCE](../../tickets/T-DOC-LAZY-REFERENCE.md) · promoção: [T-CODE-LAZY-VIEW-PROMOTE](../../tickets/T-CODE-LAZY-VIEW-PROMOTE.md)
