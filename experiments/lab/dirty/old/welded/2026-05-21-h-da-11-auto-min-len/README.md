# Lab dirty — H-DA-11 auto-detect min_len (2026-05-21)

**Ticket**: [T-EXP-H-DA-11](../../../../tickets/T-EXP-H-DA-11.md)

**Origem**: hipotese decorrente da revalidacao H-DA-10 em
`2026-05-21-revalidacao-categoria-B/03-h-da-10-min-len-realworld/`
(ticket T-REVAL-H-DA-01-06-10).

Sub-exp 03 mostrou **9.92% ganho weighted** se min_len otimo escolhido
por coluna em Adult+TPC-H. Default min_len=3 deixa esse ganho na mesa.

**Pergunta**: heuristica simples (avg_len + cardinalidade + is_numeric)
captura quanto do oracle 9.92%?

## Sub-exps planejados

1. **`01-analise-features/`** — extrair features (avg_len, card, is_num)
   por coluna; identificar regras de classificacao simples.
2. **`02-heuristica-v1/`** — implementar + validar heuristica v1
   (decision tree shallow); comparar 3-way (oracle/heuristica/default).

## Criterio de sucesso

Heuristica captura >= 50% do oracle (i.e., >= 5% weighted real-world).

## Conexoes

- [Ticket T-EXP-H-DA-11](../../../../tickets/T-EXP-H-DA-11.md)
- [Sub-exp H-DA-10 (oracle source)](../2026-05-21-revalidacao-categoria-B/03-h-da-10-min-len-realworld/result.md)
- [Revisao conceitual](../notas/revisao-conceitual-2026-05-21.md)
