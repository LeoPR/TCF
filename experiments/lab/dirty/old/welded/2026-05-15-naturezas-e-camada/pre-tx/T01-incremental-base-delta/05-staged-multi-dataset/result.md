# Resultado — 05-staged-multi-dataset

## Tabela consolidada

| Dataset | Linhas | Raw | Stage B | Stage C | B==C? | TCF puro | TCF de B | TCF de C | Esperado | RT |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| D11a-datas-dia | 12 | 136 | 34 | 34 | sim | 87 | 42 | **42** | 42 | OK |
| D11b-datas-borda | 14 | 158 | 45 | 45 | sim | 173 | 59 | **59** | 59 | OK |
| D11c-datas-mensal | 13 | 147 | 47 | 47 | **nao** | 109 | 53 | **22** | 22 | OK |

## Hipoteses

- **H1 (RT preservado em todos)**: CONFIRMADA (3/3 RT OK).
- **H2 (sem retrabalho)**: pipeline rodou nos 3 datasets sem alteracao nos modulos. **CONFIRMADA por construcao** (codigo copiado de sub-exp 04).
- **H3 (Stage C inocuo onde nao ha pattern)**: CONFIRMADA.
  - D11a (sem pattern mensal/anual): Stage C == Stage B? **True**
  - D11b (idem): Stage C == Stage B? **True**
  - D11c (cadencia mensal): Stage C aplicou escala? **True**
- **H4 (matching com sub-exps anteriores)**: CONFIRMADA.
  - D11a-datas-dia: tcf_c=42, esperado=42 — **MATCH**
  - D11b-datas-borda: tcf_c=59, esperado=59 — **MATCH**
  - D11c-datas-mensal: tcf_c=22, esperado=22 — **MATCH**

## Conclusao

O staged pipeline e' **dataset-independente** dentro da natureza
`date / day granularity`. Stage A identifica corretamente, Stage B
normaliza sem falha, Stage C aplica escala **so' onde existe**
pattern (D11c monthly cadence), preservando bytes onde nao existe
(D11a, D11b — Stage C passa direto sem custo).

Bytes do TCF do estagio C **batem byte-a-byte** com os encoders
monoliticos dos sub-exps 01 (42), 02 (59), 03 (22).

## Conexoes

- [`../04-staged-pipeline-D11c/`](../04-staged-pipeline-D11c/) — fonte dos modulos staged
- [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/) — referencia D11a
- [`../02-bordas-D11b/`](../02-bordas-D11b/) — referencia D11b
- [`../03-cadencia-mensal-D11c/`](../03-cadencia-mensal-D11c/) — referencia D11c monolitico
