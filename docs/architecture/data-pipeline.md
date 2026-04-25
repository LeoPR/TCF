---
title: Data Pipeline — fluxo único de dados nos experimentos
date: 2026-04-25
type: architecture
status: ATIVO — pós-Etapa 2 (M1-M8b + M9 unificados)
---

# Data Pipeline — fluxo único de dados nos experimentos

A partir de 2026-04-25, todos os experimentos M-series usam um **único ponto
de entrada** para dados: `experiments/eval/data_sources.load_dataset`. Este
documento descreve o fluxo, os componentes envolvidos e os contratos.

## Princípio arquitetural

**TCF Core é ingênuo.** Não importa Shaper, DatasetReader, DB drivers, ou
qualquer ferramenta de ingestão. Apenas recebe `dict[table, list[dict]]` e
codifica.

**Quem coordena é o orquestrador** (test runners em `experiments/eval/run_m*.py`
ou aplicações cliente). O orquestrador chama `load_dataset(...)`, recebe
`(tables, meta)`, e entrega para o payload builder ou para TCF.

Ver invariantes em [../components/1-tcf-core.md](../components/1-tcf-core.md).

## Fluxo unificado

```
                ORQUESTRADOR (run_m1..m9, etc.)
                         │
                         ▼
           data_sources.load_dataset(source, **kwargs)
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
      synthetic:*                 canonical:*
   (Pipeline A — fixtures)    (Pipeline B — Shaper)
            │                         │
            ▼                         ▼
   tests/fixtures/         scripts/shaper/Shaper().apply(req)
   synthetic_v2.py             ├─ schema_filter
   synthetic_domains.py        ├─ join (no-op)
                               ├─ compressibility (no-op)
                               ├─ stratify (no-op)
                               ├─ fk_preserving  ← FK-aware sampling
                               ├─ volume (skip se fk_preserving)
                               └─ ordering
                                       │
                               scripts/dataset_reader.py
                                       │
                               Z:/tcf-data/interim/*.db
                                       │
                               Z:/tcf-data/external/*.csv
                                       (raw, imutável)
            │                         │
            └────────────┬────────────┘
                         ▼
                tables: dict[name, list[dict]]
                meta: dict (canonical metadata.json ou synthetic-specific)
                         │
                         ▼
              ORQUESTRADOR entrega
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
   build_payload_*(tables, meta)   TCF.encode_columns/encode_rows(...)
   (constrói prompt LLM)            (compressão para storage/transmissão;
                                     legacy: encode(meta, data_dir) para CSV)
            │                         │
            ▼                         ▼
       LLM gera SQL              Texto TCF (L0-L3)
            │
            ▼
       SQLite executa
```

## Sources suportados

| Source | Backend | Kwargs principais |
|--------|---------|-------------------|
| `synthetic:retail_sales` | `tests/fixtures/synthetic_v2.py` | `n_orders`, `seed` |
| `synthetic:medical_consultations` | `tests/fixtures/synthetic_domains.py` | `n_orders`, `seed` |
| `synthetic:financial_transactions` | `tests/fixtures/synthetic_domains.py` | `n_orders`, `seed` |
| `canonical:tpch-sf001` | Shaper + DatasetReader → `Z:/tcf-data/interim/tpch-sf001.db` | `volume`, `seed`, `schema`, `fact_table` |
| `canonical:adult-census` | Shaper + DatasetReader → `Z:/tcf-data/interim/adult-census.db` | `volume`, `seed`, `schema`, `fact_table` |

Adicionar novos sources: editar `experiments/eval/data_sources.py` ou
`scripts/shaper/strategies/`.

## Componentes (cada um faz uma coisa)

### `experiments/eval/data_sources.py`
Orquestrador-level data manager. Único ponto de entrada para experimentos.
Despacha `synthetic:*` para fixtures, `canonical:*` para Shaper.

### `tests/fixtures/synthetic_v2.py` + `synthetic_domains.py`
Geradores Python in-memory, deterministicos por seed. Usados para ablações
controladas (varia `n_orders`, FK topology, null_rate). Zero deps externas.

### `scripts/shaper/`
Framework de extração estratificada para datasets canônicos. **Standalone** —
não depende de TCF, pode ser publicado como ferramenta independente
(ver "Shaper como ferramenta independente" abaixo).

Estratégias (executadas em ordem pelo pipeline):
- `schema_filter` — restringe ao subset de tabelas pedido
- `join` — placeholder (no-op)
- `compressibility` — placeholder (no-op)
- `stratify` — placeholder (no-op)
- `fk_preserving` — sample fact + filtra dims preservando FK integrity
- `volume` — sample N rows (skip quando fk_preserving=True)
- `ordering` — natural / random / sorted

### `scripts/dataset_reader.py`
Cliente SQLite com API uniforme (`rows`, `columns`, `iter_rows`, `query`,
`column_stats`). Lê `Z:/tcf-data/interim/*.db` que foi populado por
`scripts/csv_to_sqlite.py` a partir de `Z:/tcf-data/external/*.csv`.

### `Z:/tcf-data/`
Storage externo (não em git, configurado via `config/storage.json`):
- `external/` — CSVs raw baixados (TPC-H via DuckDB, Adult via UCI)
- `interim/` — SQLite hubs tipados (PK, FK, types declarados)
- `processed/` — derivações em outros formatos (CSV, JSONL, MD)
- `benchmarks/` — resultados pré-M-series (legacy)
- `archives/` — backups frios

Ver [storage.md](storage.md) para detalhes.

## Como adicionar um novo dataset canônico

1. **Baixar dados:** criar `scripts/setup_<name>.py` análogo a `setup_tpch.py`
   que escreve em `Z:/tcf-data/external/<name>/`
2. **Definir schema:** criar `datasets/canonical/<name>/metadata.json` com
   tipos, PK, FK, cardinalidades
3. **Construir SQLite:** rodar `python scripts/csv_to_sqlite.py <name>` para
   gerar `Z:/tcf-data/interim/<name>.db`
4. **Adicionar Shaper schema levels:** editar
   `scripts/shaper/strategies/schema.py::SCHEMA_LEVELS[<name>]` com
   minimal/core/chain/full
5. **Adicionar profile:** editar
   `experiments/eval/data_sources.py::CANONICAL_PROFILES[<name>]` com
   `schema` (lista de tabelas) e `fact_table`
6. **Documentar:** criar `datasets/canonical/<name>/README.md` com origem,
   licença, citação, particularidades

Pronto — qualquer experimento já pode usar `load_dataset("canonical:<name>", ...)`.

## Como adicionar um novo synthetic generator

1. Adicionar função em `tests/fixtures/synthetic_domains.py` que retorna
   `(tables, meta)` no mesmo padrão dos existentes
2. Adicionar branch em `data_sources._load_synthetic`
3. Documentar parâmetros aceitos

## Shaper como ferramenta independente (research idea)

O `scripts/shaper/` foi construído sem dependências em TCF — DatasetReader é
input opcional, ShapeRequest é dataclass pura. **Pode ser extraído como
biblioteca standalone** e republicado:

- Caso de uso: extrair amostras estratificadas de DB canônicos para
  qualquer projeto de ML/LLM
- Estratégias modulares (schema, join, compressibility, stratify,
  fk_preserving, volume, ordering)
- Agnóstico ao consumidor — produz `dict[table, list[dict]]` que qualquer
  framework pode usar

Ideia para investigação futura. Ver research-note: a se criar quando houver
tempo de avaliação concreto.

## Status pós-Etapa 2 (2026-04-25)

| Aspecto | Estado |
|---------|--------|
| Imports diretos de fixtures em runners M-series | **Eliminados** |
| Acesso a dados via `load_dataset` | **100%** (M1-M9) |
| Shaper FK-aware | **OK** — testado em M9 com regressão zero |
| Synthetic via fixtures | **Mantido** — para ablações controladas |
| Canonical via Shaper | **Mantido** — para validação externa |
| TCF Core importa data_sources | **Não** (invariante respeitada) |

## Próximos passos

- Migrar `scripts/benchmark_*.py` (Pipeline B legacy) de `all_rows[:N]` para Shaper
- Estender M9 para Adult Census (precisa adicionar profile no data_sources)
- Implementar Shaper Stratify e Compressibility (atualmente no-op)
- Criar Schema Qualifier (ver
  [../research-notes/2026-04-24-schema-qualifier.md](../research-notes/2026-04-24-schema-qualifier.md))
