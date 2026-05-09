# Lab didatico: efeitos das chaves em diferentes graus (refeito 2026-05-05)

## Objetivo

Mostrar visualmente como o encoder TCF v0.4 trata cada grau de chave
(0, 1, 2, 3) com a **forma vencedora** ja consolidada — sem
comparacoes obsoletas.

## Forma vencedora aplicada

Conforme decisoes consolidadas no recap (D1-D16):

- **DICT inline** com a coluna (nao no header da tabela)
- **PK grau 2 → eliminar** (regenera no decode)
- **PK grau 0/1 → preservar** valor exato
- **PK grau 3 → reconstruir** sob demanda
- **Auto-bypass** L3 quando cardinality > N/2

## Comparacoes EXCLUIDAS (obsoletas)

Nao re-comparamos:

- L3 preservando PK grau 2 (sempre perde para eliminar)
- DICT em colunas com cardinality alta (sempre perde para bypass)
- DICT no header (sempre perde para inline)
- Sort lexicografico em ints (sempre perde para numerico)

Quem quiser historico: `git log -- experiments/lab/dirty/2026-05-02-*`.

## Cenarios

| # | Tipo de chave | Grau | Acao |
|---|---------------|------|------|
| S0 | sem PK (so dados) | — | direto |
| S1 | PK int auto-increment | 2 | ELIMINAR |
| S2 | PK UUID universal | 0 | PRESERVAR (valor exato) |
| S3 | PK natural (PED-NNNN) | 1 | PRESERVAR + Affix-DICT (Proposta H) |
| S4a | PK hash 12 hex (api-facing) | 0 | PRESERVAR |
| S4b | PK hash 12 hex (interno) | 3 | RECONSTRUIR |

## Comparacao unica

Cada cenario: **naive (referencia) vs forma-vencedora-aplicada**.

Sem mais "L3 versus naive" desnecessario — quem importa eh o ganho
final do TCF v0.4 na configuracao certa.

Saida: `./output/`
