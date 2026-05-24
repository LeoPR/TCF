---
title: T-CODE-ENCODER-MANAGER — Reviver D13 (paralelismo + sinks)
status: open-fase-1-welded
priority: P2
created: 2026-05-24
updated: 2026-05-24
blocked-by: []
related:
  - docs/adr/0014-unified-api-side-outputs.md
  - docs/workbench/research-notes/_archive/2026-05-05-v04-design-recap.md
  - docs/workbench/_archive/tickets/frozen/H-streaming-encoder.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md
---

# T-CODE-ENCODER-MANAGER — Revive D13 (paralelismo + sinks)

## Contexto

Plano v0.4 (2026-04-27 → 2026-05-05) decidiu **D13 EncodeManager
coordena 1+ saidas** mas adiou implementacao pra v0.5+. Hoje (pos
ADR-0014), a fachada `encode()` ja' tem dispatcher + `_encode_column`
isolado como "encode unit" — esqueleto pronto pra workers paralelos.

## Hipotese / Pergunta

H1: paralelizar `_encode_column` em N workers (multiprocessing /
async) reduz tempo de encode em ~Nx pra tabelas largas.
H2: arquitetura de sinks pluggable permite saida pra arquivo,
N arquivos, HTTP/TCP sem reimplementar.
H3: per-channel headers (O-FMT-13) viabilizam re-assembly distribuido
sem coordenacao central.

## Plano

### Fase 1 — Manager basico (worker pool)

```python
from tcf import encode

# Serial (atual)
text = encode(table)

# Paralelo (novo)
text = encode(table, parallel=True)        # ProcessPoolExecutor default
text = encode(table, parallel=N)           # N workers
```

Internamente: `_encode_column` em N workers; manager agrega bodies
em ordem de definicao do dict.

### Fase 2 — Output sinks

```python
# Sink contract
class Sink(Protocol):
    def write_header(self, meta: bytes) -> None: ...
    def write_body(self, col_name: str, body: bytes) -> None: ...
    def close(self) -> None: ...

# Built-in sinks
FileSink("dados.tcf")                 # 1 arquivo (atual via .write(text))
MultiFileSink("col_{name}.tcf")       # N arquivos per coluna
HTTPSink(url, channels=4)             # streaming HTTP (O-FMT-13)
TCPSink(host, port)                   # TCP raw
MemorySink()                          # in-memory (atual default)

# Uso
encode(table, output=FileSink("dados.tcf"))
encode(table, output=MultiFileSink("col_{name}.tcf"))
encode(table, output=HTTPSink(url, channels=4))
```

### Fase 3 — Per-channel headers (O-FMT-13)

Cada canal carrega seu proprio header:

```
#TCF.6 C name=timestamp chunk=1/3 of=table_X
<body chunk 1>
```

Permite re-assembly via metadata distribuida. Pre-requisito: ADR
formal documentando header per-canal (atualizar ADR-0004 ou novo).

### Fase 4 — Streaming chunked (O-FMT-08)

Dividir tabelas grandes em chunks de N rows; cada chunk auto-suficiente.
Decoder reconstrói chunk-a-chunk. Memoria O(chunk_size).

Pre-requisito: chunks autocontidos (cada chunk = TCF mini-arquivo).

## Criterio de aceite

- [ ] Fase 1: paralelizar em 4 workers reduz tempo lineitem 60k de
  16.6min pra <5min (estimativa ~4x speedup)
- [ ] Fase 2: pelo menos 3 sinks implementados (FileSink, MultiFileSink,
  MemorySink) + 100% RT byte-canonical
- [ ] Fase 3: per-channel headers funcionam round-trip
- [ ] Fase 4: streaming chunked em 1 dataset > 100k rows

## Riscos

1. **HCC nao trivialmente paralelizavel**: dependencia entre linhas via
   detector greedy. Per-coluna OK; intra-coluna requer redesign.
2. **Sinks pluggable adiciona surface area**: contract `Sink` precisa
   ser estavel; quebrar quebra todos consumidores.
3. **Per-channel headers mudam formato**: requer ADR + back-compat.
4. **Streaming requer chunks autocontidos**: cada chunk precisa de
   `analyze_column` proprio — perde info global.

## Conexao

- [ADR-0014](../docs/adr/0014-unified-api-side-outputs.md) — fachada
  preparada pra dispatch paralelo
- [v04-design-recap D13](../docs/workbench/research-notes/_archive/2026-05-05-v04-design-recap.md)
- [O-FMT-08 streaming](../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md)
- [O-FMT-13 per-channel](../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md)
- [H-streaming-encoder.md frozen](../docs/workbench/_archive/tickets/frozen/H-streaming-encoder.md)
- [T-CODE-OUTPUT-SINKS](T-CODE-OUTPUT-SINKS.md) — sub-pacote sinks
- [T-CODE-PLAN-CONTRACT](T-CODE-PLAN-CONTRACT.md) — dataclass Plan

## Updates datados

### 2026-05-24 — abertura

Ticket aberto pos-ADR-0014 (API unificada). Fachada `encode()` agora
tem dispatcher + `_encode_column` isolado, pronto pra paralelizar.
Plano em 4 fases. Decisao de iniciar Fase 1 pendente do owner.

### 2026-05-24 — Fase 1 WELDED (paralelismo basico)

Owner aprovou Fase 1. Implementado:

- **`encode(data, parallel=False|True|N)`** em `src/tcf/encoder.py`
- **`_encode_columns_parallel`** em `src/tcf/multi.py` via `ProcessPoolExecutor`
- **`_worker_encode_column`** module-level picklavel
- **Threshold automatico**: paraleliza so' se `>= 2 cols` (1-col dict
  ignora; single-col list ignora)
- **`n_workers` capping**: `min(parallel, n_cols)` (10 workers em
  4 cols => 4 workers)
- **SideOutputs em parallel**: per-col SideOutputs serializado/
  deserializado entre workers; estrutura preservada
- **`multi_info["parallel_workers"]`** novo campo: 0 = serial,
  N = workers usados

**Validacao byte-canonical**:
- D17a 322B INVARIANT preservado em parallel=True/2/4
- `tests/test_parallel.py`: 14/14 passing (byte-identical, RT,
  SideOutputs, edge cases)

**Benchmark medido** (`scripts/benchmark_parallel.py --workers 4`):
- customer (1500x8): serial 0.91s, parallel 1.16s → **0.79x** (pior;
  pickling overhead > paralelismo em tabelas pequenas)
- orders (15000x9): serial 50.36s, parallel 41.09s → **1.23x** (ganho
  modesto)
- Average: 1.01x | All byte-identical: YES

**Aprendizado**:
- Speedup atual eh modesto. Razoes principais:
  1. ProcessPoolExecutor.map distribui sequencialmente (load imbalance:
     coluna datetime pesada bloqueia worker, demais ficam idle)
  2. Pickling overhead de str_values (listas grandes) supera ganho em
     tabelas pequenas
  3. Windows spawn re-importa tudo em cada worker (custo de startup)
- Otimizacao adiada pra sub-fase: trocar `map` por `submit` + work-
  stealing, ou usar `chunksize` ajustado, ou processar com `ray`/
  `joblib`

**Status**: Fase 1 funcional (byte-canonical OK, RT OK, tests passam).
Speedup modesto aceito como baseline; otimizacao pra sub-fase 1b.

### Proximos passos

- **Fase 1b** (sub-fase otimizacao): work-stealing OU chunksize OU
  alternativa pra ProcessPoolExecutor pra speedup melhor
- **Fase 2**: Output sinks (T-CODE-OUTPUT-SINKS, ticket separado)
- **Fase 3**: Per-channel headers (O-FMT-13)
- **Fase 4**: Streaming chunked (O-FMT-08)
