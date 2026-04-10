# Retail Sales Synthetic (poor reference)

Dataset minimalista gerado por `tests/fixtures/synthetic_v2.py`. Usa
nomes como "Ana", "Bruno", "Caneta" — o tipo de dado "pobre" que muitos
papers de LLM+table usam.

## Por que esta na pasta `poor-reference/`

Em 2026-04-10, decidimos adotar datasets canonicos (TPC-H, Adult) como
base principal do projeto. Este dataset foi movido conceitualmente para
"poor reference": util apenas para **comparacao com literatura** que usa
dados similares, nao como baseline cientifico.

## Onde viver o codigo

O gerador ainda esta em `tests/fixtures/synthetic_v2.py` (nao foi
movido fisicamente — continua sendo usado por alguns testes legacy).

**Nao use este dataset para novos experimentos.** Use `tpch-sf001` ou
`adult-census` em `datasets/canonical/`.

## Quando pode ser util

1. **Comparacao com literatura antiga:** se um paper reporta resultados
   em um sintetico similar, podemos rodar aqui para validar.
2. **Testes unitarios:** dados pequenos e deterministas sao uteis em
   testes automatizados.
3. **Demos:** por ser pequeno, e facil de mostrar em documentacao.

## Historia

Ate 2026-04-10, este dataset era o **principal** do projeto. Todos os
findings F30-F103 foram gerados sobre ele. Apos a decisao de reiniciar
com datasets canonicos, os findings atuais foram mantidos como
"baseline metodologico" (mostra que o pipeline funciona) mas nao como
evidencia final para o paper.

Ver [docs/research-notes/2026-04-10-critical-review.md](../../../docs/research-notes/2026-04-10-critical-review.md)
para o raciocinio completo.
