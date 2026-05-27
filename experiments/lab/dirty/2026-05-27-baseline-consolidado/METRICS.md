# METRICS — Baseline canonical 2026-05-27

> Source of truth pra **bytes-canonical de referencia**. Atualizar
> quando ADR novo entrar (ver `run-baseline.py` pra regenerar).

## D1-D9 sinteticos (single-column)

Baseline M10 (ADR-0011) + features unificadas (ADR-0008/0010 +
ColumnFeatures). RT 9/9.

Medido via `python run-baseline.py D1-D9` em 2026-05-27.
`raw_bytes` = sum(len(v.encode('utf-8'))) sem newlines.

| Dataset | raw_bytes | tcf_bytes | ratio | obs |
|---|---|---|---|---|
| D1-emails-simples    | 179 | 118 | 65.9% | base |
| D2-emails-quote-id   | 235 | 166 | 70.6% | quote-id |
| D3-stress-substring  | 332 | 177 | 53.3% | stress LCP/LCS |
| D4-caos-mix          | 144 | 113 | 78.5% | mix patterns |
| D5-padroes-multiplos | 406 | 281 | 69.2% | HCC ganha |
| D6-poucos-em-ruido   | 521 | 287 | 55.1% | ruido domina |
| D7-aninhamento       | 325 | 215 | 66.2% | virtual refs |
| D8-cabeca-cauda      | 372 | 100 | 26.9% | bidir affixes (D8 + D9 puxam media baixa) |
| D9-frequencia-alta   | 351 |  66 | 18.8% | seq-RLE essencial |
| **TOTAL**            | **2865** | **1523** | **53.2%** | **M10 baseline** |

Source: Re-rodar `python run-baseline.py D1-D9`.

## D17a multi-column INVARIANT

D17a-multi-column-mixed.csv (13 linhas x 4 colunas).

| Format | Bytes | obs |
|---|---|---|
| raw csv | ~450 | header + dados |
| tcf single-col concat | ~480 | sem ganho cross-col |
| **tcf multi-col canonical** | **322B** | **INVARIANT preservado em 16 ADRs** |

**Critico**: Qualquer mudanca em `src/tcf/` que quebre 322B = regressao.
Test: `tests/test_pipeline_config.py::test_d17a_default_invariant`.

## Real-world (Adult Census + TPC-H tier 1+2)

9 tabelas, 57 colunas total, 136k linhas.

| Source | Raw | TCF | Ganho |
|---|---|---|---|
| Adult Census (1 tabela, 15 cols, 32k) | ~6.5MB | ~4.3MB | -34% |
| TPC-H tier 1 (5 tabelas, 42 cols, 100k) | ~28MB | ~19MB | -33% |
| TPC-H tier 2 (3 tabelas) | ~10MB | ~6.7MB | -32% |
| **Weighted total** | **~44.5MB** | **~30MB** | **-33.02%** |

RT: 57/57 colunas exactas.

Source: `experiments/lab/dirty/old/welded/2026-05-23-multi-column-scaling/`.

## Real-world adicionado (T-DATA-1, 2026-05-27)

3 datasets UCI/OpenML cobrindo dominios distintos:

| Dataset | Rows | Cols | Raw | TCF | Ratio | enc/dec | RT |
|---|---|---|---|---|---|---|---|
| wine-quality        |   6.497 | 13 |   322KB |   293KB | **90.9%** |  2.0s /  0.1s | OK |
| beijing-pm25        |  43.824 | 13 |  1.40MB |   977KB | **71.7%** |  7.5s /  0.6s | OK |
| online-retail       | 541.909 |  8 |  41.7MB |  9.87MB | **23.7%** | 90.3s /  3.3s | OK |

**Insights**:
- **online-retail**: dominio comercial — InvoiceDate cadenced, StockCode/
  Country/Description repetidos. TCF brilha (HCC seq-RLE + dedup).
- **beijing-pm25**: sensores cientificos — timestamps periodicos +
  valores decimais com repeticao parcial. Ratio medio.
- **wine-quality**: decimais quimicos quase unicos por linha. TCF perde
  pouco (pre-pass nao decide nada), mas overhead minimo.

**Bug descoberto durante validacao** (2026-05-27): encoder seq-RLE
multi-delta emitia marker `*N+-1,0|...` (primeiro delta negativo
double-signed), decoder falhava. Fix em `src/tcf/composicional/
hcc_seqrle.py` linha 207. 2 testes regressao adicionados em
`tests/test_hcc_multi_delta.py`. D1-D9 1523B e D17a 322B preservados.

## Suite regressao formal

`tests/test_regression_v1_baseline.py` (21 tests):
- D1-D9 byte-count snapshot (frozen): 9 datasets × snapshot exact bytes
- D1-D9 round-trip: 9 datasets × decode == values
- D1-D9 total: 1523B invariant
- D17a 322B INVARIANT exato + round-trip

Falha em qualquer test = regressao byte-canonical. Atualizar snapshot
requer welding deliberado + ADR.

## Benchmark formats x compression

Sub-exp `2026-05-24-benchmark-formats-compression/` (6 datasets,
formats csv/json/tcf, compression none/gzip/brotli/zstd).

| Dataset | Vencedor | Bytes | Runner-up |
|---|---|---|---|
| D-CPF 1000 | tcf+nature+brotli | ~3.2KB | csv+brotli ~5.1KB |
| D-IP-subnet 1000 | tcf+nature+brotli | 0.4KB | csv+zstd 2.8KB |
| D-IP-random 1000 | tcf+brotli | 4.2KB | csv+brotli 4.5KB |
| D-Adult 32k | tcf+brotli | ~960KB | csv+brotli ~1.1MB |
| D-Lineitem 60k | csv+brotli | ~4.2MB | tcf+brotli ~4.4MB |
| D-Customer 60k | csv+brotli | ~890KB | tcf+brotli ~920KB |

TCF vence em **4/6** datasets, pos ADR-0015 + ADR-0016.

## Cadeia byte-canonica (preservada via testes)

- M9 -> M10 -> M11 -> M12 -> M13 -> M14 -> M14+pacote1-weld
  -> +multi-col -> +API-unificada -> +natures -> +multi-delta

Cada bullet acima e' **byte-identico ao anterior em D1-D9 single-col**
(tests `test_pipeline_config.py::TestPipelineConfigD1D9Invariant`).

## Reproduzir

```bash
python experiments/lab/dirty/2026-05-27-baseline-consolidado/run-baseline.py
# Outputs em outputs/<dataset>/<dataset>.tcf
# Bytes printados; comparar com tabelas acima
```

## Quando bytes baterem regressao

Investigar via:
1. `git log -p src/tcf/` desde commit que welded ADR responsavel
2. Re-rodar test suite: `pytest tests/test_pipeline_config.py`
3. Comparar `.tcf` byte-a-byte com baseline anterior (em `old/welded/`)

## Quando bytes baterem ganho

1. Verificar que e' ganho real (RT preservado em todos datasets)
2. Abrir sub-exp documentando hipotese implicita responsavel
3. Considerar welding via ADR novo
