---
title: T-CODE-ENCODER-MANAGER — Reviver D13 (paralelismo + sinks)
status: open
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
