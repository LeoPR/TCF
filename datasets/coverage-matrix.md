# Matriz de cobertura de transmissão — datasets × volume-tier × forma-de-transmissão [probatório]

**Data**: 2026-07-05 · **Tipo**: [probatório] · Corpo do ticket
[T-DATA-TRANSMISSION-GROUPING](../tickets/T-DATA-TRANSMISSION-GROUPING.md). Materializa o esquema
3-eixos do [assessment de cobertura](../experiments/lab/dirty/notas/2026-07-05-cobertura-datasets-shaper-assessment.md)
(VEREDITO 1 = PARCIAL) e responde as duas perguntas do owner: **(Q1)** os datasets estão agrupados
de forma consistente para os cenários de transmissão? **(Q2)** o shaper dimensiona em todas as direções?

Cada célula é lastreada por **medição real** (não estimativa): bytes brotli-q11 + RT, do
[nested-tcf-study](../experiments/lab/dirty/2026-07-05-nested-tcf-study/) (harness `nested_bench.py`
+ `trace_experiment.py`, saída bruta em `trace_output.txt`) e do [T1](../experiments/lab/dirty/2026-07-05-t1-ndjson-brotli/result.md).
A prosa aponta; o número vem do harness. `py -3` + `tcf 0.7.1` + `brotli 1.2.0`.

---

## Os 3 eixos ortogonais

| Eixo | Valores | Origem |
|---|---|---|
| **tipo/forma-de-dados** | classes `data_shape` (categorical low/high-card · integer key/count · float sci/monetary · datetime/série · free-text curto/longo · hierárquico · check-digit-id) | [coverage-map](../../.claude/…/memory) (reusa) |
| **volume-tier** | `µ` (<1KB / 20-100 itens) · `S` (~1k) · `M` (3-10k) · `L` (10-100k) · `XL` (>1M) | novo |
| **forma-de-transmissão** | 7 formas (tabela abaixo) — refinado pelo nested-study | novo (T1 + nested-study + nota transmissão) |

O 3º eixo é o **load-bearing** (o T1 mostrou que o veredito muda por forma). O nested-study refinou
de 4 para **7 formas**, separando `upload` em small-config vs batch e adicionando `nested-response`.

---

## Eixo 3 — as 7 formas de transmissão (com veredito TCF medido)

| # | forma-tx | o que é | veredito TCF | evidência (medida) |
|---|---|---|---|---|
| 1 | **upload-small** | request de config/instrução escalar, <1KB | **✗** (moldura > ganho) | config-only: TCF **169B** br > raw-JSON **140B** br |
| 2 | **upload-batch** | request com **array grande homogêneo** (batch) | **✓ em escala** | series n=500: nested-TCF **283B** vs raw-JSON 1033B (27%) |
| 3 | **download-bulk** | response = array de objetos tabular | **✓** | adult[:200]: **2354B** br de ~21.6KB TSV; T1 −20–28% vs NDJSON |
| 4 | **download-cadenced** | série/forecast/logs, chaves sequenciais | **✓✓** (o nicho robusto) | forecast 744pts: nested-TCF **990B** = 71.9% do JSON-colunar (−28%) |
| 5 | **download-narrow-high-card** | poucas colunas, quase-únicas (CPF/nome/UUID) | **✗/marginal** (o LIMITE) | pessoas[:200]: **5598B** br de 16.2KB TSV; `!cpf` cai raw |
| 6 | **lazy-query** | agregação seletiva sem descomprimir tudo | **✓** (ortogonal) | query toca **0,2–7,9%** do blob ([lazy-query](../experiments/lab/dirty/old/welded/2026-06-16-lazy-query/result.md)) |
| 7 | **nested-response** | envelope aninhado embrulhando 3/4/5 | **✓ se o conteúdo for bulk/cadenced** | envelope+blocos add ~86B sobre o TCF puro; conteúdo decide |

**Leitura**: TCF vence quando a transmissão carrega **volume tabular ou cadência** (2·3·4). Empata/perde
em **payload pequeno** (1) ou **high-card estreito** (5). O `nested` (7) é ortogonal — o envelope é
barato; quem decide é o array embrulhado.

---

## A matriz — posicionamento de cada dataset

Legenda tier: **µ**<1KB · **S**~1k · **M**3-10k · **L**10-100k · **XL**>1M. `†` = sintético.

| dataset | tipo dominante | tiers disponíveis | forma-tx primária | no T1? | medido |
|---|---|---|---|---|---|
| **adult** | categorical low-card largo (15c) | S · M · L (~49k) | **download-bulk** | sim | ✓ forte |
| **ibge-municipios** | hierárquico/geo (8c) | S · M (~5.6k) | download-bulk | sim | ✓ |
| **online-retail** | misto categórico+free-text (8c) | S · M · L · **XL** (~541k) | download-bulk | sim (≤10k) | ✓ |
| **receita-cnpj** | misto estruturado+endereço (8c) | S · M · L · **XL** | download-bulk | sim (≤10k) | ✓ |
| **br-identidades/pessoas** | high-card (CPF/nome/email, 6c) | S · M · L | **download-narrow-high-card** ⟵ LIMITE | sim | ✓ (marginal) |
| **br-identidades/empresas** | check-digit CNPJ + estruturado | S · M · L | download-bulk | não | — |
| **tpch-lineitem** | estruturado+free-text (16c) | S · M · L · **XL** | download-bulk | sim | ✓ |
| **tpch orders/customer/part…** | estruturado (star/chain) | S · M · L | download-bulk **+ arquitetura** (join/FK) | não | — |
| **beijing-pm25** | série temporal sensor | S · M (~44k) | **download-cadenced** ⚠ ts SPLIT em int → **G3** | não | — |
| **wine-quality** | float científico (12c) | S (~6.5k) | download-bulk | não | — |
| **D1-D17** † | por tipo, single-col, 12-20 linhas | **µ** | probes de tipo (não payload) | parcial | — |
| **forecast_bench** † | série cadenciada (ds/yhat) | µ · S | **download-cadenced** (a claim robusta) | sim | ✓✓ |
| **nested request** † (batch) | config + array series | µ · S | **upload-batch** / upload-small | não | ✓ (este study) |
| **nested response** † (envelope) | envelope + forecast array | µ · S | **nested-response** | não | ✓ (este study) |

### Células VAZIAS (a resposta honesta de onde NÃO cobrimos)

| célula vazia | forma-tx | gap | severidade |
|---|---|---|---|
| **— nenhum —** tier **XL** (>1M) real medido | qualquer | **G2** (shaper trava >100k; A1 reaberto) | ALTA |
| **— nenhum —** download-cadenced **real** com timestamp ISO | download-cadenced | **G3** (beijing tem ts split-int; claim repousa em forecast † sintético) | ALTA |
| **— nenhum —** µ **real** (<1KB, página 20-100) | upload-small | **G2** (só medido ad-hoc/sintético) | ALTA |
| **— nenhum —** nested-response **real** (captura de API aninhada) | nested-response | novo — só sintético (este study) | MÉDIA |
| **— nenhum —** high-card não-BR (UUID/hash/IP) | download-narrow-high-card | **G4** (só CPF/nome; falta o perfil que *prova o limite* de forma geral) | MÉDIA |

**Leitura da matriz**: cobertura densa em `download-bulk` (o caso já provado, 6 datasets reais).
Vazios **exatamente** onde o T1/nested-study apontam valor ou limite: cadenced-real, bordas µ e XL,
nested-real. → confirma **VEREDITO 1 = PARCIAL** e nomeia o que falta adquirir.

---

## Experimento de sempre — amostra entrada→saída + trace por forma-tx

Uma célula representativa por forma-tx. Trace completo (OBAT + HCC + seq-RLE) em
[`trace_output.txt`](../experiments/lab/dirty/2026-07-05-nested-tcf-study/trace_output.txt);
aqui vai o essencial. Todos com **RT=True**.

### (1) upload-small — config/instrução multi-camada `(path, value)` — TCF ✗
```
entrada:  model=seasonal-cumulative · options.{cumulate,reset,horizon,freq,tz,fill_gaps} · window.{start,end}
saída:    #TCF.7 M / 83=path,!value / model / options.*cumulate / 2reset / 2horizon / 2f*req ...
          OBAT fatora o prefixo "options." (P(2,8)+L('reset')); sem cadência, sem seq-RLE.
bytes:    169B br  (vs raw-JSON 140B br)  →  PERDE — payload <200B, moldura > ganho.
```

### (2) upload-batch — array `series` (n=20) — TCF ✓ em escala
```
entrada:  {asset:ASSET_SYN_0001.., variable:cumulative_metric, unit:unit_a, weight:1.0} × 20
saída:    #TCF.7 M / 46=asset,22=variable,11=unit,weight
          ASSET_SYN_\00*\0*\1  ← seq-RLE do id cadenciado (asset seq_rle_runs=2)
          *20|cumulative_metric / *20|unit_a / *20|\1.\0   ← colunas constantes → 1 linha RLE cada
bytes:    n=20 134B ; n=500 nested-TCF 283B vs raw-JSON 1033B (27%)  →  VENCE em batch.
```

### (3) download-bulk — adult[:200] (low-card largo) — TCF ✓ forte
```
entrada:  15 col × 200 (age·workclass·education·occupation·race·sex·native-country·class…)
saída:    #TCF.7 M / @440=age,@263=workclass,!1365=fnlwgt,@325=education,...  ← dict-coded low-card
          236 / *2+13|\25 / *2+16|\28 ...  ← seq-RLE nos deltas de age
bytes:    2354B br  de ~21.6KB TSV  (T1: −20–28% vs NDJSON+brotli)  →  VENCE.
```

### (4) download-cadenced — forecast block ds/yhat (24pts) — TCF ✓✓
```
entrada:  {ds:2026-07-05T00:37.., yhat:53.0..} × 24
saída:    #TCF.7 M / %109=ds,!yhat
          *24|\2026 / *24|\07 / *24|\05 / *24+1|\00 / *11|\37 / *12|\38   ← cadência do ds
          (ds cadence=1-uniform-length-high-lcp-lcs, seq_rle_runs=3 ; yhat raw)
bytes:    24pts 181B br ; 744pts nested-TCF 990B = 71.9% do JSON-colunar (−28%)  →  VENCE o steelman.
```

### (5) download-narrow-high-card — pessoas[:200] (CPF/nome/email) — TCF marginal (LIMITE)
```
entrada:  6 col × 200 (cpf·nome·municipio_id·uf_sigla·data_cadastro·email)
saída:    #TCF.7 M / !2999=cpf,2604=nome,!1599=municipio_id,@275=uf_sigla,%943=data_cadastro,email
          cpf/municipio_id/email → RAW (!): quase-únicos, sem redundância estrutural.
          uf_sigla → @dict (low-card) ; data_cadastro → %split (estrutura de data).
bytes:    5598B br  de 16.2KB TSV  →  ganho MODESTO (compressão pior que adult apesar de menos bytes de entrada).
```

### (6) nested-response — envelope + bloco TCF (o "TCF aninhado") — TCF ✓ se conteúdo bulk/cadenced
```
esqueleto:  {"ASSET_SYN_01":{"cumulative_metric":{"-":{"projectable":true,
             "messages":["ok","cumulative","gap.variable"],"forecast":{"@tcf_block":0}}}}}
bloco 0:    #BLOCK 0 ds:str yhat:num  +  <TCF do array forecast (cadência acima)>
bytes:      744pts nested-TCF 990B vs JSON-colunar 1377B (−28%); envelope custa ~86B sobre TCF puro (904B).
            (7) é ortogonal: o envelope é barato; quem decide é o array embrulhado (aqui, cadenced).
```

### (6b) lazy-query — não re-medido aqui; ver [lazy-query](../experiments/lab/dirty/old/welded/2026-06-16-lazy-query/result.md) (query toca 0,2–7,9% do blob).

---

## Cruzamento com o shaper (responde Q2 de graça)

A matriz tem colunas de **tipo**, **volume-tier** e **forma-tx**. O
[`ShapeRequest`](../scripts/shaper/request.py) só tem lever para **volume** (linhas) e **arquitetura**
(schema/join/fk/order/stratify/compressibility). **Não** tem lever de **tipo**, **qualidade** nem
**cardinalidade-a-N-fixo**. Logo:

| eixo da matriz | shaper dimensiona? |
|---|---|
| volume-tier (linhas) | **sim** — `volume.py` (teto ~866k; sem XL; lento >100k → G2/A1) |
| arquitetura (tabelas/join/FK) | **sim** — `schema/join/fk_preserving` (gated, 10 testes) |
| tipo de dados | **não** — sem campo `type`; só devolve colunas já no hub |
| qualidade | **não** (stub `compressibility`; qualidade real = gadget deferido) |
| cardinalidade a N-fixo | **não** — `compressibility_range` filtra por quantil (muda N); não segura N e varre % únicos |

→ **VEREDITO 2 = PARCIAL (2 de 4 eixos)**. O shaper dimensiona **quantidade** (linhas + arquitetura),
não **natureza** (tipo/qualidade/cardinalidade) — justo onde a forma-tx 5 (high-card) e o sweep T3
localizam o limite do TCF.

---

## Conclusão — respostas diretas

- **Q1 (datasets consistentes?) → PARCIAL.** Agora existe um esquema explícito de 3 eixos e cada
  dataset está posicionado. A cobertura é densa e provada em `download-bulk`; as células vazias
  (XL real, cadenced-ISO real, µ real, nested real) são o que falta para dizer "os datasets
  representam os cenários de transmissão reais". Os gaps viram os decorrentes
  T-DATA-CADENCED-TIMESERIES-REAL (G3) e T-DATA-EDGE-TRANSMISSION-PAYLOADS (G2).
- **Q2 (shaper dimensiona tudo?) → PARCIAL (2/4).** Cobre quantidade; não cobre natureza.

## Cross-links

[T-DATA-TRANSMISSION-GROUPING](../tickets/T-DATA-TRANSMISSION-GROUPING.md) ·
[assessment cobertura](../experiments/lab/dirty/notas/2026-07-05-cobertura-datasets-shaper-assessment.md) ·
[nested-tcf-study](../experiments/lab/dirty/2026-07-05-nested-tcf-study/result.md) ·
[T1](../experiments/lab/dirty/2026-07-05-t1-ndjson-brotli/result.md) ·
[nota transmissão](../experiments/lab/dirty/notas/transmissao-api-onde-tcf-importa.md).
