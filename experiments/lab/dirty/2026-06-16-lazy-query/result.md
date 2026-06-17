# Result — Lazy/queryable view (H-QUERY-01) [probatório]

**Data**: 2026-06-16 · **Tipo**: [probatório] · FORK (NÃO toca src/tcf; gadget que lê o blob).

A "venda" do TCF: **descomprimir só o suficiente pra responder**. Em etapas segmentadas.

## L1 — column pruning + agregadores (PoC)
`lazy_query_poc.py` — `LazyTCF(blob)` conecta sem descomprimir; fatia o corpo por coluna
(header diz nome/modo/tamanho) e decodifica **sob demanda** (cache + tracking `touched`).
Agregadores: `count / sum / min / max / avg` + `where` (filtro). Reusa os decoders core
(byte-exato). `where('cidade','SP').sum('valor')` toca só `cidade`+`valor`. RT lossless.

## L2 — quantificar a venda (memória/latência)
`lazy_query_dimensions.py` — online-retail real, 5000 linhas x 8 colunas, blob = 103 264 B.
Quanto do blob cada query precisa **materializar** (descomprimir):

| query | resposta | materializou | colunas |
|---|---:|---:|---|
| `count()` | 5000 | **0,2%** | Country (a mais barata) |
| `sum('Quantity')` | 45929 | **5,2%** | Quantity |
| `where(CustomerID=X).sum('Quantity')` — *qtd comprada pelo usuário* | 1733 | **7,9%** | CustomerID, Quantity |
| `where(CustomerID=X).count()` — *pedidos do usuário* | 297 | **2,7%** | CustomerID |
| `where(Country='France').sum('Quantity')` | 449 | **5,4%** | Country, Quantity |

vs `decode()` completo = **100%** (8 colunas). Responder "quantos itens o usuário X comprou"
toca **7,9%** do blob — o resto fica comprimido. Um compressor binário descomprimiria 100%
antes de qualquer conta. **Memória e latência baixas** caem direto da estrutura do TCF.

## L3 — contar/agrupar sem expandir (FEITO, via dict/raw)
Promovido no gadget `scripts/tcf_lazy/` (`nrows` estrutural + `group_count`).
- **dict (`@`)**: `count` = tamanho do stream de índices; `group_count` = tally do stream +
  decode só da tabelinha de únicos (K valores). **Sem expandir as N linhas.** Verificado vs
  decode completo (adult/receita). Ex.: `group_count('education')` em 5000 linhas materializa
  **5,0%** do blob; `nrows` idem (não constrói a lista de 5000).
- **raw**: `count` = nº de `\n` (sem decode de valores).
- **ACHADO honesto (verificado 2026-06-16)**: agregar os runs `*N|` **direto no modo-tcf NÃO é
  barato/separável** — OBAT+HCC entrelaçam o valor com refs de outras linhas. O invariante de
  contagem (Σ multiplicidades == nº de linhas) **falhou** em colunas tipo-ID (InvoiceNo,
  l_orderkey), e **0** colunas tcf eram "clean-numeric". Por isso o L3 usa a estrutura do
  **dicionário/raw**, não o parse de `*N|` do tcf. tcf/split caem em fallback (decode + Counter).

## L4 — filtro pelo índice do dicionário (FEITO)
`where(col, value/pred)` sobre coluna `@`: acha o(s) id(s) na tabelinha de únicos (avalia
value/pred sobre os K únicos) e **varre só o stream** comparando id — sem decodificar os N
valores. Encadeado (AND) lê só as posições já filtradas. Non-dict: fallback (decode + filtro).
Verificado: índices idênticos ao filtro via decode completo. Ex.: `where(workclass='Private')`
em 5000 linhas (3420 casam) materializa **5,0%** do blob e NÃO coloca a coluna no cache.

## L5 — layout p/ baixa latência (FEITO)
`encode(table, sort_by=key)` agrupa as linhas (a chave vira runs `*N|` contíguos) →
`group_ranges(key)` dá `{valor: (início, fim)}` e `agg_by(key, col, op)` faz **group-by por
slice** (cada grupo = um intervalo; a coluna agregada é decodificada uma vez). É o **"qtd por
usuário"**: `agg_by("CustomerID", "Quantity", "sum")` em online-retail (3795 linhas, 197 users)
== group-by manual (verificado).

**Trade-off de compressão (honesto, medido)**: ordenar pela chave **ajuda** onde ela correlaciona
com a estrutura geral (adult `sort_by=education`: **90,0%**, −10%) e **pode piorar** onde outras
colunas estavam melhor ordenadas (online-retail `sort_by=CustomerID`: **102,3%**, +2,3% — desarruma
InvoiceDate/InvoiceNo). O ganho de **query** (grupos contíguos → slices, baixa latência) é sempre
presente; a compressão da transmissão é dataset/chave-dependente. `sort_by` é order-free.

## Etapas seguintes
- Otimizações finas (saltos dedutivos / binary-search nos runs ordenados; dicas no header).
  **Funcional já fechado: L1-L5.**

## É uma versão de formato?
- **Lazy-view (`view()`)**: **NÃO**. Lê o `#TCF.7` existente; é gadget/tooling. Pode evoluir
  sem bump de formato.
- **Layout L5 via `sort_by`**: **NÃO** (order-free, já welded). Vira versão só se for um **modo
  de layout novo** no formato.

## Artefatos
- `lazy_query_poc.py` (L1, runnable, RT lossless) · `lazy_query_dimensions.py` (L2, medição real).
