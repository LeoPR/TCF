# TCF -- Testes

Registro dos testes deterministicos. Para resultados LLM, ver [article/](article/README.md).

## Como rodar

```bash
python -m pytest tests/ -v              # Todos (112 testes)
python -m pytest tests/ -k encode       # Filtro
python -m pytest tests/ -s              # Ver prints (benchmark report)
```

## Cobertura

| Arquivo | Testes | O que testa |
|---------|--------|-------------|
| test_encode_decode.py | 21 | Roundtrip levels 0-3, stats, normalize, CLI |
| test_compression_benchmark.py | 55 | 12 cenarios sinteticos x 4 levels, roundtrip |
| test_p01_p02_p03.py | 36 | Infra: tokens, parser, ground truth, scoring |
| **Total** | **112** | |

## Fixtures

### Dados de referencia (`tests/fixtures/__init__.py`)

Progressao L0-L6 para testes de encode/decode.

### Dados sinteticos v2 (`tests/fixtures/synthetic_v2.py`)

| Gerador | Descricao | Parametros |
|---------|-----------|-----------|
| `retail_sales(n, seed)` | E-commerce realista (Zipf, datas, 6 cols) | orders, customers |
| `sensor_logs(n, seed)` | IoT com status repetitivo | readings, sensors |
| `survey_wide(n, q, seed)` | Likert 1-5, muitas colunas | respondents, questions |

### Benchmark de compressao

```bash
python -m pytest tests/test_compression_benchmark.py::TestBenchmarkReport -s
```

Resultados completos: [article/05-results-e1-e2.md](article/05-results-e1-e2.md).
