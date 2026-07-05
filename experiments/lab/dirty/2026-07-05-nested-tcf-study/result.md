# Result — Nested-TCF study: como o TCF trata JSON aninhado, e dá pra um "TCF aninhado"? [probatório]

**Data**: 2026-07-05 · **Tipo**: [probatório] · FORK (não toca `src/tcf`) · owner pediu, antes de
fechar a [matriz de transmissão](../../../../datasets/coverage-matrix.md): estudar como o TCF lida
com o envio padrão (JSON de request/response, às vezes multi-camada / instrução aninhada) e se dá pra
ter um "TCF aninhado similar ao JSON". Harness `nested_bench.py` (mede bytes+RT) + `trace_experiment.py`
(trace OBAT/HCC). Saída bruta: `trace_output.txt`, `sample_nested_tcf.tcf.txt`. `py -3` + `tcf 0.7.1`
+ `brotli 1.2.0`. Rótulos SINTÉTICOS/anonimizados (`ASSET_SYN_*`, `cumulative_metric`).

## Dois sentidos de "aninhado" — não confundir

O TCF **já** faz nesting, mas em **nível de VALOR/afixo**: o HCC compõe strings por prefixo/sufixo
(`filho_de(no2=decl folha "Mar")+"ina"`), herança direta das provas M0
([old/.../2026-05-10-05-patricia-aninhado](../old/M0-fase-exploratoria-inicial/2026-05-10-05-patricia-aninhado/conclusoes.md),
`...06-aninhado-emails-urls`). Isso é o ancestral do `~` composicional de hoje.

O que o owner pede é **outro** nesting: de **DOCUMENTO** — a árvore de objetos/arrays do JSON
(`{a:{b:[{...},{...}]}}`). O TCF **não** tem isso: a API é estritamente tabular (`encode(list)` ou
`encode(dict[str,list[str]])`). Este study é sobre o nesting de documento.

## Tese (medida, não especulada)

**JSON aninhado = ESQUELETO escalar (config/instrução, pequeno) + ARRAYS-DE-OBJETOS (tabulares, onde
está o volume).** O array-de-objetos homogêneo **já é** a unidade nativa do TCF (dict de colunas). Logo
"TCF aninhado" não precisa de um formato novo de árvore — precisa de um **envelope** que preserve a
forma da árvore e **hoiste cada array-de-objetos para um bloco TCF**. O esqueleto (pequeno) fica JSON
inspecionável; o volume (grande) vira TCF (ainda textual, ainda com grupos visíveis — pilar 1).

## Três adaptadores nested↔TCF (lab, não toca `src/tcf`)

| adaptador | ideia | RT |
|---|---|---|
| **A · flatten_dotted** | achata toda folha → `(path, json_value)` → 1 tabela TCF 2-col. Arrays viram índice no path (`series.0.asset`). | `unflatten` (segmento só-dígito = índice) |
| **B · nested_tcf** ⟵ recomendado | "TCF aninhado": esqueleto JSON fino com placeholders `{"@tcf_block":k}` + 1 bloco TCF multi-col por array-de-objetos, com header `#BLOCK k col:type…`. | reinsere blocos decodados + re-tipa |
| **C · (comparação)** | raw JSON compacto + JSON-colunar (`{col:[...]}`) — os steelmen já do T1. | trivial |

## Medição — bytes brotli-q11 (RT=True em 24/24 células)

### REQUEST (upload): instrução multi-camada + array `series` (batch) — sweep n_assets
| n_assets | raw JSON | JSON-col | flatten-TCF | **nested-TCF** | nest %raw | nest %col |
|---|---|---|---|---|---|---|
| 3 | 204 | 228 | 281 | **263** | 128.9% | 115.4% |
| 20 | 242 | 258 | 437 | **273** | 112.8% | 105.8% |
| 100 | 385 | 346 | 829 | **280** | 72.7% | 80.9% |
| 500 | 1033 | 702 | 2218 | **283** | **27.4%** | **40.3%** |

O nested-TCF é **quase constante** (263→283B) enquanto o array cresce 3→500: `series` é totalmente
cadenciado (`ASSET_SYN_\00*\0*\1`) + colunas constantes (`*20|cumulative_metric`, `*20|unit_a`,
`*20|\1.\0`). **flatten explode** (281→2218B) porque a coluna `path` incha com os índices. Leitura:
o request só é caso do TCF quando carrega um **array grande homogêneo** (batch); config escalar pura
(<300B) → TCF perde.

### RESPONSE (download): envelope aninhado + array GRANDE cadenciado `forecast` — sweep n_pts
| n_pts | raw JSON | JSON-col | flatten-TCF | **nested-TCF** | nest %raw | nest %col |
|---|---|---|---|---|---|---|
| 24 | 258 | 259 | 412 | **294** | 114.0% | 113.5% |
| 168 | 703 | 588 | 1373 | **489** | 69.6% | 83.2% |
| 744 | 2022 | 1377 | 5386 | **990** | **49.0%** | **71.9%** |

O envelope custa ~86B sobre o TCF puro (904B no T1) e ainda entrega **−28% vs o steelman JSON-colunar**
em 744 pts. `<300B` (24 pts) empata/perde — coerente com "upload/payload pequeno TCF não ajuda".

## Design recomendado — B (envelope-with-tcf-blocks)

Worked example (response, 24 pts), do `sample_nested_tcf.tcf.txt`:
```
{"ASSET_SYN_01":{"cumulative_metric":{"-":{"projectable":true,
 "messages":["ok","cumulative","gap.variable"],"forecast":{"@tcf_block":0}}}}}
<SEP>
#BLOCK 0 ds:str yhat:num
#TCF.7 M
%109=ds,!yhat
16
*24|\2026 / *24|\07 / *24|\05 / *24+1|\00 / *11|\37 / *12|\38   ← cadência do ds
53.0 / 113.4 / 181.2 / ...                                       ← yhat raw
```
- **RT**: parse do esqueleto → cada `{"@tcf_block":k}` vira o bloco `k` decodado (list-of-dicts,
  re-tipado pelo header `col:type`). Preserva a forma da árvore.
- **Explicabilidade (pilar 1)**: o esqueleto fica JSON legível; o bloco é TCF textual com grupos
  visíveis (`*24|…` mostra a cadência sem descomprimir). Não vira sopa opaca.
- **Cons honestos** (a corrigir num protótipo formal, se avançar): chaves com `.` no path (flatten);
  `null` vs ausente vs `""` ambíguo no bloco; ordem de chaves do objeto; arrays vazios; tipos mistos
  numa coluna; `<SEP>` (RS `\x1e`) precisa não ocorrer no conteúdo. Nenhum ocorre nas formas medidas;
  todos são bordas conhecidas.

## Trace OBAT/HCC (o "experimento de sempre" — `trace_output.txt`)

**forecast-block** (download-cadenced): `ds` cadence=`1-uniform-length-high-lcp-lcs`, `seq_rle_runs=3`,
HCC substitui a sub-tupla `\07 \05` em 9 linhas (Iter 1 PICK net=16); `yhat` cadence numérica, sem
composição (raw). **series-block** (upload-batch): `asset` `seq_rle_runs=2` (`1,2 R=8` PICK); `variable`/
`unit`/`weight` = primeira-string-literal + `*20|` (constante). O trace mostra a máquina escolhendo
seq-RLE onde há cadência e caindo em literal/raw onde não há.

## Pesquisa — formas reais de payload aninhado (survey web, 4 lentes)

Workflow `nested-tcf-study` (21 agentes: 4 lentes web + 4 designs × 3 juízes + síntese). As citações são
de survey web (a checar por amostragem); os **bytes** são medidos localmente (acima). Achados:

**Lente A — REQUEST (upload).** O request "normal" é **config escalar aninhado, pequeno (<1KB),
heterogêneo** — árvore de operadores/opções, cada nó único. Ex.: Elasticsearch query DSL
(`{query:{bool:{must:[…],filter:[…]}}}`), GraphQL `variables`, JSON-RPC `params`, `options/settings/
filters` de create/update REST (Stripe `metadata` cap 50 chaves). **Sem array homogêneo → TCF neutro.**
A exceção é **batch/bulk**: `{records:[{col_a,col_b,col_c},…]}` (bulk-create), DynamoDB `BatchWriteItem`
(cap 25 itens/16MB), JSON-RPC batch, LLM JSONL (até 50k linhas). Mas: os grandes **já chegam como
NDJSON/JSONL** (o concorrente que o TCF já bate no T1), e os JSON puros são capados pequenos. → o upload
só é caso do TCF no nicho **batch homogêneo achatado**, minoria dos endpoints.

**Lente B — RESPONSE (download): o alvo.** O formato que carrega volume é um **envelope fino (<1KB:
`meta/links/took/_shards`) embrulhando UM array grande homogêneo**. Nomes convencionais por ecossistema:
`data` (JSON:API, Stripe list), `value` (OData v4), `results/rows/items` (REST/SQL), `hits.hits[]._source`
(Elasticsearch), `edges[].node` (GraphQL Relay), `features` (GeoJSON), **`result[].values` a passo fixo
(Prometheus `query_range`, CloudWatch `GetMetricData` — SÉRIE cadenciada)**. É exatamente a forma que o
`nested_tcf` ataca. O padrão da indústria pra nested→tabular converge em 3 passos: (1) localizar o
caminho repetido, (2) UNNEST/explode = 1 linha/elemento, (3) path-flatten dos escalares.

**Lente C — como os formatos colunares fazem (a validação teórica).** Todo sistema colunar maduro usa o
**"shred + reassemble" do Dremel** (Parquet/BigQuery): as folhas viram **colunas primitivas planas** e a
**topologia da árvore vai pra um side-channel compacto** (repetition+definition levels) **separado dos
valores**. Assimetria universal: STRUCT (1:1) = rename de coluna barato; ARRAY/REPEATED (1:many) = o caso
duro. **O design B é o mesmo princípio em nível de documento**: o **envelope é o side-channel de topologia**;
o **bloco TCF são as colunas shredded**. Não é invenção nova — é Dremel aplicado ao envelope textual.

**Lente D — endereçamento de path (para RT).** Famílias: path-como-coluna (dotted `a.b.c`, bracket
`a[0].b`, **JSON Pointer `/a/b/0` RFC 6901** com escapes `~0`/`~1`, JSONPath RFC 9535) vs normalizar-para-
sub-tabela (explode/`record_path`) vs level-encoding Dremel (reconstrói sem nomear por path). **Lição para
os cons do flatten**: JSON Pointer (RFC 6901) resolve chaves com `.`/`/` via escapes — a rota robusta se
o flatten fosse necessário (não é: perde pro envelope).

### Design panel — ranking (juízes: bytes · round-trip · explicabilidade)

| abordagem | avg | nota |
|---|---|---|
| **envelope-with-tcf-blocks** (= `nested_tcf` medido) | **8.0** | esqueleto JSON literal (RT nativo + inspecionável) + bloco TCF só no array homogêneo/cadenciado |
| path-value-plus-subtables | 7.3 | mesma hoistagem, mas achata escalares do envelope em (path,val) — perde a inspeção da árvore |
| json-columnar-hybrid (steelman T1) | 7.0 | chaves uma vez, colunas TCF; RT seguro, mas não modela cadência tão bem |
| dotted-flatten-single | 5.3 | universal/sem-schema, mas **explode em arrays** (confirmado: 5386B/744pts) |

O ranking do panel **coincide com a medição**: o recomendado (envelope-with-tcf-blocks) é o `nested_tcf`
que venceu no bench; o pior (dotted-flatten) é o `flatten` que explodiu.

### Open questions (do synth — pra um protótipo formal, se avançar)

Fidelidade de tipo (number/bool/null/string) sem inflar — type-tag inline vs sidecar · sintaxe inequívoca
de delimitação/placeholder dos blocos · múltiplos blocos / `included[]` do JSON:API / N séries em
`result[]` · **break-even por tamanho do array** (a partir de quantos itens o bloco vale o header) · ruído
anti-TCF no mesmo payload (cursores base64, `_score`/`_id`/ETag aleatórios, `geometry.coordinates`, hashes)
→ manter no envelope, fora do bloco · schema NÃO-uniforme (campos opcionais, unions) · medição
end-to-end do envelope completo (parcialmente feita aqui — o `nested_tcf` mede o envelope inteiro).

## Posicionamento (sóbrio)

> JSON aninhado não é, por si, inimigo do TCF: um payload aninhado é **esqueleto escalar + arrays**.
> O TCF ajuda quando o nesting **embrulha um array grande homogêneo** (batch no request, série/tabela
> no response) — aí um "**TCF aninhado**" = envelope JSON fino + bloco TCF por array vence o JSON-colunar
> em dados **cadenciados** (−28% em 744 pts) e em **batch** (n=500: 27% do raw), mantendo o texto
> inspecionável. NÃO ajuda quando o payload é **config escalar pequeno** (<300B: TCF 169B > raw-JSON
> 140B) — aí o envelope é overhead. O `flatten` ingênuo (path indexado) **explode** em arrays e não deve
> ser a rota.

## Checklist anti-incidente (5 perguntas, CLAUDE.md)

1. **Real-world?** Parcial — formas ecológicas (request/response reais de forecast) mas com dados
   sintéticos/anonimizados. **Viés declarado**: cadência é TCF-favorável por construção.
2. **N≥5 fontes?** Não — é um study de FORMA (feasibility + design), não gate empírico. As formas vêm
   do survey web (4 lentes) + T1. Gate real fica pros decorrentes G2/G3 (dados reais).
3. **Sintético vs real?** Sintético declarado; espelha a forma medida no T1 (forecast real anonimizado).
4. **Viés declarado?** Sim.
5. **Bytes ≥5%?** Sim onde há array (batch/cadenced: 28–73%); ~0/negativo em config pequeno (declarado).

**Status**: feasibility de "TCF aninhado" **confirmada-conceitual** (design B mede + RT + explicável).
A vitória em bytes herda o veredito do T1 (robusta em cadenced/batch; ausente em small/high-card). NÃO
é proposta de mudar `src/tcf` — é um adaptador de envelope externo (gadget), coerente com a filosofia.

## Cross-links

[Matriz de transmissão](../../../../datasets/coverage-matrix.md) ·
[T1](../2026-07-05-t1-ndjson-brotli/result.md) ·
[nota transmissão](../notas/transmissao-api-onde-tcf-importa.md) ·
[assessment cobertura](../notas/2026-07-05-cobertura-datasets-shaper-assessment.md) ·
M0 affix-nesting: [patricia-aninhado](../old/M0-fase-exploratoria-inicial/2026-05-10-05-patricia-aninhado/conclusoes.md).
