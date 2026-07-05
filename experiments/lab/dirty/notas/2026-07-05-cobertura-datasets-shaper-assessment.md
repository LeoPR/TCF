# Assessment — datasets agrupados consistentemente + shaper dimensiona todas as direções? [probatório]

**Data**: 2026-07-05 · **Tipo**: [probatório] · Auditoria pré-benchmark (owner pediu: antes de novos
benchmarks, ver se os datasets estão agrupados consistentemente pros cenários de transmissão e se o
shaper dimensiona em todas as direções). Método: workflow `dataset-shaper-coverage-audit` (4 lentes
paralelas — tickets, cobertura de datasets, capacidade do shaper, taxonomia-alvo — + síntese),
cruzado com leitura direta de `tickets/`, `datasets/`, `scripts/shaper/`, memória coverage-map.
Insumo: [T1](../2026-07-05-t1-ndjson-brotli/result.md).

> Nota de método: o repasse por-lente teve um mismatch de chave (filtro `.lens`); o agregado (35
> gaps) passou e a síntese foi reconstruída relendo o repo. Onde não se achou cobertura, diz-se
> "ausente" — sem preencher com suposição.

## VEREDITO 1 — datasets agrupados de forma consistente? **PARCIAL**

Existe **um** esquema, mas num eixo só: a **taxonomia por `data_shape`** (design 2026-06-01, memória
`project-dataset-coverage-map`): categorical low/high-card, integer keys/counts, float
scientific/monetary, date/datetime/time-series, free-text curto, hierárquico (ibge), check-digit ID
(br-identidades). Descreve **o que o dado É**, não **como ele TRANSITA** nem **em que volume**.

Problemas para o objetivo de transmissão:
1. **Falta o eixo que o T1 tornou load-bearing** — forma de transmissão (upload <1KB → TCF não
   ajuda; download bulk → vence NDJSON; download **cadenciado** → vence até o steelman JSON-colunar).
   Nenhum dataset está *rotulado* por isso; a distinção só existe em prosa na nota de transmissão.
2. **Falta eixo de volume-tier** — 1k/3k/5k/10k do T1 são sweep de benchmark, não agrupamento. Sem
   tier declarado (µ / página 20-100 / batch >1k / bulk >10k / >1M).
3. **Dois esquemas desconectados** — `datasets/synthetic/` (D1-D17, por tipo, single-col, 12-20
   linhas) e `datasets/canonical/` (por `data_shape`, real, em Z:) não compartilham vocabulário.

**Esquema proposto (3 eixos ortogonais)** — reconcilia as duas taxonomias:

| Eixo | Valores | Origem |
|---|---|---|
| **tipo/forma-de-dados** | classes `data_shape` já existentes | coverage-map (reusar) |
| **volume-tier** | `µ`(<1KB/20-100) · `S`(~1k) · `M`(3-10k) · `L`(10-100k) · `XL`(>1M) | novo |
| **forma-de-transmissão** | `upload-small` · `download-bulk` · `download-cadenced` · `lazy-query` | novo (T1 + nota) |

Ação que converte PARCIAL→SIM (ou expõe o gap): matriz colocando cada canônico + D1-D17 numa célula
`(tipo × tier × forma-tx)`; células vazias = gaps. → ticket **T-DATA-TRANSMISSION-GROUPING**.

## VEREDITO 2 — shaper dimensiona "todas as direções"? **PARCIAL (2 de 4 eixos)**

O shaper (`scripts/shaper/`) é um **subsetter** de hubs canônicos: fatia o que já existe, **não
sintetiza**. Forte em *quantidade*, cego em *natureza*.

| Eixo | Cobre hoje? | Evidência |
|---|---|---|
| **tipo de dados** | **AUSENTE** — sem campo `type` em `ShapeRequest`; só devolve colunas já no hub; schema opera em nível de TABELA (nem projeção de coluna). | `scripts/shaper/request.py` |
| **qualidade de dados** | **AUSENTE/STUB** — só `compressibility` (correlação score↔bytes não validada); qualidade real (nulls/defeitos/anomalias) só planejada. | `strategies/compressibility.py`; `T-DATA-3` (deferred) |
| **volume de dados (linhas)** | **COBRE + gated** — teto ~866k (tpch-sf01), sem >1M, lento >100k. | `strategies/volume.py`; `T-SHAPER-CODE-HARDENING` (A1) |
| **volume de arquitetura (tabelas/join/FK)** | **COBRE + gated** — schema levels, join integrity, cascata FK sem órfãs (10 testes estatísticos). | `strategies/{schema,join,fk_preserving}.py`; `tests/test_shaper_scientific.py` |

Ressalva: há um 2º caminho de geração fora do shaper (`synthetic:*` via `data_sources`) que *pode*
produzir tipo/qualidade — mas marcado **LEGACY/poor-reference** (`tests/fixtures/synthetic_v2.py`),
só 2 domínios. Capacidade de dimensionar natureza existe parcial e sinalizada como legado, não no
shaper aprovado.

**Leitura**: o shaper dimensiona **quantidade** (linhas + arquitetura, gated). **Não** dimensiona
**natureza** (tipo, qualidade, cardinalidade) — justo onde o T1 localiza os verdictos (high-card vs
cadência). **Cardinalidade** merece destaque: o único lever (`compressibility_range`) FILTRA por
quantil de raridade (muda N); não segura N e varre % de únicos (o sweep T3). É a dimensão-chave do
T1 sem knob nenhum.

## Matriz de gaps (priorizada)

**ALTA** (bloqueia responder "amostra cobre os cenários de transmissão?"):
- **G1** — sem rótulo de forma-de-transmissão nos datasets (eixo load-bearing do T1 não materializado).
- **G2** — bordas de volume ausentes nas duas pontas: µ real (<1KB / página 20-100) só medido ad-hoc;
  `XL` (>1M) inexistente (teto ~866k) + shaper trava >100k. As **bordas idealistas** que o owner pediu.
- **G3** — nicho cadenciado (a vitória mais robusta do T1, −29% vs steelman) sustentado por dado
  **sintético** (`forecast_bench.py`). `beijing-pm25` (série real) existe mas (a) ficou fora do T1,
  (b) tem timestamp SPLIT em int (year/month/day/hour) → **não** exercita a cadência ISO
  (`2026-01-31T09:37` → RLE+delta) que sustenta a claim.

**MÉDIA**:
- **G4** — gaps de tipo (coverage-map): free-text longo near-unique real, IP/UUID/MAC/phone/email/URL,
  monetary-string (`R$ 1.234,56`), geo lat/lon, iso8601-TZ, boolean-literal. São os perfis
  **high-card poucas-colunas** onde o T1 mostra TCF **perder** — precisam existir pra *provar o limite*.
- **G5** — eixo de qualidade não implementado (T-DATA-3 deferido). Consistente com "dados felizes";
  relevante só pros gadgets, não pro TCF-core. Não bloqueia a pergunta de transmissão.

**BAIXA**:
- **G6** — `compressibility` sem validação de correlação; `order=random` sem gate de uniformidade.

## Plano de tickets

- **Reabrir**: [T-SHAPER-CODE-HARDENING](../../../../tickets/T-SHAPER-CODE-HARDENING.md) — só a ação
  **A1** (filter-before-load) SE o alvo exigir datasets de transmissão >100k (gap G2, tier L/XL).
- **Criar**:
  - **T-DATA-TRANSMISSION-GROUPING** (doc/tabela, sem benchmark) — materializa o esquema 3-eixos +
    mapeia os canônicos + D1-D17 em células. Responde Q1. Fecha G1.
  - **T-DATA-CADENCED-TIMESERIES-REAL** — enquadra beijing-pm25 (compor coluna ISO de year/month/
    day/hour) ou curar novo, como dataset **download-cadenced real**. Fecha G3 (tira a claim do synthetic).
  - **T-DATA-EDGE-TRANSMISSION-PAYLOADS** — fixtures de borda: µ (<1KB), bulk (>10k), XL (>1M). Fecha
    G2. Liga a T2/T6 pendentes.
- **Já cobrem (não mexer)**: T-SHAPER-SCIENTIFIC-GATING (closed), T-DATA-1/2/4 (closed).
- **Manter deferido**: T-DATA-3-EDGE-QUALITY-FIXTURES (é insumo dos gadgets, não gap de transmissão;
  alinhado a "dados felizes"). T2-T6 da nota = cenários futuros, não abrir agora.

## Próximo passo mínimo (foco-agora, sem benchmark)

Produzir a **matriz 3-eixos** (tipo × volume-tier × forma-tx) posicionando cada dataset e rotulando a
forma-tx — exercício de mesa sobre metadados já existentes + T1 + coverage-map. Cruzada com os campos
de `ShapeRequest`, responde as **duas** perguntas de uma vez: células vazias = onde os datasets NÃO
são consistentes; colunas tipo/qualidade sem lever correspondente no `ShapeRequest` = onde o shaper
NÃO dimensiona. Entregável = corpo de **T-DATA-TRANSMISSION-GROUPING**. Zero download, zero benchmark,
zero toque em `src/tcf/`.

## Cross-links

[T1 result](../2026-07-05-t1-ndjson-brotli/result.md) · [nota transmissão](transmissao-api-onde-tcf-importa.md) ·
[coverage-map (memória)](C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/project_dataset_coverage_map.md) ·
[diário 2026-07-05](diario/2026-07-05.md).
