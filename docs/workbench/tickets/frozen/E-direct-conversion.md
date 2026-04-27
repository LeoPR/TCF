---
title: Conversao direta da fonte — SQL/Parquet/DataFrame → TCF (pular CSV)
type: experiment
status: OPEN
priority: MEDIUM
created: 2026-04-10
origin: Observacao — se a fonte e SQL, converter direto e mais eficiente?
parent: G-utility-analysis
---

# Conversao Direta da Fonte

## Hipotese

**H-direct:** Encodar direto de SQL/Parquet/DataFrame para TCF e
significativamente mais rapido que o pipeline SQL → CSV → TCF.

**Razoes:**
1. CSV parsing e custoso (split, quoting, escape handling)
2. CSV perde tipos (tudo vira string, depois precisa re-inferir)
3. Fontes tipadas (SQL, Parquet) ja tem schema — reusar
4. Menos alocacao de memoria intermediaria

## Comparacoes relevantes

### SQL source
```
Pipeline A: PostgreSQL → cursor → rows → CSV text → parse CSV → dict → TCF text
Pipeline B: PostgreSQL → cursor → rows → dict → TCF text (direto)
```

**Hipotese:** Pipeline B e 3-5x mais rapido.

### Parquet source
```
Pipeline A: Parquet → pyarrow → to_csv() → read CSV → parse → TCF
Pipeline B: Parquet → pyarrow → arrays → TCF (direto, com tipos)
```

**Hipotese:** Pipeline B e mais rapido E preserva tipos numericos
(nao precisa re-parsear floats).

### DataFrame source
```
Pipeline A: df.to_csv() → read CSV → parse → TCF
Pipeline B: df.itertuples() → TCF (direto)
```

**Hipotese:** Pipeline B 2-3x mais rapido.

## Vantagens potenciais

1. **Velocidade:** menos steps, menos parsing
2. **Tipos preservados:** integers ficam integers, floats ficam floats
3. **Menos memoria:** nao precisa armazenar CSV intermediario
4. **Metadata disponivel:** PK, FK, NOT NULL ja estao na fonte

Ponto 4 se conecta com **P-schema-extension** — se TCF tem schema
declarado, o encoder direto popula automaticamente do DDL da fonte.

## Desvantagens potenciais

1. **Acoplamento:** encoder precisa conhecer cada fonte (mais codigo)
2. **Dependencias:** pyarrow, sqlalchemy, pandas viram opcionais
3. **Dificil manter bug-por-bug compat com versao CSV**

## Competidores

### TOON
Nao testamos se TOON tem adapters diretos. Provavelmente tambem
converte por CSV/JSON primeiro.

**Se TCF tiver adapter direto e TOON nao, e um ponto de vantagem real.**

### Parquet
Parquet e ja "direto da fonte" — nao precisa adapter. Mas Parquet e
binario e nao e LLM-friendly.

### JSON
`json.dumps(list(cursor))` e o pipeline padrao. Simples mas lento em escala.

## Design experimental

### Setup
- Fonte: SQLite in-memory com retail_sales(1000) pre-carregado
- Target: TCF L2 text
- Metrica: tempo wall-clock para encode completo
- Repeticoes: 100 runs cada, reportar mediana

### Pipelines a comparar

1. **sqlite → csv → TCF** (baseline, como fazemos hoje)
2. **sqlite → dict → TCF** (adapter direto)
3. **sqlite → pandas → TCF** (via pandas)
4. **pandas → csv → TCF** (baseline pandas)
5. **pandas → dict → TCF** (direto de pandas)
6. **parquet → pandas → csv → TCF** (pior caso)
7. **parquet → pyarrow → TCF** (melhor caso)

### Escalas: 100, 1000, 10000 linhas

## Metricas adicionais (alem de tempo)

- **Peak memory:** tracemalloc
- **GC pressure:** numero de objetos alocados
- **CPU cycles:** sys.monotonic()

## Implementacao

Modulo novo: `src/tcf/adapters/`

```python
from tcf.adapters import from_sqlite, from_parquet, from_dataframe

# Cada adapter bypassa CSV
text = from_sqlite("db.sqlite", query="SELECT * FROM vendas", level=2)
```

Internamente, adapters produzem `dict[str, list[str]]` (ou list[dict])
e passam direto para `encode_from_dict(...)` — uma nova funcao que
contorna o parser CSV atual.

## Relacao com outros tickets

- **T-G42-input-adapters**: ja propoe os adapters, este ticket testa
  performance
- **P-schema-extension**: adapter direto pode popular schema automaticamente
- **G-utility-analysis**: uma das dimensoes do guia mestre
- **E-http-protocol**: se encode e rapido, TCF e viavel para APIs
  server-side

## Tarefas

- [ ] Implementar `encode_from_dict(columns: dict, meta: dict)` no encoder
- [ ] Implementar adapter SQLite (zero deps)
- [ ] Implementar adapter pandas (dep opcional)
- [ ] Implementar adapter pyarrow/parquet (dep opcional)
- [ ] Benchmark: 7 pipelines × 3 escalas × 100 runs
- [ ] Comparar com pipelines JSON equivalentes (baseline)
- [ ] Se TOON tem adapters: comparar
- [ ] Documentar em article/ como "Direct Source Integration"
