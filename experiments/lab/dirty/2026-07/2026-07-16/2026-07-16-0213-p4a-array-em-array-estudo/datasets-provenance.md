# Proveniência das entradas

Sintéticas, **didáticas** — viés total declarado (construídas para o GATE do checkpoint
2026-07-16 do owner; material de FORMA/contrato, não medida de ganho).

- `inputs/01-didatico-array-em-array.json` — 12 formas do gate: básico `[[1,2],[3]]`, matriz
  retangular, profundidade 3, inners vazios, `[]`≠`[[]]`≠`[[1]]`, arrays de arrays de OBJETOS,
  null ENTRE arrays (P3b∘P4a externo), null DENTRO do inner (P3b interno), compose total
  (P2+P3b+P4a: nulls em 2 níveis + typed + campos irmãos), strings/bool aninhados, campo
  array-em-array no meio de outros campos.
- **Fuzz** (`study.py`): seedado (`random.Random(20260716)`), profundidade 1–4, ~20% null por
  nível, elementos n/b/s. 4000 docs.
- **Adversarial**: frames mutilados (count interno truncado/excedente, folha faltando/sobrando)
  construídos por mutação das colunas do próprio encode.

Roundtrip diffável em `outputs/01-*-rt.json` (vs `intermediates/01-*.json`). Validação real +
byte-custo = fase do weld (padrão P1/P3/P2), após inspeção da gramática pelo owner.
