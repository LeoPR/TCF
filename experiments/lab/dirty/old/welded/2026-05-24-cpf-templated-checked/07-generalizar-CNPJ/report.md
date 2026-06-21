# Sub-exp 07 — Generalizar pra CNPJ (report)

**RT 100% em todos os 18 datasets**: True

## H3 — Categoria abstraida via mesma maquina

`TemplatedCheckedSpec` parametriza CPF e CNPJ:

| Spec | template | body_len | check_len | encoded_len |
|---|---|---:|---:|---:|
| CPF | `NNN.NNN.NNN-DD` | 9 | 2 | 5 |
| CNPJ | `NN.NNN.NNN/NNNN-DD` | 12 | 2 | 7 |

Diferencas APENAS em parametros (regex, body_length, check_fn,
formatter, encoded_length). Codigo `encode_value` / `decode_value`
/ `classify_value` 100% compartilhado. **H3 confirmada.**

## Comparacao CPF vs CNPJ

### CPF (9 datasets)

| Dataset | rows | raw | tcf | ratio | apply | RT |
|---|---:|---:|---:|---:|---:|:---:|
| D-CPF-uniform | 1000 | 15000 | 6798 | 45.32% | 100.00% | OK |
| D-CPF-clustered | 1000 | 15000 | 6895 | 45.97% | 100.00% | OK |
| D-CPF-mixed | 1000 | 13500 | 10532 | 78.01% | 50.00% | OK |
| D-CPF-corrupt | 1000 | 14985 | 7356 | 49.09% | 95.60% | OK |
| D-CPF-edge-single | 1 | 15 | 6 | 40.00% | 100.00% | OK |
| D-CPF-edge-allsame | 1000 | 15000 | 12 | 0.08% | 100.00% | OK |
| D-CPF-edge-allcorrupt | 1000 | 14750 | 19718 | 133.68% | 0.00% | OK |
| D-CPF-extra-large10k | 10000 | 150000 | 68044 | 45.36% | 100.00% | OK |
| D-CPF-extra-hostile | 1000 | 10938 | 11356 | 103.82% | 25.00% | OK |

### CNPJ (9 datasets)

| Dataset | rows | raw | tcf | ratio | apply | RT |
|---|---:|---:|---:|---:|---:|:---:|
| D-CNPJ-uniform | 1000 | 19000 | 8670 | 45.63% | 100.00% | OK |
| D-CNPJ-clustered | 1000 | 19000 | 7469 | 39.31% | 100.00% | OK |
| D-CNPJ-mixed | 1000 | 17000 | 12957 | 76.22% | 50.00% | OK |
| D-CNPJ-corrupt | 1000 | 18989 | 9510 | 50.08% | 94.80% | OK |
| D-CNPJ-edge-single | 1 | 19 | 9 | 47.37% | 100.00% | OK |
| D-CNPJ-edge-allsame | 1000 | 19000 | 15 | 0.08% | 100.00% | OK |
| D-CNPJ-edge-allcorrupt | 1000 | 18750 | 24753 | 132.02% | 0.00% | OK |
| D-CNPJ-extra-large10k | 10000 | 190000 | 86795 | 45.68% | 100.00% | OK |
| D-CNPJ-extra-hostile | 1000 | 13438 | 13338 | 99.26% | 25.00% | OK |

## Observacoes

- CPF e CNPJ tem perfis de compressao similares — confirma que
  pertencem a mesma categoria comportamental.
- CNPJ uniform/clustered/large10k esperado em ~45-50% (similar CPF).
- edge-allsame ambos brilham (RLE HCC).
- edge-allcorrupt + extra-hostile ambos pioram — mesma heuristica
  de aplicacao serve.

## Conclusao

`TemplatedCheckedSpec` valida-se como abstracao da categoria.
CNPJ welded com zero codigo novo alem da spec. **H3 confirmada.**

Proximos: sub-exp 08 (IP TCU-Delta) testa categoria com
SlotBehavior heterogeneo — proxima generalizacao.

