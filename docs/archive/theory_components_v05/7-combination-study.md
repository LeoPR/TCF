# Componente 7 — Estudo combinatorial de ordem de transformacoes

Plano experimental para decidir **empiricamente** qual ordem de
transformacoes (sort/DICT/RLE/STATS) produz melhor compactacao em
cada cenario.

> **Filosofia**: Em vez de escolher uma ordem teoricamente, testar
> todas as combinacoes plausiveis × varios datasets × varios profiles,
> e reportar a melhor por cenario. A "melhor ordem" pode variar por
> dataset.

## Eixos do experimento

### Eixo 1 — Ordem das transformacoes

```
Pipeline = (sort) → (DICT) → (RLE) → (STATS)

Variacoes plausiveis:
  S → D → R → T   (sort + DICT primeiro, RLE em indices)
  S → R → D → T   (sort + RLE primeiro, DICT depois)
  D → S → R → T   (DICT antes de sort)
  S → D → T → R   (STATS antes de RLE)
  T → S → D → R   (STATS primeiro, antes de tudo)
  S → R → T (sem D)   (sem DICT — controle v0.2)
  S → D → T (sem R)   (sem RLE — variante)
  ... etc
```

Ordens **descartadas teoricamente** (nao fazem sentido):
- RLE → DICT — RLE produziria `2*Male`, depois DICT mapeia o run
  marker, nao o valor. Confuso.
- DICT depois de outro DICT — redundante.
- STATS depois de DICT — STATS perde valores originais.

Total: ~8-12 ordens plausiveis a testar.

### Eixo 2 — Escopo de DICT

| Valor | Significado |
|-------|-------------|
| `none` | sem DICT (controle) |
| `per_column` | DICT separado por coluna |
| `cross_column_auto` | encoder decide se cross-col ou per-col |
| `cross_column_forced` | sempre cross-col em todas categoricas |
| `cross_column_subset` | cross-col so para subset escolhido |

### Eixo 3 — Threshold de RLE

| Valor | Significado |
|-------|-------------|
| `off` | sem RLE |
| `fixed_2` | runs >= 2 (padrao v0.2) |
| `fixed_3` | runs >= 3 (mais conservador) |
| `adaptive_by_type` | threshold varia por tipo (str/int/bool) |
| `bytes_saved` | aplica so se compressao real (proposta v0.4) |

### Eixo 4 — Modo STATS

| Valor | Significado |
|-------|-------------|
| `off` | sem STATS |
| `cardinality_only` | so cardinality + samples |
| `global` | sum/min/max/avg por coluna (v0.2) |
| `stratified` | + cruzamentos por categorical |

### Eixo 5 — Sort

| Valor | Significado |
|-------|-------------|
| `none` | sem sort |
| `manual_<col>` | sort_by especifico |
| `auto_compress` | escolhe coluna que mais comprime |
| `auto_cardinality` | escolhe categorical de menor cardinalidade |

### Eixo 6 — Column ordering

| Valor | Significado |
|-------|-------------|
| `natural` | dict insertion order |
| `pk_first` | PK -> FK -> outras |
| `by_compressibility` | colunas que mais comprimem primeiro |
| `categorical_first` | categoricas antes de numericas |

## Datasets de teste (cenarios)

| Dataset | Caracteristica | TCF deveria brilhar? |
|---------|----------------|---------------------|
| `min_5x3` | 5 rows, 3 cols (overhead alto) | nao |
| `time_series_1000` | sensor 1000 leituras, baixa variacao | sim |
| `adult_100` | Adult Census 100 rows (mix categorico) | sim |
| `tpch_partsupp_100` | TPC-H 100 rows (FKs, numericos) | sim |
| `wide_random_100` | 100×50 valores aleatorios | nao |
| `nested_flat_100` | JSON aninhado flatten 100 rows | nao |

6 datasets cobrem espectro min/max.

## Tamanho do espaco

```
8 ordens × 5 dict_scope × 5 rle_threshold × 4 stats_mode × 4 sort × 4 col_order
= 8 × 5 × 5 × 4 × 4 × 4 = 12,800 combinacoes
```

Multiplicado por 6 datasets = **76,800 execucoes**. Inviavel.

### Reducao via screening

Estrategia **fatorial fracional** + **eliminacao por Pareto**:

1. **Fase A — screening 1D**: para cada eixo, fixa os outros em
   default e varia. Identifica niveis "obviamente piores" e elimina.
   ~ (8+5+5+4+4+4) × 6 = 180 combinacoes
2. **Fase B — pares**: testar todos os pares (eixo 1 × eixo 2, etc.)
   para detectar interacoes. ~ 200 combinacoes
3. **Fase C — top combinacoes**: 30-50 combinacoes finalistas testadas
   em todos os 6 datasets. ~ 300 combinacoes
4. **Fase D — replicacao**: top 5-10 por cenario com 10 iteracoes
   cada para timing.

Total estimado: ~1000 combinacoes em vez de 76,800. Tratavel.

## Metrica composta

Para cada combinacao, calcular:

```python
score(combo, dataset) = (
    bytes_final +
    α * encode_time_ms +
    β * decode_time_ms +
    γ * (1 if not roundtrip_ok else 0)
)
```

Pesos α, β, γ variam por **profile**:
- `minimal_bytes` profile: α=0, β=0 (so bytes importam)
- `decode_speed` profile: α=10, β=20 (latencia importa)
- `balanced` profile: α=1, β=1

Cada profile produz **ranking proprio** das combinacoes.

## Output esperado

Tabela final:

| Profile | Dataset | Best combo (top 1) | Bytes | Encode ms | Decode ms |
|---------|---------|-------------------|-------|-----------|-----------|
| minimal_bytes | adult_100 | S→D_cross→R_bytesaved→T_card | 1850 | 8.2 | 1.5 |
| balanced | adult_100 | S→D_per→R_adaptive→T_global | 5500 | 0.5 | 0.4 |
| decode_speed | adult_100 | (no_sort)→R_off→D_off→T_card | 8500 | 0.1 | 0.1 |
| llm_input | adult_100 | S→R_conservative→T_strat (no D) | 6800 | 0.4 | 0.3 |
| ...      | ...     | ...                | ...   | ...       | ...       |

Plus heatmaps de "qual combo e best em qual cenario".

## Conexao com paper

Resultado deste estudo entra:
- **Cap 3** (TCF Format) — design final justificado por dados
- **Cap 5** (Compressao) — tabelas + heatmaps
- **Apendice A** — defaults v0.4 documentados
- **Apendice C** — full tables com top-10 combos por cenario

E permite responder no paper:
> "TCF v0.4 com profile X em dataset Y atinge Z bytes,
>  N% melhor que CSV+gzip, M% pior que CSV+brotli, mas com
>  vantagem K em accuracy LLM."

## Implementacao do estudo

```python
from harness import simulate
from itertools import product

# Pre-defined combos a testar (apos screening)
combos = [
    {"order": "SDRT", "dict_scope": "per_column", ...},
    {"order": "SDRT", "dict_scope": "cross_column", ...},
    {"order": "SRDT", "dict_scope": "per_column", ...},
    # ... 30-50 combos
]

datasets = ["adult_100", "time_series_1000", ...]
profiles = ["minimal_bytes", "balanced", "decode_speed", "llm_input"]

for combo in combos:
    for dataset_name in datasets:
        rows = load_dataset(dataset_name)
        for profile in profiles:
            # combo + profile podem ter conflitos — combo override
            result = simulate(rows, encoder="tcf", encoder_config={
                **profile_config(profile),
                **combo,
            })
            log_to_manifest(result, combo, dataset_name, profile)
```

## Roadmap

### Fase 1 (semana 1)
- Implementar pipeline configuravel no encoder TCF v0.4
- Cada transformacao pluggable (Strategy pattern)

### Fase 2 (semana 2)
- Screening 1D em cada eixo (Fase A acima)
- Identificar niveis dominados/dominantes

### Fase 3 (semana 3)
- Pares (Fase B)
- Top combos (Fase C)

### Fase 4 (semana 4)
- Replicacao + analise + figuras
- Documentar defaults v0.4

## Notas para revisar

Quando reabrir:
- Tickets relacionados:
  - [E-compression-combinations](../../workbench/tickets/open/E-compression-combinations.md)
  - [T-test-harness-mvp](../../workbench/tickets/open/T-test-harness-mvp.md)
- Estado: implementacao depende do harness MVP existir primeiro
- Tempo total estimado: ~4 semanas (paralelo a implementacao TCF v0.4)
