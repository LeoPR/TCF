# tcf_lazy — view lazy/consultável sobre um blob TCF

Gadget **auxiliar** (não faz parte do TCF-CORE; lê o `#TCF.7` existente, **não toca `src/tcf`**).
Promovido do PoC `experiments/lab/dirty/2026-06-16-lazy-query/`.

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
  `.indices`, e `.where(...)` encadeado AND).
- `select(cols=None, idx=None)` → linhas alinhadas (decodifica só as colunas pedidas).

**Alinhamento de linha**: row-aligned por posição (a i-ésima posição de cada coluna é a linha `i`).
`where()` devolve os índices; agregação/`select` em outra coluna usam os MESMOS índices.

## Estado
Funcional (filtro + agregação + alinhamento). `tests/test_tcf_lazy.py` (13 testes).
Otimizações futuras (agregar runs `*N|` sem expandir, índice de dicionário, layout p/ baixa
latência, dicas no header) são hooks documentados em `lazy.py` — **funcional primeiro, otimizado depois**.

**Não é versão de formato**: lê o `#TCF.7` atual. Pode evoluir sem bump.
