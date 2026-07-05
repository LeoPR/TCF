---
title: T-DATA-TRANSMISSION-GROUPING — Agrupar datasets por cenário de transmissão (matriz 3-eixos)
status: matrix-done
priority: P2
created: 2026-07-05
updated: 2026-07-05
blocked-by: []
related:
  - datasets/coverage-matrix.md
  - experiments/lab/dirty/2026-07-05-nested-tcf-study/result.md
  - experiments/lab/dirty/notas/2026-07-05-cobertura-datasets-shaper-assessment.md
  - experiments/lab/dirty/2026-07-05-t1-ndjson-brotli/result.md
  - experiments/lab/dirty/notas/transmissao-api-onde-tcf-importa.md
  - scripts/shaper/request.py
  - C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/project_dataset_coverage_map.md
---

> **MATRIZ COMPLETADA (2026-07-05)** — corpo (esquema 3-eixos + posicionamento + células vazias +
> "experimento de sempre" com trace OBAT/HCC por forma-tx) em
> **[datasets/coverage-matrix.md](../datasets/coverage-matrix.md)**, lastreado por medição real.
> O eixo forma-tx foi **refinado de 4 → 7 formas** pelo
> [nested-tcf-study](../experiments/lab/dirty/2026-07-05-nested-tcf-study/result.md) (owner pediu
> estudar nested/JSON antes de fechar a matriz): +`upload-batch`, +`download-narrow-high-card` (o
> LIMITE medido), +`nested-response` (envelope). **Q1 = PARCIAL** (matriz consistente, células vazias
> em XL / cadenced-real / µ / nested-real); **Q2 = PARCIAL 2/4** (shaper dimensiona quantidade, não
> natureza). Decorrentes de aquisição (G2/G3) seguem abertos.

# T-DATA-TRANSMISSION-GROUPING — matriz de agrupamento por cenário de transmissão

**[dispositivo]** Decorre do assessment 2026-07-05 (VEREDITO 1 = PARCIAL). Os datasets hoje são
agrupados só por **tipo de dado** (`data_shape`), não por **como transitam** nem por **volume-tier**
— e o T1 (2026-07-05) tornou a forma-de-transmissão o eixo que decide o veredito (upload<1KB → TCF
não ajuda; download-bulk → vence NDJSON; download-cadenced → vence o steelman JSON-colunar). Sem esse
rótulo não dá pra afirmar que "os datasets representam os cenários de transmissão reais".

## Objetivo (foco-agora do owner: só VER a consistência, sem benchmark)

Materializar um esquema explícito de **3 eixos ortogonais** e posicionar cada dataset numa célula.
Células vazias = a resposta honesta de onde os datasets NÃO cobrem. Cruzar com `ShapeRequest` para,
de quebra, mostrar onde o shaper NÃO dimensiona.

| Eixo | Valores | Origem |
|---|---|---|
| **tipo/forma-de-dados** | classes `data_shape` (categorical low/high-card, integer, float sci/monetary, datetime/series, free-text, hierárquico, check-digit-id) | coverage-map (reusar) |
| **volume-tier** | `µ` (<1KB / 20-100 itens) · `S` (~1k) · `M` (3-10k) · `L` (10-100k) · `XL` (>1M) | novo |
| **forma-de-transmissão** | `upload-small` · `download-bulk` · `download-cadenced` · `lazy-query` | novo (T1 + nota transmissão) |

## Rascunho da matriz (para aprovação — dados já existentes, forma-tx inferida)

Forma-de-transmissão de cada canônico (best-fit; um dataset pode servir >1 forma):

| dataset | tipo dominante | tier disponível | forma-tx representada | no T1? |
|---|---|---|---|---|
| adult | categorical low-card largo (15c) | S-L (até ~49k) | **download-bulk** (o caso forte) | sim |
| ibge-municipios | hierárquico/geo (8c) | S-M (~5.6k) | download-bulk | sim |
| online-retail | misto categórico+free-text (8c) | S-XL (~541k) | download-bulk | sim (até 10k) |
| receita-cnpj | misto estruturado+endereço (8c) | S-XL | download-bulk | sim (até 10k) |
| br-identidades/pessoas | high-card (CPF/nomes, 6c) | S-L | download-narrow-high-card (**limite**) | sim |
| tpch-lineitem | estruturado+free-text (16c) | S-XL | download-bulk | sim |
| tpch-orders/customer/... | estruturado (star/chain) | S-L | download-bulk + arquitetura (join/FK) | não |
| **beijing-pm25** | **série temporal sensor** | S-M (~44k) | **download-cadenced** (MAS ts split em int → G3) | **não** |
| wine-quality | float científico (12c) | S (~6.5k) | download-bulk | não |
| D1-D17 (sintéticos) | por tipo, single-col, 12-20 linhas | µ | probes de tipo (não payload) | parcial |
| **— vazio —** | — | **XL (>1M)** | qualquer | **G2** |
| **— vazio —** | timestamp ISO cadenciado real | qualquer | **download-cadenced real** | **G3** |
| **— vazio —** | qualquer | **µ real (<1KB)** | **upload-small / página 20-100** | **G2** |
| **— vazio —** | aninhado | — | **nested-response** (flatten-from-nested) | ausente |

**Leitura do rascunho**: cobertura densa em `download-bulk` (o caso já provado); **vazios** exatamente
onde o T1 aponta valor (cadenced real, bordas µ e XL, nested). Confirma VEREDITO 1 = PARCIAL.

## Cruzamento com o shaper (responde Q2 de graça)

As colunas **tipo** e **qualidade/cardinalidade** da matriz **não têm lever** em
[`ShapeRequest`](../scripts/shaper/request.py) (só volume/schema/join/order/stratify/compressibility/
fk). → o shaper dimensiona quantidade (linhas+arquitetura), não natureza. Gap visível sem rodar nada.

## Critério de aceite

- [ ] Esquema 3-eixos **aprovado pelo owner** (valores dos tiers/formas) — PENDENTE (revisão do owner).
- [x] Matriz completa (canônicos + D1-D17 + sintéticos nested) com forma-tx e tier por célula → `datasets/coverage-matrix.md`.
- [x] Índice `datasets/coverage-matrix.md` central escolhido (não tocar os `metadata.json` por ora).
- [x] Células vazias listadas como gaps (XL / cadenced-real / µ / nested-real / high-card não-BR) → decorrentes G2/G3 + novos registrados.
- [x] Memória `project_dataset_coverage_map` atualizada com o eixo forma-tx (7 formas).
- [x] "Experimento de sempre" (amostra entrada→saída + trace OBAT/HCC) por forma-tx → seção na matriz + `trace_output.txt`.

## Decorrentes (criar SE o owner aprovar priorizar — hoje só registrados)

- **T-DATA-CADENCED-TIMESERIES-REAL** (fecha G3): enquadrar beijing-pm25 como download-cadenced real
  **compondo** uma coluna ISO `ds` de year/month/day/hour (hoje split em int → não exercita a cadência
  ISO que sustenta o T1 Achado 3), OU curar dataset novo com timestamp ISO. Tira a claim mais forte do
  TCF de cima de dado sintético (`forecast_bench.py`).
- **T-DATA-EDGE-TRANSMISSION-PAYLOADS** (fecha G2): fixtures de borda idealista — `µ` (<1KB, página
  20-100), `bulk` (>10k), `XL` (>1M, exige A1 do T-SHAPER-CODE-HARDENING). Cobre o Eixo-1 (bordas) do
  owner + cenários T2/T6 da nota de transmissão.

## Conexões

- Assessment: `experiments/lab/dirty/notas/2026-07-05-cobertura-datasets-shaper-assessment.md`
- Não-gap (manter deferido): [T-DATA-3-EDGE-QUALITY-FIXTURES](T-DATA-3-EDGE-QUALITY-FIXTURES.md) (é
  insumo dos gadgets de qualidade, não cenário de transmissão; alinhado a "dados felizes").
- Reabrir parcial: [T-SHAPER-CODE-HARDENING](T-SHAPER-CODE-HARDENING.md) (A1 filter-before-load, se XL).
