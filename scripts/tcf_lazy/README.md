# tcf_lazy — view lazy/consultável sobre um blob TCF

> **MOVIDO (A4, plano 0.8)**: a implementação agora é a camada read-only do core em
> [`src/tcf/view.py`](../../src/tcf/view.py). Caminho canônico: **`from tcf import view`** (vai no
> wheel). Esta pasta virou **shim de compat** (`from tcf_lazy import view` ainda funciona).

Camada **read-only** do TCF (lê o `#TCF.8M` existente; **não muda encode/decode/formato**).
PoC de origem: `experiments/lab/dirty/old/welded/2026-06-16-lazy-query/`.

A "venda" do TCF: **descomprimir só o suficiente pra responder**. O header já diz nome / modo /
tamanho de cada coluna → dá pra fatiar o corpo por coluna sem decodificar nada, e só descomprimir
a(s) coluna(s) — e, no filtro, só as linhas — que a pergunta precisa.

```python
from tcf import encode
from tcf_lazy import view                      # (scripts/ no sys.path)

v = view(encode(table))                        # conecta, NÃO descomprime
v.count()                                      # toca a coluna mais barata
v.sum("valor")                                 # toca só 'valor'
v.where("cidade", "Sao Paulo").sum("valor")    # toca só 'cidade' + 'valor'
v.where("cidade", "SP").where("plano", "Premium").count()   # filtro encadeado (AND)
v.report()                                     # {materialized_bytes, total_bytes, pct, touched, n_cols}
```

## API
- `view(blob) -> LazyTCF` — conecta sem descomprimir.
- `.columns`, `.nrows`, `.column_bytes(name)`, `.total_bytes`, `.materialized_bytes`, `.report()`.
- Agregadores: `count`, `sum`, `min`, `max`, `avg` (numérico: ignora vazios, erra em não-numérico).
- `where(col, value=...)` ou `where(col, pred=callable)` → `Filtered` (`.count/.sum/.min/.max/.avg/.select`,
  `.indices`, e `.where(...)` encadeado AND). **L4**: em coluna `@` o filtro varre só o stream de
  índices (compara id; value/pred avaliados sobre os K únicos) — sem decodar os N valores.
- `select(cols=None, idx=None)` → linhas alinhadas (decodifica só as colunas pedidas).
- **L3 — sem expandir**: `.nrows` (estrutural: dict = tamanho do stream, raw = nº de `\n`) e
  `group_count(col)` (`{valor: n}`; em coluna `@` dicionário, tallia o stream + só a tabelinha
  de únicos — não expande as N linhas; demais modos: fallback decode+Counter).
- **L5 — layout p/ query**: `group_ranges(key)` → `{valor: (início, fim)}` e `agg_by(key, col, op)`
  → group-by por slice (o "qtd por usuário": `agg_by("user", "qtd", "sum")`). Requer um blob
  agrupado: `encode(table, sort_by=key)` (order-free). A compressão do layout é trade-off
  (ajuda onde a chave correlaciona com a estrutura; pode piorar onde outras colunas estavam
  melhor ordenadas) — o ganho de **latência da query** é sempre presente.

**Alinhamento de linha**: row-aligned por posição (a i-ésima posição de cada coluna é a linha `i`).
`where()` devolve os índices; agregação/`select` em outra coluna usam os MESMOS índices.

## Estado
**Funcional L1–L5** (filtro + agregação + alinhamento + contar/agrupar sem expandir + filtro
pelo índice do dicionário + group-by por layout ordenado). `tests/test_tcf_lazy.py` (27 testes).
**Achado L3 (verificado)**: agregar `*N|` direto no modo-tcf não é separável (OBAT+HCC entrelaçam
valor com refs) — o ganho estrutural limpo vive no dicionário (`@`)/raw. **L5 trade-off**: o layout
ordenado ajuda/atrapalha a compressão conforme o dataset/chave; o ganho de latência da query é
sempre presente. Otimizações finas (binary-search nos runs, dicas no header) ficam como hooks
em `lazy.py`. **Não é versão de formato** (lê `#TCF.8M`).

**Não é versão de formato**: lê o `#TCF.8M` atual. Pode evoluir sem bump.
