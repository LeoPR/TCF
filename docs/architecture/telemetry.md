# Telemetry — Honest Benchmark Timing

Como medimos tempos de forma honesta, separando fases para que benchmarks
nao sejam enganosos.

## O problema

Benchmarks sem isolamento de fases sao enganosos. Exemplo:

> "TCF encode levou 3 segundos"

Realmente 3s de encode? Ou:
- 100ms de encode + 2.9s lendo do disco?
- 500ms de parse CSV + 2.4s descomprimindo gzip + 100ms encode?
- 50ms de encode + 50ms de cache miss + 2.9s de swap do SO?

Sem separacao, nao sabemos.

## Solucao — modulo central de timing

Todos os experimentos e benchmarks usam `src/tcf/timing.py`:

```python
from tcf.timing import Timings

t = Timings()

with t.measure("io_read"):
    raw = path.read_bytes()

with t.measure("decompress"):
    data = lzma.decompress(raw) if compressed else raw

with t.measure("parse_csv"):
    rows = list(csv.DictReader(io.StringIO(data.decode())))

with t.measure("tcf_encode"):          # <-- isolado
    tcf_text = tcf.encode(rows, config)

with t.measure("tcf_gzip"):
    compressed = gzip.compress(tcf_text.encode())

# Output no manifest
result["timings_ms"] = t.to_dict(unit="ms")
# {"io_read": 2.1, "decompress": 0.0, "parse_csv": 45.3,
#  "tcf_encode": 12.7, "tcf_gzip": 8.2}
```

## Fases padronizadas

Nomes consistentes em todos os experimentos:

### Pipeline de leitura (comum a todos os formatos)

| Nome | O que mede | Comum a |
|------|-----------|---------|
| `io_read` | Leitura de bytes do disco | todos |
| `decompress` | lzma/gzip/zstd decompress | datasets archived |
| `parse_csv` | csv → rows/dicts | baseline |
| `parse_json` | json → dicts | JSONL |
| `parse_sqlite` | SQL query → rows | SQLite hub |

### Pipeline de encode (especifico por formato)

| Nome | O que mede | Formato |
|------|-----------|---------|
| `tcf_encode` | TCF encoder | TCF |
| `csv_write` | CSV writer stdlib | CSV |
| `jsonl_write` | JSON lines writer | JSONL |
| `markdown_write` | MD table writer | MD |
| `toon_encode` | TOON encoder | TOON (futuro) |

### Pipeline de decode

| Nome | O que mede | Formato |
|------|-----------|---------|
| `tcf_decode` | TCF decoder | TCF |
| `csv_read` | CSV reader stdlib | CSV |
| ... | | |

### Pipeline de compressao binaria

| Nome | O que mede | Algoritmo |
|------|-----------|-----------|
| `gzip_compress` | gzip encode | gzip |
| `gzip_decompress` | gzip decode | gzip |
| `brotli_compress` | brotli encode | brotli |
| `zstd_compress` | zstd encode | zstd |

## No paper — como reportar

**Reportar por fase, nao total.**

Exemplo correto:

```
Formato | io_read | parse | encode | total | gzip | final_bytes
TCF L0  |  2.1ms  | 45ms  |  12ms  | 59ms  | 8ms  |     21KB
TCF L2  |  2.1ms  | 45ms  |  35ms  | 82ms  | 7ms  |     19KB
CSV     |  2.1ms  | 45ms  |   0ms  | 47ms  | 9ms  |     21KB
JSONL   |  2.1ms  | 45ms  |   8ms  | 55ms  | 11ms |     60KB
```

**Leitor ve claramente:**
- `io_read + parse = 47ms` e comum a todos (baseline)
- `encode` isolado: TCF 12-35ms, CSV 0ms (stdlib), JSONL 8ms
- `gzip` varia por formato (eficiencia da compressao)
- `final_bytes` e o output util

**Claim do paper:** "TCF encode adiciona 12ms ao baseline de leitura/parse,
mas economiza 13% de bytes finais apos gzip."

## Comparacao com outros benchmarks

Muitos benchmarks de LLM format fazem um dos erros:

### Erro 1: reportar "total time" sem desagregar

"Format X leva 500ms" mistura disco, parse, encode. Nao reproduzivel
entre sistemas (SSD vs HDD muda tudo).

**Nosso approach:** sempre reportar fases separadas.

### Erro 2: medir com `time.time()` em vez de `perf_counter_ns()`

`time.time()` tem resolucao variavel por OS. Em Windows, muitas vezes
so 15ms de resolucao.

**Nosso approach:** usar `time.perf_counter_ns()` sempre (nanossegundo,
monotonic, otimizado para benchmarks).

### Erro 3: nao rodar warmup

Primeira execucao inclui: JIT (se houver), cache miss de disco, page fault.

**Nosso approach:** warmup de 1-2 execucoes antes da medicao real.
Descartar primeira.

### Erro 4: rodar 1x so

Ruido aleatorio de GC, SO scheduler, thermal throttling.

**Nosso approach:** mediana de 3-5 execucoes, reportar mediana + p95.

## Implementacao

`src/tcf/timing.py`:

```python
from contextlib import contextmanager
from pathlib import Path
import json
import time
import statistics

class Timings:
    """Coletor de tempos por fase usando perf_counter_ns."""

    def __init__(self):
        self.events: dict[str, int] = {}

    @contextmanager
    def measure(self, name: str):
        """Mede o bloco. Grava em nanosegundos."""
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            self.events[name] = time.perf_counter_ns() - t0

    def to_dict(self, unit: str = "ms") -> dict[str, float]:
        """Exporta em unidade escolhida (ns, us, ms, s)."""
        divs = {"ns": 1, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000}
        div = divs[unit]
        return {k: round(v / div, 3) for k, v in self.events.items()}

    def total(self, unit: str = "ms") -> float:
        """Soma de todos os eventos."""
        divs = {"ns": 1, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000}
        return round(sum(self.events.values()) / divs[unit], 3)


def repeat(fn, n: int = 5, warmup: int = 1) -> dict:
    """Roda funcao N vezes (+ warmup) e retorna estatisticas."""
    for _ in range(warmup):
        fn()  # descarta warmup

    times = []
    for _ in range(n):
        t = Timings()
        fn(t)  # fn deve aceitar Timings opcional
        times.append(t.to_dict())

    # Consolidar por fase
    result = {}
    for key in times[0].keys():
        values = [run[key] for run in times]
        result[key] = {
            "median_ms": round(statistics.median(values), 3),
            "mean_ms": round(statistics.mean(values), 3),
            "p95_ms": round(sorted(values)[int(len(values) * 0.95)], 3),
            "min_ms": round(min(values), 3),
            "max_ms": round(max(values), 3),
            "stdev_ms": round(statistics.stdev(values) if len(values) > 1 else 0, 3),
        }
    return result
```

Ver ticket `11-T-telemetry.md` para implementacao completa.

## Integracao com manifests

Cada experiment runner adiciona `timings_ms` em cada entry do manifest:

```json
{
  "key": "gemma3:12b|tpch-sf001|lineitem|csv|q1_sum",
  "model": "gemma3:12b",
  "dataset": "tpch-sf001",
  "table": "lineitem",
  "format": "csv",
  "question": "q1_sum",
  "correct": true,
  "response": "153078.22",
  "prompt_chars": 4821,
  "prompt_tokens": 1234,
  "response_tokens": 8,
  "latency_s": 2.1,

  "timings_ms": {
    "io_read": 2.1,
    "parse_csv": 45.3,
    "encode": 0,
    "llm_inference": 2047.2,
    "score_response": 0.1
  }
}
```

Analise pos-hoc pode decompor `latency_s` em cada fase.

## Referencias

- [Python time module (perf_counter_ns)](https://docs.python.org/3/library/time.html#time.perf_counter_ns)
- [Google Benchmarking guide](https://google.github.io/benchmark/)
- [Best practices — timing in Python](https://stackoverflow.com/questions/8220801/how-to-use-timeit-module)
