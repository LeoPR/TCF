# Sub-exp 05 — Fallback marker (report)

**Data**: 2026-05-24
**Status**: completed — **RT 100% em TODOS os 9 datasets**

## Objetivo

Resolver o RT FAIL das variantes B/C (sub-exps 03/04) em datasets
dirty (corrupt_check causava silent data corruption).

## Solucao implementada

- Marker prefix `_` distingue literal vs compressed
- Encoder pre-tx STRITTA: classifica cada valor; so' encoda
  `compressible` (formato OK + check valido)
- Outros casos viram `_<original>` literal
- Decoder distingue por prefixo

## Resultados (etapas 1, 3, 4 da progressao dirty)

| Dataset | Etapa | rows | raw | tcf | ratio | RT | Compressible | Outros |
|---|---|---:|---:|---:|---:|:---:|---:|---|
| uniform | 1 | 1000 | 15000 | **6798** | **45.32%** | 1000/1000 | 1000 | — |
| clustered | 1 | 1000 | 15000 | **6895** | **45.97%** | 1000/1000 | 1000 | — |
| mixed | 1 | 1000 | 13500 | 10532 | 78.01% | 1000/1000 | 500 | format_unmasked=500 |
| corrupt | 1 | 1000 | 14985 | 7356 | 49.09% | 1000/1000 | 956 | format_mismatch=18, length=15, check=11 |
| edge-single | 3 | 1 | 15 | 6 | 40% | 1/1 | 1 | — |
| edge-allsame | 3 | 1000 | 15000 | **12** | **0.08%** ⚡ | 1000/1000 | 1000 | RLE explosivo |
| edge-allcorrupt | 3 | 1000 | 14750 | 19718 | **133.68%** ⚠ | 1000/1000 | 0 | check=250, format=500, length=250 |
| extra-large10k | 4 | 10000 | 150000 | 68044 | 45.36% | 10000/10000 | 10000 | — |
| extra-hostile | 4 | 1000 | 10938 | 11356 | 103.82% ⚠ | 1000/1000 | 250 | check=63, format=125, length=312, empty=250 |

## Observacoes

### O bom

1. **RT 100% em TODOS os 9 datasets** — incluindo corrupt, edges, hostis.
   Objetivo principal atingido: **zero silent data corruption**.
2. **Compressao mantida em compressible-heavy**: uniform/clustered/extra-large10k
   ficam em ~45% (similar variante B sem fallback). Penalidade do marker
   negligenciavel quando maioria comprime.
3. **edge-allsame eh wow**: 1000 CPFs identicos -> 12 bytes (0.08%). HCC
   RLE captura repeticao perfeita. Independe de pre-tx CPF.
4. **Comportamento honesto em edges**: ratio reflete realidade, sem
   "fake compression" via data corruption.

### O ruim (visivel e documentado)

5. **edge-allcorrupt: 133% ratio** — todos viram literal com marker
   `_` (+1 byte cada). Pior que raw. Esperado.
6. **extra-hostile: 103.82%** — 75% fallback literal. Pra esses casos,
   melhor nem aplicar pre-tx CPF.

### Implicacao pratica

- **Heuristica de aplicacao**: so' aplicar pre-tx CPF se
  `n_compressible / n_total >= ~50%` (a determinar empiricamente).
  Caso contrario, M10 puro (sub-exp 01) eh melhor.
- Schema builder Fase 3 deve detectar essa heuristica antes de
  populador `column.natures = ["cpf"]`.

## Outputs visiveis (auditoria)

`out_tcf/` contem por dataset:
- `<dataset>.tcf` — encoded
- `<dataset>-pretx-sample20.txt` — 20 valores com classificacao
  (`compressible` / `check_invalid` / `format_mismatch` / etc.)
- `<dataset>-decoded-sample20.txt` — RT marker per linha
- (se houvesse mismatches) `<dataset>-mismatches.txt` — lista completa
  (vazio em todos: RT 100%)

## Conclusao

Variante B+fallback (sub-exp 05) **substitui** variante B pura
(sub-exp 03) como vencedora **segura** pra real-world. Pre-requisitos:

1. **Heuristica de aplicacao**: detectar se vale a pena (% compressible)
2. **Schema builder integration**: detect_templated_checked alimenta
   `column.natures` se heuristica positiva

## Proximos passos

- Sub-exp 06: NatureApplyStats estruturado em SideOutputs
- Sub-exp 07: generalizar pra CNPJ (mesma maquina, params diferentes)
- Sub-exp 08: IP TCU-Delta (SlotBehavior heterogeneo)
