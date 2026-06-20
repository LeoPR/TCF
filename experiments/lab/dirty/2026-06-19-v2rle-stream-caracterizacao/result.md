# V2-RLE-STREAM — caracterização [resultado]

**Data**: 2026-06-19 · resultado (lab dirty, **read-only, NÃO tocou `src/tcf`**).
**Hipótese**: aplicar RLE no **stream de índices do V2-B** (`@dict`) reduz bytes onde há runs
adjacentes do mesmo índice (coluna clusterizada/ordenada). Script: [`analyze.py`](analyze.py) ·
medições brutas: [`result.txt`](result.txt).
**Status**: `CLOSED-INSUFFICIENT-GAIN`.

## Método

`encode(table)` real → gadget `LazyTCF` identifica colunas `@dict` e extrai o stream → modelo RLE
ótimo por run (marcador reservado `0x01` + count base-94 + token; literal quando RLE não compensa).
Métricas: economia textual (% do blob) e **sobrevivência sob brotli-q11** (proxy do uso com
compressor a jusante). 7 datasets **reais** (adult, tpch lineitem/orders/customer, br-identidades,
receita-cnpj, ibge), amostra 1,5k-20k linhas/tabela.

## Resultados

| dataset/tabela | @dict cols | economia textual (% blob) | sob brotli | sort_by upper |
|---|---|---|---|---|
| adult-census/adult | 11/15 | **+7,34%** | −1,43% | relationship 13,0% |
| tpch/lineitem | 7/16 | +0,64% | −2,42% | 0,79% |
| tpch/orders | 4/9 | +0,17% | −0,86% | 0,17% |
| tpch/customer | 2/8 | +0,01% | −2,58% | 0,01% |
| br-identidades/pessoas | 1/6 | +0,00% | −0,18% | 0,0% |
| receita-cnpj/estabelecimentos | 3/8 | +1,96% | −0,73% | uf 2,06% |
| ibge/municipios | 2/8 | +0,56% | −1,82% | 0,68% |

- **Weighted textual: +1,19%** (46.375 B / 3.887.648 B). **0/7 ≥ 15%** → **não passa o gate.**
- **Downstream (brotli) agregado: −1,39%** — a economia **some e inverte**: o brotli já captura os
  runs; os marcadores RLE viram overhead.

## Leitura

- **Por coluna** há ganhos grandes no *stream* de colunas skewed/low-card (race +53,9%, situacao
  +55,0%, l_returnflag +37,0%). Mas o **stream é minoria do blob** — a tabela de únicos + as colunas
  high-card (decimais, ids, free-text) dominam os bytes. Daí o impacto no blob ser pequeno.
- O melhor caso real (adult, muitas categóricas) chega a **7,34%** — metade do gate. O **upper bound
  `sort_by`** (que maximiza runs na chave) não passa de **13,0%** (relationship), e `sort_by` é
  **order-free** (só uma chave se beneficia, reordena tudo).
- **Sob brotli é contraproducente** em 7/7. Confirma o padrão já visto (number-nature; staged-brotli):
  ganho textual modesto que não sobrevive ao compressor a jusante.

## Gate (anti-incidente 2026-05-21)

| pergunta | resposta |
|---|---|
| Real-world testado? | **Sim** — 7 datasets reais (não só sintéticos) |
| N ≥ 5 de fontes diferentes? | **Sim** (7: UCI, TPC-H, BR-id, Receita, IBGE) |
| Bytes absolutos relevantes (≥5% weighted)? | **Não** — 1,19% weighted; melhor caso 7,34% |
| Some sob compressor? | **Sim** — −1,39% sob brotli (inverte) |

→ Falha 2 de 4. **Veredito: `CLOSED-INSUFFICIENT-GAIN`.** Não justifica format change (#TCF.8) +
GATE + complexidade permanente no decoder/lazy.

## Quando reabrir (nicho estreito)

Só se surgir um caso de **transmissão textual-pura** (sem compressor a jusante) de tabelas com
colunas low-card **fortemente clusterizadas/ordenadas** (sinergia com o layout L5/`sort_by` do gadget
lazy, que já cria runs). Mesmo aí, o teto medido (~7-13%) é abaixo do gate. Não priorizar.

## Encaminhamento

- **`src/tcf` intocado** (lab-first; a hipótese não passou, nada foi weldado).
- Marcar `V2-RLE-STREAM` como `closed-insufficient-gain` no ROADMAP + roadmap-hipoteses.
