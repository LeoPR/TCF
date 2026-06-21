# T-REGRESSION-REAL-WORLD — relatório

> Estende o regression suite byte-canonical para colunas free-text reais,
> fechando o blind spot do regime `n_tam_est >= 3` (descoberto na Fase A
> de H-PERF-06-v2). Gate obrigatório antes de weldar prune algorítmico.

## Problema

O mini-suite (`test_regression_v1_baseline.py`: D1-D9 = 1523B + D17a =
322B, todos sintéticos) **não cobre** o regime `n_tam_est >= 3` —
colunas com `atom_count` alto, onde o id virtual da composição HCC passa
a precisar de 3 dígitos. Candidato #03 (prune-k-03) da Fase A passou
D1-D9 + D17a mas **regrediu +0.59% em online-retail real**. Mesmo padrão
do incidente Pacote 2 (2026-05-21).

## Achado empírico — poder discriminante por tamanho (`probe.py`)

Rodando baseline vs #03 (known-bad) vs #15 (topK-heap) por coluna:

| Fixture | rows | #03 diverge? | #15 |
|---|---|---|---|
| committed samples (todas as colunas) | 100 | **não** | match |
| retail Description | 500 / 1000 / 2000 | +115 / +322 / **+549** | match |
| lineitem l_comment | 500 / 1000 / 2000 | +22 / +249 / **+427** | match |
| retail StockCode | 1000 / 2000 | +18 / +92 | match |
| adult occupation/education/native-country | até 2000 | **não** (low-card) | match |

Conclusões:
1. **Samples de 100 linhas não discriminam** — mesmo blind spot do
   mini-suite. O gate precisa de ≥1000 linhas de colunas **free-text**.
2. **Colunas categóricas low-cardinality** (adult) não atingem o regime —
   já cobertas pelos padrões D1-D9. Não servem de gate aqui.
3. **#15 byte-safe em todos os tamanhos/colunas** — re-validação Fase 4.

## Fixtures congeladas (`make_fixtures.py`)

Primeiros 2000 valores (ordem de inserção da fonte canônica), committados
em `datasets/samples/` (frozen, portáveis, independem de Z:):

| Fixture | coluna | fonte | baseline |
|---|---|---|---|
| `online-retail/description-2k.csv` | Description | online-retail CSV | **27581B** |
| `online-retail/stockcode-2k.csv` | StockCode | online-retail CSV | **11437B** |
| `tpch-sf001/lcomment-2k.csv` | l_comment | tpch-sf001 hub | **50598B** |

Total: **89616B**. Read-back exato verificado na geração.

## Validação (`measure_and_validate.py`)

Nas 3 fixtures committadas:
- **Discriminam #03**: +549 / +92 / +427 (o gate teria pego a regressão)
- **#15 byte-safe**: match exato em todas (re-validação Fase 4 ✓)
- **RT OK** em todas

## Entregue

- `tests/test_real_world_snapshots.py` — 7 testes (3 byte-count frozen +
  3 RT + 1 total invariant), todos verdes. Lê fixtures committadas, sem
  dependência de Z:, sem skip.
- `CLAUDE.md` — gate registrado em "Antes de declarar confirmada-empirica":
  mudança em HCC/prune deve passar os DOIS suites.
- Fixtures committadas em `datasets/samples/`.

## Fase 4 — re-validação do #15 (CONCLUÍDA)

#15 (`tier-scoring-02-topK-heap-with-safe-skip`, 1.354× na Fase A)
preserva bytes **byte-exato** nas 3 fixtures real-world do regime
`n_tam_est>=3`, além de D1-D9 + D17a. **Desbloqueado para welding** —
abrir `H-PERF-06-v2-T01` (port para src/tcf + ADR-0019).

## Limitações / honestidade

- Fixtures são "primeiros N" (determinístico/reproduzível), **não**
  amostra estatística representativa — apropriado para regression fixture
  (precisa ser estável, não representativo). Sem dependência do shaper.
- 2000 linhas escolhido por dar sinal forte (+427..+549) com tamanho de
  fixture gerenciável (~125KB total). Não testa cardinalidade extrema
  (>50k únicas) — open question herdada da Fase A.
- Adult/TPC-H categóricos low-card não entram no gate (não discriminam);
  cobertura desse regime fica no D1-D9.

## Arquivos

- `probe.py` — varredura de poder discriminante por tamanho (lê Z:)
- `make_fixtures.py` — gerador reproduzível das fixtures (lê Z:)
- `measure_and_validate.py` — mede baseline + valida #03/#15 (lê fixtures)
