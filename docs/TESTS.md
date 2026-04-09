# TCF -- Testes Unitarios

Registro dos testes deterministicos (sem LLM). Para resultados de
experimentos com LLM, ver [docs/article/](article/README.md).

**Rastreabilidade:** Este arquivo e fonte primaria de cobertura de testes.
Ver [SOURCE_MAP.md](SOURCE_MAP.md) para hierarquia de documentos.

## Como rodar

```bash
python -m pytest tests/ -v              # Todos (151 testes)
python -m pytest tests/ -k g01          # Filtro por grupo
python -m pytest tests/ -x              # Parar no primeiro erro
python -m pytest tests/ -s              # Ver print (benchmark report)
```

## Cobertura

| Grupo | Arquivo | Testes | O que testa |
|-------|---------|--------|-------------|
| G01 | test_g01_encode_decode.py | 63 | Encode/decode L0-L6 + variantes + stats |
| G01b | test_g01_compression.py | 17 | Benchmark compressao sintetica |
| - | test_roundtrip.py | 7 | Roundtrip dados reais |
| - | test_p01_p02_p03.py | 36 | Token count, parser, ground truth |
| - | test_p04_encoder_variants.py | 28 | 24 variantes de EncoderConfig |
| **Total** | | **151** | **All pass** |

## Fixtures (`tests/fixtures/`)

### Dados de referencia (`tests/fixtures/__init__.py`)

| Fixture | Dados | Complexidade |
|---------|-------|-------------|
| `l0_single_column()` | 1 tabela, 1 coluna, 3 linhas | L0: trivial |
| `l1_key_value()` | 1 tabela com PK, 3 linhas | L1: chave primaria |
| `l2_numeric()` | int + float, 5 linhas | L2: tipos numericos |
| `l3_multi_type()` | texto + int + float, 4 linhas | L3: tipos mistos |
| `l4_two_tables_fk()` | 2 tabelas com FK, 5+2 linhas | L4: relacional |
| `l5_rle_heavy()` | Alta repeticao FK, 10 linhas | L5: RLE |
| `l6_edge_cases()` | Zeros, negativos, grandes | L6: edge cases |

### Dados sinteticos (`tests/fixtures/synthetic.py`)

| Gerador | Descricao | Parametros |
|---------|-----------|-----------|
| `crm_sales(n, c, p, seed)` | E-commerce com FK Zipf | rows, clientes, produtos |
| `service_logs(n, seed)` | Logs API (5 status codes) | rows |
| `survey_likert(r, q, seed)` | Pesquisa Likert 1-5 | respondentes, perguntas |
| `unique_data(n, seed)` | Tudo unico (worst case RLE) | rows |

## Progressao L0-L6

Os testes seguem complexidade crescente como um manual:

```
L0: Simples  ────────────────────────>  L6: Complexo
coluna unica    PK    numeros    tipos    FK+RLE    edge cases
                                mistos
```

Cada nivel adiciona uma feature do TCF. Se L0 falhar, nada funciona.

## Resultados de benchmark

Os testes de compressao (G01b) geram um relatorio visivel com `pytest -s`:
```bash
python -m pytest tests/test_g01_compression.py::TestBenchmarkReport -s
```

Resultados completos e conclusoes cientificas (C1-C5) estao em:
- **Fonte primaria:** [article/05-results-e1-e2.md](article/05-results-e1-e2.md)
