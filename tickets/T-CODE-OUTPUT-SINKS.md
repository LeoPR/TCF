---
title: T-CODE-OUTPUT-SINKS — Interface Sink pluggable
status: open
priority: P2
created: 2026-05-24
updated: 2026-05-24
blocked-by: [T-CODE-ENCODER-MANAGER]
related:
  - docs/adr/0014-unified-api-side-outputs.md
  - tickets/T-CODE-ENCODER-MANAGER.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md
  - docs/workbench/_archive/tickets/frozen/E-http-protocol.md
---

# T-CODE-OUTPUT-SINKS — Sinks pluggable

## Contexto

`scripts/writers/` hoje tem 4 writers standalone (csv, jsonl, markdown,
toon) sem interface comum. Cada um eh funcao top-level.

Pra welding D13 EncodeManager (T-CODE-ENCODER-MANAGER), precisamos de
**contract `Sink`** estavel pra outputs alternativos:

- Arquivo unico (.tcf)
- Multi-arquivo (1 por coluna)
- HTTP streaming
- TCP raw
- In-memory

Plus: side_outputs (debug, stats, schema) podem virar sinks tambem
(grava trace/rede em arquivos paralelos).

## Hipotese

H1: contract `Sink` Protocol-based eh suficiente (vs base class)
H2: side_outputs como sinks separados permite `encode(data,
outputs=[FileSink("dados.tcf"), JSONLSink("trace.jsonl")])`
H3: writers de `scripts/writers/` podem ser refatorados como Sinks
sem quebrar uso atual

## Plano

### Fase 1 — Contract Sink

```python
# src/tcf/sinks/base.py
from typing import Protocol

class Sink(Protocol):
    def write_header(self, magic: bytes, meta: bytes) -> None: ...
    def write_body(self, col_name: str, body: bytes) -> None: ...
    def close(self) -> None: ...
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
```

### Fase 2 — Built-in sinks

```python
# src/tcf/sinks/file.py
class FileSink:
    def __init__(self, path): ...

class MultiFileSink:
    def __init__(self, pattern):  # ex: "col_{name}.tcf"
        ...

class MemorySink:
    def __init__(self): self.data = bytearray()
    def get_text(self) -> str: ...
```

### Fase 3 — Streaming sinks

```python
# src/tcf/sinks/network.py
class HTTPSink:
    def __init__(self, url, channels=1): ...

class TCPSink:
    def __init__(self, host, port): ...
```

Per-channel headers (O-FMT-13) habilitam channels=N.

### Fase 4 — Side-output sinks

```python
# Capturar side_outputs em arquivos paralelos
side_sink = SideOutputsSink("trace_{col}.txt")  # 1 por coluna
encode(data, output=FileSink("dados.tcf"), side_outputs_sink=side_sink)
```

### Fase 5 — Refactor writers/

`scripts/writers/` viram sinks formais. Mantem compat: funcoes
top-level continuam, mas internamente chamam sinks.

## Criterio de aceite

- [ ] Contract `Sink` Protocol definido em `src/tcf/sinks/base.py`
- [ ] 3+ sinks implementados (FileSink, MultiFileSink, MemorySink)
- [ ] RT byte-canonical via FileSink == via str (atual)
- [ ] Pelo menos 1 streaming sink (HTTP ou TCP)
- [ ] Tests: 10+ scenarios

## Riscos

1. **Bloqueado por T-CODE-ENCODER-MANAGER**: precisa de dispatcher
   estavel antes de adicionar sinks
2. **Protocol vs ABC**: Python Protocol mais flexivel mas menos
   ferramentas; ABC mais rigido mas comum em libs
3. **Streaming HTTP precisa per-channel headers** (O-FMT-13 ainda
   conceitual)
4. **Side-output sinks adiciona surface area**: 2 streams paralelos
   (output principal + side) podem confundir API

## Conexao

- [T-CODE-ENCODER-MANAGER](T-CODE-ENCODER-MANAGER.md) — dependencia
- [ADR-0014](../docs/adr/0014-unified-api-side-outputs.md) — SideOutputs
- [O-FMT-08 streaming](../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md)
- [O-FMT-13 per-channel](../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md)
- [E-http-protocol frozen](../docs/workbench/_archive/tickets/frozen/E-http-protocol.md)
- [scripts/writers/](../scripts/writers/) — refatorar

## Updates datados

### 2026-05-24 — abertura

Ticket aberto pos-ADR-0014. Bloqueado por T-CODE-ENCODER-MANAGER (que
introduz manager onde sinks se encaixam). Plano em 5 fases.
