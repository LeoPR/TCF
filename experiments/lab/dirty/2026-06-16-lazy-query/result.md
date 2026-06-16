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

## Etapas seguintes (segmentadas, baratas)
- **L3** — agregar **runs** (`*N|`, `*N+delta|`) lendo o marcador, sem expandir a coluna
  (descomprime ainda menos; usa a explicabilidade do formato).
- **L4** — filtro assistido por índice: coluna dicionário (`@`) dá pertinência de grupo sem
  decodificar todos os valores.
- **L5** — **layout p/ baixa latência**: organizar/encodar de modo que uma query-alvo
  (ex.: "qtd por usuário") seja respondida tocando o mínimo (ordenar/agrupar pela chave) —
  mantendo a compressão da transmissão. Dimensões: memória, velocidade, latência, compressão.

## É uma versão de formato?
- **Lazy-view (`view()`)**: **NÃO**. Lê o `#TCF.7` existente; é gadget/tooling. Pode evoluir
  sem bump de formato.
- **Layout L5 via `sort_by`**: **NÃO** (order-free, já welded). Vira versão só se for um **modo
  de layout novo** no formato.

## Artefatos
- `lazy_query_poc.py` (L1, runnable, RT lossless) · `lazy_query_dimensions.py` (L2, medição real).
