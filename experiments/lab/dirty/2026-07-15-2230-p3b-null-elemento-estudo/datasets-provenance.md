# Proveniência das entradas

Sintética, **didática** — viés total declarado (construída pra FORÇAR cada forma de null-em-elemento,
pra inspeção/prova de conceito; não é medida de ganho).

- `inputs/01-didatico-null-elemento.json` — 8 formas: null no meio/início/fim, array todo-null,
  vazio vs `[null]` vs `[valor]`, elemento-OBJETO null, 4-vias no elemento (null/`""`/`"null"`/valor),
  duas listas (só uma com null), e aninhamento (array em objeto em array). Cada uma isola um aspecto
  do alinhamento count×emask×dense.

- `inputs/02-realista-telemetria.json` — **REALISTA** (weld): telemetria com `leituras` (array de
  objetos, com elemento null E campo interno `umid` null) + `alertas` (array de escalares com null).
  Sintético-realista; exercita element-object-null + P3a compondo, plausível de IoT/logs.
- **MASSA** (weld, `run_weld.py`): fuzz seedado (`random.Random(20260715)`), ~30% dos elementos null,
  arrays de escalar E de objeto, schema fixo por batch (in-class). 6000 docs. Cobertura reportada.

Roundtrip diffável em `outputs/*-rt.json`. O `proto.py` (estudo) e o `run_weld.py` (evidência do core)
são distintos: o estudo extraiu a IDEIA; o weld usa o `src/tcf` real.
