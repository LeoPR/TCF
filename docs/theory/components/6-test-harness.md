# Componente 6 — Meta-programa de teste (harness)

Infraestrutura **fora do TCF** que orquestra experimentos cientificos.
Foco: validar o TCF, comparar com CSV/JSON/TOON, simular cenarios
diversos.

> **Filosofia**: TCF nao tem server, transport, ou compressores embutidos.
> Tudo isso e simulado pelo harness. Isso mantem TCF puro como
> encoder/decoder e libera o harness para evoluir sem afetar o core.

## Localizacao no repo

```
TCF/
├── packages/tcf/                  ← TCF core puro (encoder/decoder)
└── experiments/
    └── harness/                   ← META-PROGRAMA aqui
        ├── pipeline.py            ← simula encode → compress → decompress → decode
        ├── transports/
        │   ├── memory.py          ← bytes em memoria (default, rapido)
        │   ├── disk.py            ← grava .tcf.gz em /tmp e le
        │   ├── http_simulated.py  ← simula HTTP via TestServer
        │   ├── tcp_local.py       ← localhost socket (futuro)
        │   └── udp_local.py       ← localhost UDP (futuro)
        ├── compressors/
        │   ├── gzip_codec.py      ← wrapper gzip
        │   ├── brotli_codec.py    ← wrapper brotli
        │   └── zstd_codec.py      ← wrapper zstd (opcional)
        ├── encoders/
        │   ├── tcf_encoder.py     ← chama tcf.encode
        │   ├── csv_encoder.py     ← csv.writer
        │   ├── json_encoder.py    ← json.dumps
        │   └── toon_encoder.py    ← biblioteca toon (se houver)
        ├── compare.py             ← compara N formatos lado a lado
        └── scenarios/
            ├── min_dataset.py     ← cenario minimo (5 rows)
            ├── max_dataset.py     ← cenario maximo (10k rows)
            ├── time_series.py
            └── ...
```

## Por que separar do TCF

| Decisao | Razao |
|---------|-------|
| Nao instalar gzip/brotli no TCF | Usuario que so usa encode/decode nao precisa |
| Nao incluir HTTP no TCF | TCF e biblioteca, nao framework |
| Nao incluir CSV/JSON/TOON | TCF nao deveria conhecer concorrentes |
| Manter harness em `experiments/` | E ferramenta de pesquisa, nao produto |

## Pipeline simulator — API

```python
from harness.pipeline import simulate

result = simulate(
    rows,                            # dados de entrada
    encoder="tcf",                   # OR "csv", "json", "toon"
    encoder_config=tcf_config,       # passthrough para encoder
    transport="memory",              # OR "disk", "http_simulated"
    compression="brotli",            # OR "gzip", "zstd", None
    compression_level=11,            # 1-11 (varia por codec)
    n_iterations=10,                 # repete para timing estavel
)

# result e um PipelineResult com:
#   bytes_uncompressed: int        ← saida do encoder
#   bytes_compressed: int          ← saida do compressor
#   bytes_total: int               ← total transmitido (compressed + headers)
#   encode_ms: float               ← tempo do encoder
#   compress_ms: float
#   transport_ms: float            ← simula latencia
#   decompress_ms: float
#   decode_ms: float
#   roundtrip_ok: bool             ← compare(rows_in, rows_out)
#   roundtrip_diff: dict | None    ← se nao ok, onde difere
```

### Transports disponiveis

**memory**: bytes vivem em variavel local. Sem latencia. Usado para
medicao pura de tamanho/compressao.

**disk**: bytes vao para arquivo `/tmp/<uuid>.tcf.<ext>`. Mede I/O.

**http_simulated**: usa `wsgiref.simple_server` para subir um endpoint
local. Mede HTTP overhead (headers, content-encoding negotiation).

**tcp_local** (futuro): localhost socket. Mede TCP framing.

**udp_local** (futuro): localhost UDP. Mede ausencia de
flow-control/retransmission.

Cada transport implementa interface:

```python
class Transport(Protocol):
    def send(self, payload: bytes) -> None: ...
    def receive(self) -> bytes: ...
    def latency_ms(self) -> float: ...
```

### Compressors disponiveis

```python
class Compressor(Protocol):
    def compress(self, data: bytes, level: int) -> bytes: ...
    def decompress(self, data: bytes) -> bytes: ...
    def name(self) -> str: ...
```

- `gzip_codec` — Python stdlib `gzip`
- `brotli_codec` — `pip install brotli`
- `zstd_codec` — `pip install zstandard`

### Encoders disponiveis

```python
class Encoder(Protocol):
    def encode(self, rows: list[dict], config: dict) -> str | bytes: ...
    def decode(self, data: str | bytes) -> list[dict]: ...
    def name(self) -> str: ...
```

- `tcf_encoder` — chama `tcf.encode_rows`/`tcf.decode`
- `csv_encoder` — `csv.DictWriter`/`csv.DictReader`
- `json_encoder` — `json.dumps`/`json.loads`
- `toon_encoder` — quando integrarmos TOON

## API de comparacao

```python
from harness.compare import compare_formats

result = compare_formats(
    rows,
    encoders=["tcf", "csv", "json", "toon"],
    compressions=[None, "gzip", "brotli"],
    transport="memory",
    n_iterations=10,
)

# result e DataFrame:
# encoder | compression | bytes | encode_ms | decode_ms | roundtrip
# tcf     | None        | 7188  | 0.2       | 0.15      | OK
# tcf     | gzip        | 2200  | 0.5       | 0.4       | OK
# tcf     | brotli      | 1900  | 5.0       | 1.0       | OK
# csv     | None        | 9000  | 0.1       | 0.1       | OK
# csv     | gzip        | 3500  | 0.3       | 0.3       | OK
# ...
```

## Cenarios pre-definidos (scenarios/)

Cada cenario e um dataset + configuracoes esperadas:

### `min_dataset` — 5 rows, 3 cols
Para verificar overhead constante (headers, etc.). TCF deveria ter
overhead alto aqui (poucas linhas para amortizar).

### `max_dataset` — 10000 rows, 20 cols
Para testar escala. TCF compactacao real-world.

### `time_series` — sensor data, alta repetition
Cenario onde TCF deveria brilhar (RLE potencial alto).

### `wide_random` — 100 rows × 100 cols, valores aleatorios
Cenario adverso — pouca redundancia para TCF explorar.

### `categorical_heavy` — Adult Census subset
Real-world com mix categorico + numerico.

### `nested_simulated` — flatten de JSON aninhado
TCF nao suporta nesting nativo; mostrar limitacao.

## Metricas reportadas

Para cada `(encoder, compression, scenario)`:

| Metrica | O que mede |
|---------|------------|
| `bytes_uncompressed` | Saida do encoder (sem compressor) |
| `bytes_compressed` | Apos compressor (se aplicavel) |
| `compression_ratio` | bytes_compressed / bytes_uncompressed |
| `vs_csv_baseline` | bytes_compressed / csv_compressed |
| `vs_json_baseline` | bytes_compressed / json_compressed |
| `encode_ms` | Tempo encoder |
| `compress_ms` | Tempo compressor |
| `total_encode_ms` | encode + compress |
| `decompress_ms` | Tempo descompressor |
| `decode_ms` | Tempo decoder |
| `total_decode_ms` | decompress + decode |
| `roundtrip_ok` | True/False |
| `roundtrip_diff` | Detalhes se False |

## Saida cientifica

Cada experimento gera:

1. **Dados brutos** em `experiments/results/harness/<scenario>/<timestamp>.csv`
2. **Sumario markdown** com tabela e plots (consumido por capitulos do paper)
3. **Manifest JSONL** com cada (encoder, compression, scenario, iteration)
   row para auditoria

```
experiments/results/harness/min_dataset/2026-04-27_140523.csv
experiments/results/harness/min_dataset/2026-04-27_140523.summary.md
experiments/results/harness/min_dataset/2026-04-27_140523.manifest.jsonl
```

## Reuso para outros formatos no futuro

Adicionar novo encoder e simples:

```python
# experiments/harness/encoders/parquet_encoder.py
import pyarrow.parquet as pq
import pyarrow as pa

class ParquetEncoder:
    name = "parquet"
    def encode(self, rows, config):
        table = pa.Table.from_pylist(rows)
        buf = io.BytesIO()
        pq.write_table(table, buf, compression="zstd")
        return buf.getvalue()  # bytes (binario)
    def decode(self, data):
        ...
```

Registra no harness e ja entra nas comparacoes. **TCF nao precisa
mudar para suportar essa extensao.**

## Conexao com cenarios cientificos

O paper precisa responder:
> "Em quais cenarios minimos e maximos o TCF funciona bem?"

Resposta vira dos resultados do harness rodando:

- 6+ cenarios (min/max/time-series/random/categorical/nested)
- 4+ encoders (TCF/CSV/JSON/TOON, futuro Parquet/Avro)
- 3+ compressions (None/gzip/brotli)
- N iteracoes para timing estavel

Total: ~6 × 4 × 3 = 72 combinacoes minimas. Cada uma com
multiplas iteracoes. Saida: tabela 3D `(scenario, encoder, compression)`
com bytes e tempos. Esses dados viram **figuras do paper**.

## Roadmap (proposta)

### Sprint 1 — MVP
- [ ] `pipeline.py` com transport=memory + compressao opt-in
- [ ] Encoders: tcf + csv + json
- [ ] Compressions: gzip + brotli
- [ ] 2 cenarios: min_dataset + max_dataset
- [ ] Resultados em CSV

### Sprint 2 — Combinacoes
- [ ] `compare.py` para sweep multi-encoder
- [ ] Markdown summary auto-gerado
- [ ] Manifests JSONL para auditoria

### Sprint 3 — Cenarios
- [ ] time_series, wide_random, categorical_heavy, nested_simulated
- [ ] Plot generation (matplotlib)

### Sprint 4 — Transports avancados
- [ ] disk transport
- [ ] http_simulated transport
- [ ] (Sprints futuras): tcp_local, udp_local

### Sprint 5 — TOON integration
- [ ] toon_encoder se biblioteca disponivel
- [ ] Comparacao TCF vs TOON em todos os cenarios

## Notas para revisar

Quando reabrir:
- Ver tickets [T-test-harness-mvp](../../workbench/tickets/open/T-test-harness-mvp.md)
- Snapshot deste arquivo no commit `<ts>`
- Estado: `experiments/harness/` provavelmente nao existe ainda
- Foco: validar TCF v0.4 com comparacoes cientificas
