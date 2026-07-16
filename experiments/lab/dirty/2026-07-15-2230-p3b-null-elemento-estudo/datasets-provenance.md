# Proveniência das entradas

Sintética, **didática** — viés total declarado (construída pra FORÇAR cada forma de null-em-elemento,
pra inspeção/prova de conceito; não é medida de ganho).

- `inputs/01-didatico-null-elemento.json` — 8 formas: null no meio/início/fim, array todo-null,
  vazio vs `[null]` vs `[valor]`, elemento-OBJETO null, 4-vias no elemento (null/`""`/`"null"`/valor),
  duas listas (só uma com null), e aninhamento (array em objeto em array). Cada uma isola um aspecto
  do alinhamento count×emask×dense.

Sem dado real neste estudo (validação real = fase do weld, padrão P3a: didático→realista→massa com
receita-cnpj/etc., RT obrigatório + gate byte-canônico). Roundtrip diffável em `outputs/*-rt.json`.
