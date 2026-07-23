# Proveniência — reality-check low-card dados reais

**Origem**: adult-census REAL — `Z:/tcf-data/external/adult-census/adult.csv` (48.842 linhas). Dataset
canônico do projeto; nenhum download (regra: usar `Z:/tcf-data/`). **Amostra**: primeiras 10.000
linhas (reality-check, não medição massiva) — declarado no result.md.

**Colunas medidas** (9 categóricas low-card, cobrindo w=1..8):
sex/class (k=2, w1) · race (5) · relationship (6) · marital-status (7) · workclass (9) · occupation
(15) · education (16) · native-country (41, w8). Valores como estão no CSV (strings), sem limpeza.

**Duas ordens** por coluna: `as-is` (ordem natural das linhas do CSV — o que o TCF receberia) e
`sorted` (`sorted(vals)` — simula clusterização/ordenação total). Isola o efeito da ORDEM no regime.

**Sem dados sensíveis**: adult-census é público (UCI); colunas categóricas demográficas, sem PII
individual reconstruível (nomes/ids não estão nas colunas medidas).

**Reprodutibilidade**: `python run.py` regenera determinístico (amostra = primeiras N, sem aleatório).
RT dos 3 modos → índices → domínio → valores == original, por coluna. Kit `pecas.py` do lab 1759
(passe único provado pela Fonte instrumentada). Bytes só com RT ✅.
