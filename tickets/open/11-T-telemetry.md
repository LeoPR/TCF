---
title: Modulo de telemetria (timing honesto por fase)
type: task
status: OPEN
priority: 10
parent: 01-M-datasets-setup
---

# Modulo de Telemetria

## Objetivo

Criar modulo central de medicao de tempo para uso em todos os experimentos.
Isolar fases (IO, parse, encode, decode, compress, LLM inference) para
benchmarks cientificamente honestos.

## Motivacao

Ver [docs/architecture/telemetry.md](../../docs/architecture/telemetry.md)
para discussao completa.

TL;DR: "TCF leva 500ms" nao diz nada. Precisamos:
- `io_read: 2ms`
- `parse: 45ms`
- `tcf_encode: 12ms`
- `llm_inference: 2000ms`

Sem essa separacao, nossos numeros nao sao comparaveis nem reproduziveis.

## Implementacao

Arquivo: `src/tcf/timing.py`

```python
from contextlib import contextmanager
import time
import statistics

class Timings:
    """Coletor de tempos por fase."""

    def __init__(self):
        self.events: dict[str, int] = {}  # ns

    @contextmanager
    def measure(self, name: str):
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            self.events[name] = time.perf_counter_ns() - t0

    def to_dict(self, unit: str = "ms") -> dict[str, float]:
        divs = {"ns": 1, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000}
        div = divs[unit]
        return {k: round(v / div, 3) for k, v in self.events.items()}

    def total(self, unit: str = "ms") -> float:
        divs = {"ns": 1, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000}
        return round(sum(self.events.values()) / divs[unit], 3)


def repeat_with_stats(fn, n: int = 5, warmup: int = 1):
    """Roda fn N vezes, retorna mediana/p95/stdev por fase."""
    for _ in range(warmup):
        t = Timings()
        fn(t)

    runs = []
    for _ in range(n):
        t = Timings()
        fn(t)
        runs.append(t.to_dict())

    result = {}
    for key in runs[0].keys():
        values = [run[key] for run in runs]
        result[key] = {
            "median_ms": round(statistics.median(values), 3),
            "mean_ms": round(statistics.mean(values), 3),
            "p95_ms": round(sorted(values)[min(len(values)-1, int(len(values)*0.95))], 3),
            "min_ms": round(min(values), 3),
            "max_ms": round(max(values), 3),
            "stdev_ms": round(statistics.stdev(values) if len(values) > 1 else 0, 3),
        }
    return result
```

## Fases padronizadas

Nomes consistentes em todos os experimentos (ver telemetry.md):

- `io_read` — leitura de bytes
- `decompress` — lzma/gzip/zstd decode
- `parse_csv`, `parse_json`, `parse_sqlite` — parsers
- `tcf_encode`, `tcf_decode` — TCF especifico
- `csv_write`, `jsonl_write`, `markdown_write` — formato writers
- `gzip_compress`, `gzip_decompress` — compressao binaria
- `llm_inference` — chamada LLM
- `score_response` — scoring

## Testes

`tests/test_timing.py`:

```python
import time
from tcf.timing import Timings, repeat_with_stats

def test_measure_basic():
    t = Timings()
    with t.measure("sleep"):
        time.sleep(0.01)
    assert t.events["sleep"] > 9_000_000  # > 9ms em ns

def test_multiple_phases():
    t = Timings()
    with t.measure("a"):
        time.sleep(0.005)
    with t.measure("b"):
        time.sleep(0.01)
    d = t.to_dict()
    assert "a" in d and "b" in d
    assert d["b"] > d["a"]

def test_repeat_with_stats():
    def fn(t):
        with t.measure("work"):
            time.sleep(0.001)

    result = repeat_with_stats(fn, n=3, warmup=1)
    assert "work" in result
    assert result["work"]["median_ms"] > 0
```

## Integracao com runners futuros

Cada runner (quando criarmos os novos da Fase 2+) importa e usa:

```python
from tcf.timing import Timings

t = Timings()
with t.measure("io_read"):
    data = load_data()
with t.measure("tcf_encode"):
    text = tcf.encode(data)

manifest_entry["timings_ms"] = t.to_dict()
```

## Tarefas

- [ ] Criar `src/tcf/timing.py` com `Timings` e `repeat_with_stats`
- [ ] Criar `tests/test_timing.py` (5-10 testes unitarios)
- [ ] Verificar `pytest tests/test_timing.py` passa
- [ ] Documentar em `docs/architecture/telemetry.md` (ja feito)
- [ ] Nao integrar ainda com runners legacy — so criar o modulo

## O que NAO fazer aqui

- **Nao integrar** com runners antigos (etapa1, etapa2, etc)
  — eles ja estao congelados em `experiments/results-legacy-retail/`
- **Nao criar** runners novos (vem na Fase 2)
- **Nao criar** helpers para Ollama especifico — `Timings` e generico

## Criterio

- `src/tcf/timing.py` existe e exporta `Timings`, `repeat_with_stats`
- Testes passam
- Uso documentado em `docs/architecture/telemetry.md`
- `from tcf.timing import Timings` funciona
