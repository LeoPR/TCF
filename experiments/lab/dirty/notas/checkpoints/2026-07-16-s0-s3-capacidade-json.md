# Checkpoint 2026-07-16 — S0–S3 capacidade JSON e álgebra de vínculos

## Estado confirmado

- Programa adotado: primeiro capacidade semântica, depois simplificação física.
- S0 contrato/corpus: executado.
- S1 codec-oráculo explícito: executado.
- S2 IR de nós, arestas e lanes: executado.
- S3 counts/offsets/parent-index/steps: executado.
- Gate: 20/20 RT, 20/20 álgebras, 8/8 fail-loud, round-trip canônico byte-idêntico.
- `src/tcf`: intocado.

Fonte probatória: [lab S0–S3](../../2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/).

## Hipóteses após o gate

- `H-DATASETH-COMPLETE-01`: confirmada-conceitual, confiança Média.
- `H-HIER-LINK-ALGEBRA-01`: confirmada-conceitual, confiança Média.
- `H-HIER-BOUNDARY-EMPTY-01`: confirmada-conceitual por contraprova, confiança Alta no modelo.

Limite: corpus sintético de design. Não há decisão sobre wire, header, bytes, desempenho ou weld.

## Problema que não pode ser esquecido

Um bit `first-child` sem step/skip perde pais vazios intermediários: parent-index `[0,2,2]` e
`[0,1,1]` colidem em `[start,start,continue]`. Qualquer candidato S4 precisa carregar o salto, um
bitmap de vazios ou informação equivalente.

## Retomada

1. Abrir lab S4 separado; não ampliar o lab S0–S3 já fechado.
2. Produzir wires reais lado a lado para counts, offsets, parent-id, rep/def-level, tabelão/RLE e eventos.
3. Reconstruir todos pelo mesmo oráculo S1 e pelo mesmo corpus antes de medir bytes.
4. Em S5, declarar o DAG de dependências de decode/busca e medir sincronização, lazy e paralelismo.
5. Só em S6 comparar os headers; só em S7 recomendar default/fallback e discutir weld.

Tickets de retomada:

- [semântica/oráculo](../../../../../tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md);
- [álgebra e S4–S7](../../../../../tickets/T-STUDY-HIERARCHY-LINK-ALGEBRA.md);
- [execução S0–S3](../../../../../tickets/T-EXP-DATASETH-S0-S3.md).
