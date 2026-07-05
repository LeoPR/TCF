# Transmissão de dados por API — onde o TCF faz diferença (guia de argumentação) [referência]

**Data**: 2026-06-21 · guia honesto (pesquisa de literatura + práticas de big techs). Responde:
*"qual o formato comum/recomendado pra transmitir dados, e em que situações o TCF realmente faz
diferença prática?"* — pra focar utilidade e virar cenários de teste. **Sóbrio, sem inflar o nicho.**
Fonte: workflow `tcf-transmissao-api-guia` (3 lentes web + síntese). Cross-links no fim.

## Estado da prática (o que se usa hoje)

Do menor ao maior payload:
1. **Maioria absoluta**: **JSON pequeno** sobre HTTP, **paginado** (20-100 itens/página — GitHub 30/100;
   Google AIP-132/158), **comprimido automaticamente** pela camada HTTP (gzip universal; brotli ~96%,
   +15-25% sobre gzip) via `Accept-Encoding`/`Content-Encoding` (RFC 7231/9110). Threshold típico de
   compressão: **>1KB** (abaixo, a moldura supera o ganho).
2. **Redução de payload é resolvida no SCHEMA, antes do formato**: field masks / partial responses
   (Google AIP-161/157, Netflix), thin events (Stripe v2, **−90%**).
3. **Bulk/export em escala (>10k registros) muda o formato deliberadamente**: Salesforce/Oracle Bulk
   API = **CSV ou NDJSON**; data warehouses (BigQuery/Snowflake/Redshift) = **Parquet** (5-10× menor
   que CSV, colunar, predicate pushdown). **NDJSON** domina streaming/bulk textual (parse incremental,
   O(1) memória).
4. **Interno/RPC**: binário (**Protobuf+gRPC**, ~2-3× menor, ~6× mais rápido — valor real é
   schema+codegen, não bytes). APIs públicas ficam em JSON por ergonomia/debug.

> **Não há demanda difundida por um meio-termo "textual + comprimido colunar + consultável".** É aí
> que o TCF tenta existir — um nicho, não o mainstream.

## Onde o TCF FAZ diferença (o nicho, ~5-15% dos casos — estimativa)

Cada um com a **condição precisa** e a medição que temos:
- **Batch/export TABULAR em escala, como pré-processo antes do brotli.** Condição: tabular,
  repetitivo (domínios/códigos/máscaras), **>~1-3k linhas**, **≥~8 colunas**, baixa cardinalidade.
  Medido: TCF-0.7+brotli **<** CSV+brotli — Adult **−28%**, lineitem ~−20% ([staged-brotli](../old/refuted/2026-06-16-staged-and-ordering-brotli/result.md)).
- **Consulta seletiva sem descomprimir tudo (lazy).** Condição: o consumidor quer agregados/filtros
  sobre poucas colunas, não o dataset inteiro. Medido: query toca **0,2-7,9%** do blob vs 100% no
  decode ([lazy-query](../old/welded/2026-06-16-lazy-query/result.md) + [A1 testbank](../2026-06-19-lazy-testbank/result.md): adult 10%, tpch 14%).
- **Compressão colunar + texto inspecionável ANTES da transmissão** (storage/dev/pipeline que lê sem
  materializar). Condição: a inspecionabilidade é consumida **onde o brotli ainda não rodou** —
  pós-brotli o blob é opaco como qualquer outro. Diferença vs Parquet: TCF é texto + grupos visíveis.
- **Layout p/ baixa latência de group-by** (`sort_by`): ganho de query sempre presente; compressão
  dataset/chave-dependente (adult −10%; online-retail +2,3%).

## Onde o TCF NÃO ajuda (a maioria — honesto)

- **Payload pequeno (<~1KB, páginas de 20-100)** — o caso da maioria das REST. Medido: cadastro 244B,
  CSV+brotli **162B vence** TCF+brotli 185B.
- **Quando o gargalo é resolvido no schema** (field masks, thin events) — TCF é ortogonal e chega tarde.
- **JSON+gzip/brotli já resolve 70-90%** — o incremento do TCF só existe na margem >90% (dado muito estruturado).
- **Dados não-tabulares / aninhados / high-entropy** (hashes, IDs aleatórios, free-text único) — sem
  redundância estrutural, TCF iguala ou piora.
- **Analytics em escala** — Parquet/Arrow ganham (ratio, predicate pushdown, Arrow Flight 2-3GB/s).
- **Streaming incremental** — NDJSON/SSE já resolvem (textuais, padrão).
- **RPC/contrato de schema** — Protobuf/gRPC (codegen/type-safety) — eixo que o TCF não endereça.
- **Drop-in de JSON em REST** — trocar formato é breaking change.

## TCF vs alternativas (resumo)

| vs | veredito |
|---|---|
| **gzip/brotli/zstd** | NÃO compete — **complementar** (pré-processo textual). Brotli sozinho basta na maioria. |
| **Parquet/Arrow** | Perde em tamanho e throughput. Nicho só em "textual+inspecionável+consultável sem tooling binário". |
| **Protobuf/gRPC** | Eixo diferente (schema/codegen). TCF fica "perto do JSON" (textual); Protobuf é opaco/rápido. |
| **NDJSON** | **O concorrente mais direto** (textual + queryable + compressível) e é **padrão**. **MEDIDO 2026-07-05 (T1)**: TCF+brotli **vence NDJSON+brotli em 24/24** (real, 6 datasets), **20–28% menos bytes**. Mas vs **JSON-colunar** (`{col:[...]}`, steelman) a vantagem é estrutura-dependente (ver §"teste decisivo"). |

## Perfil DUPLO: upload vs download (2026-07-05)

APIs têm **duas direções** com economia distinta:
- **Upload** (request, cliente→servidor): foco em economia de ENVIO; tipicamente **pequeno**
  (query/params). Ex. `/forecast` request ~250B — **TCF não ajuda** (<1KB, moldura > ganho).
- **Download** (response, servidor→cliente): **onde está o VOLUME**. Ex. `/forecast` response =
  array de `{"ds":<timestamp>,"yhat":<float>}` (horizon 1m ≈ 744 pontos). **É o foco de volume e o
  nicho do TCF.**

A direção **download** é o alvo melhor: paginação/bulk/export/séries-temporais são respostas
grandes. E respostas **cadenciadas/sequenciais** (timestamps, IDs) são onde o TCF bate até o
steelman JSON — a cadência vira RLE+delta que nenhum layout JSON captura.

## O teste decisivo — MEDIDO (2026-07-05, T1)

Era: toda evidência de "TCF ganha" era vs **CSV+brotli**; faltava vs **NDJSON+brotli** (padrão
BigQuery/Elasticsearch/X API). Medido em [2026-07-05-t1-ndjson-brotli](../2026-07-05-t1-ndjson-brotli/result.md)
(6 datasets reais × 4 scales, RT 24/24, brotli q11+q5+gzip):

- **vs NDJSON+brotli**: TCF **vence 24/24**, weighted **72–80%** (−20–28%). Consistente gzip+q5.
  Confiança **Alta**. → o gate fecha **a favor do TCF**.
- **vs JSON-colunar+brotli** (steelman: chaves uma vez): vitória **marginal e dataset-dependente**
  (TCF perde em 10/24 — pessoas/ibge/online-retail em scales baixos; vence forte em adult low-card
  largo e em cadenciado). NÃO se claima "TCF vence JSON+brotli" em geral.
- **Download cadenciado** (forecast): TCF **−29%** vs JSON-colunar em 744 pontos (RLE da cadência).

Leitura honesta: o TCF vence o concorrente textual REAL (NDJSON), e vence o JSON mais compacto
possível só onde há **estrutura** (categórico largo ou cadência). Não é vitória universal sobre JSON.

## Cenários de teste pro progresso (registrar/medir)

- **T1 (decisivo)** — TCF+brotli **vs NDJSON+brotli** (+CSV+brotli + JSON-array como teto), 4 datasets
  reais (Adult 3k, Online-Retail 5k, Receita-CNPJ, lineitem). Tabela de bytes pós-brotli + % vs cada.
- **T2** — curva de break-even por volume: n_linhas ∈ {50,100,500,1k,3k,10k,50k} → a partir de quantas
  linhas TCF passa a vencer (validar ">~1-3k").
- **T3** — sensibilidade à cardinalidade (1/10/50/100% únicos, n fixo) → ponto onde TCF deixa de ganhar.
- **T4** — lazy vs descompressão total: bytes-tocados **E latência** de count/sum/where.agg via Lazy
  vs decode TCF completo vs Parquet pushdown vs NDJSON varrendo tudo.
- **T5** — custo de CPU do pré-processo (encode TCF+brotli vs CSV/NDJSON→brotli, níveis brotli 5/9/11).
- **T6** — limite de resposta (cap 6MB Lambda / 10MB API GW): linhas-por-resposta JSON+gzip vs
  TCF+brotli vs Parquet.

## Posicionamento (a frase-guia)

> *Para a maioria das APIs (JSON pequeno, paginado, gzip/brotli automático), o TCF **não faz
> diferença** — o formato comum já resolve. O TCF tem utilidade prática num **nicho pequeno (~5-15%)**,
> na direção **download** (response, onde está o volume): endpoints de batch/export/séries com dados
> **tabulares, grandes (>~1k linhas)**, onde atua como **pré-processo textual antes do brotli**.
> Contra o padrão real **NDJSON+brotli**, entrega **20–28% menos bytes** (medido T1, 6 datasets, não
> só vs CSV). Contra o JSON mais compacto (colunar), a vantagem é **estrutura-dependente**: robusta em
> categórico largo e — sobretudo — em payloads **cadenciados/sequenciais** (séries/forecast: −29% vs
> JSON-colunar via RLE+delta da cadência); marginal/negativa em high-card de poucas colunas. E/ou
> onde se quer **consultar/agregar sem descomprimir tudo** (query toca 0,2-7,9% do blob), mantendo
> output textual e inspecionável. Upload pequeno (<1KB) e alta entropia ficam fora. **Gate T1
> fechado** (2026-07-05): a tese de transmissão vs NDJSON se sustenta; vs JSON-colunar é localizada.*

## Fontes

RFC 7231/9110; Google AIP-132/157/158/161/231; Netflix TechBlog (FieldMask); Stripe/Hookdeck (thin
events); Salesforce/Oracle Bulk API; GitHub pagination; AWS API Gateway/Lambda; Paul Calvano
(gzip/brotli/zstd 2024); Auth0/buf.build (Protobuf); NDJSON spec / X API v2 / BigQuery/Elasticsearch
bulk; Apache Parquet/Arrow Flight; DuckDB 2024. Internos: [README §Resultados](../../../../README.md),
[staged-brotli](../old/refuted/2026-06-16-staged-and-ordering-brotli/result.md), [lazy-query](../old/welded/2026-06-16-lazy-query/result.md),
[divulgação](../../../../docs/divulgacao-tcf.md).
