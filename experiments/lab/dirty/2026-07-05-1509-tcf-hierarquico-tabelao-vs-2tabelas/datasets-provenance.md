# Proveniência dos datasets (entradas) [probatório]

**Data**: 2026-07-05 15:09. As entradas em `inputs/` são **sintéticas / artificiais, focadas na
ESTRUTURA**. A **forma** (campos, aninhamento, cadência) espelha as formas reais de API que o owner
forneceu; os **valores são inventados/anonimizados** — nenhum dado real. Auto-contido (cópias locais).

## Formas

- **S1** (request de forecast): config escalar + arrays de seleção + `observations[].points[]`.
- **S2** (série `day[]`): array de `{time,value,isOutOfRange,minValue,maxValue}`.
- **S3** (equipamento ⊃ série): a série dentro de um objeto que descreve o equipamento — **worked example**.

## Anonimização (obrigatória)

- Equipamentos `EQP_001…`; nome `Equipamento Sintetico NN`; facility/area/group `FAC_A`/`AREA_X`/`GRP_1`/`SUB_1`.
- Variável `var_a`; unidade `unit_a` (genérico — **não** copia rótulo real tipo "Accumulated KWH").
- Valores (`value`/`minValue`/`maxValue`): inventados (550.00/548.50/… com repetição+degrau). Timestamps ~15min sintéticos.

## Viés declarado

Construídos para exercitar a estrutura (cross/nesting, colunas constantes, cadência) → viés TCF-favorável
por construção nas partes cadenciadas/constantes. Ecológico na forma, **não** medição primária. Progressão
pendente: realista → bordas → extrapolação (ver README §Será).

## Determinismo

`hierlib.synth_docs` gera M equipamentos deterministicamente (sem random/clock). `run.py` regenera todos
os `artifacts/`. Origem das cópias: fixtures do estudo (antes em `2026-07-05-json-input-estudo`, removido).
