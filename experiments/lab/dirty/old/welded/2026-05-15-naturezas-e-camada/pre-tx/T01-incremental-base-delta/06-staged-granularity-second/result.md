# Resultado — 06-staged-granularity-second

Pipeline staged estendido pra suportar **granularidade segundo**
alem de dia. Validado em 4 datasets (3 day backward compat + 1
second novo).

## Tabela consolidada

| Dataset | Granul. | Linhas | Raw | B inter | C inter | B==C? | TCF puro | TCF B | TCF C | Esperado | RT |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| D11a-datas-dia | day | 12 | 136 | 34 | 34 | sim | 87 | 42 | **42** | 42 | OK |
| D11b-datas-borda | day | 14 | 158 | 45 | 45 | sim | 173 | 59 | **59** | 59 | OK |
| D11c-datas-mensal | day | 13 | 147 | 47 | 47 | **nao** | 109 | 53 | **22** | 22 | OK |
| D11d-datetime-min | second | 13 | 264 | 56 | 56 | **nao** | 110 | 34 | **34** | — | OK |

## Hipoteses

- **H1 (RT preservado em todos os 4 datasets)**: CONFIRMADA.
- **H2 (backward compat: D11a/b/c batem byte-exato com sub-exps anteriores)**: CONFIRMADA.
- **H3 (Stage A identifica granularity=second em D11d)**: CONFIRMADA.

## Observacoes

- **D11d** (minute cadence em second granularity): Stage C aplica escala `1m`? sim.
- TCF de B (em segundos `60` repetido) e TCF de C (em `1m` repetido) tem tamanhos similares — ambos compactam via repeticao no HCC. Ver `outputs/D11d-datetime-min/`.

## Linguagem das escalas (cumulativo apos sub-exps 03-06)

- Sem letra = unidade base detectada em A (dia ou segundo).
- `Y` = ano, `M` = mes (capital pra distinguir de minuto).
- `D` = dia (so' quando granularity=second).
- `h` = hora, `m` = minuto (so' quando granularity=second).
- Sinal `-` explicito pra negativos.

## Proximos passos pendentes (escopo NAO deste sub-exp)

- Granularidade milissegundo / microssegundo / nanossegundo (sufixos multi-char `ms`/`us`/`ns`)
- Timezone handling
- Mixed-granularity (logs com timestamps + IDs em mesma coluna — improvavel pela diretriz dados-realistas)

## Conexoes

- [`../05-staged-multi-dataset/`](../05-staged-multi-dataset/) — generalizacao day-only
- [`../04-staged-pipeline-D11c/`](../04-staged-pipeline-D11c/) — staged inicial
