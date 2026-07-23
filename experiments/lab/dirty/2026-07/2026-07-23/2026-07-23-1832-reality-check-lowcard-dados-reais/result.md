# Reality-check — seg-adapt em colunas REAIS low-card (adult-census)

Amostra: primeiras 10000 linhas de adult.csv (REAL, Z:/tcf-data). Kit `pecas.py` (lab 1759). `mean_run` = comprimento médio de run (≈1 = ruído; grande = clusterizado). `Δadapt` = seg-adapt − melhor modo único (<0 = seg-adapt ganha). Duas ordens: as-is (natural) e sorted.

| coluna | ordem | k | w | nruns | mean_run | dense | rle | seg-adapt | vencedor | Δadapt | RT |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|---:|:---:|
| sex | as-is | 2 | 1 | 4446 | 2.2 | 1668 | 17844 | 1675 | dense | +7 | ✅ |
| sex | sorted | 2 | 1 | 2 | 5000.0 | 1668 | 13 | 15 | rle | +2 | ✅ |
| class | as-is | 2 | 1 | 3612 | 2.8 | 1668 | 14602 | 1675 | dense | +7 | ✅ |
| class | sorted | 2 | 1 | 2 | 5000.0 | 1668 | 13 | 15 | rle | +2 | ✅ |
| race | as-is | 5 | 4 | 2490 | 4.0 | 6668 | 10272 | 7095 | dense | +427 | ✅ |
| race | sorted | 5 | 4 | 5 | 2000.0 | 6668 | 29 | 34 | rle | +5 | ✅ |
| relationship | as-is | 6 | 4 | 7414 | 1.3 | 6668 | 29655 | 6681 | dense | +13 | ✅ |
| relationship | sorted | 6 | 4 | 6 | 1666.7 | 6668 | 39 | 45 | rle | +6 | ✅ |
| marital-status | as-is | 7 | 4 | 6719 | 1.5 | 6668 | 26877 | 6714 | dense | +46 | ✅ |
| marital-status | sorted | 7 | 4 | 7 | 1428.6 | 6668 | 42 | 49 | rle | +7 | ✅ |
| workclass | as-is | 9 | 4 | 5139 | 1.9 | 6668 | 20620 | 7068 | dense | +400 | ✅ |
| workclass | sorted | 9 | 4 | 9 | 1111.1 | 6668 | 50 | 65 | rle | +15 | ✅ |
| occupation | as-is | 15 | 4 | 9034 | 1.1 | 6668 | 38037 | 6675 | dense | +7 | ✅ |
| occupation | sorted | 15 | 4 | 15 | 666.7 | 6668 | 97 | 115 | rle | +18 | ✅ |
| education | as-is | 16 | 4 | 8116 | 1.2 | 6668 | 33328 | 6682 | dense | +14 | ✅ |
| education | sorted | 16 | 4 | 16 | 625.0 | 6668 | 102 | 118 | rle | +16 | ✅ |
| native-country | as-is | 41 | 8 | 1867 | 5.4 | 13336 | 8254 | 9049 | rle | +795 | ✅ |
| native-country | sorted | 41 | 8 | 41 | 243.9 | 13336 | 223 | 266 | rle | +43 | ✅ |

## Leitura — o regime vencedor existe em dados reais?

- **seg-adapt vence em 0/9 colunas na ordem AS-IS** (natural). Ver `mean_run`: se ≈1, a coluna é RUÍDO (linhas consecutivas descorrelacionadas) → whole-dense vence e seg-adapt é peso morto. É o caso esperado de dados não-ordenados.
- **Comparar as-is vs sorted**: ordenar cria runs longos (`mean_run` sobe muito) → vira regime RUNNY → whole-rle domina. O 'misto genuíno' (onde seg-adapt ganha) é uma faixa ESTREITA entre ruído puro e ordenado puro — raro de ocorrer naturalmente.
- **Implicação pro weld**: se dados reais não-ordenados são ruído-por-coluna, o seg-adapt quase nunca dispara e o FLOOR cai no whole-dense/rle. O valor do seg-adapt depende de os dados serem clusterizados-mas-não-ordenados — que existe (dados agrupados por categoria), mas não é o default. Decide se o misto vale o custo de código.
- **O verdadeiro achado**: em dados reais a decisão é BIMODAL — ruído→dense(bN), clusterizado/ordenado→rle — e a escolha por coluna é o FLOOR/min que o TCF já tem. A SEGMENTAÇÃO (seg-adapt) não acrescenta nada: 0/18 vitórias. O misto é artefato sintético.
- **A alavanca real é ordenar+RLE**: education 6668→102 quando ordenado (65×). Mas isso é whole-rle + uma decisão de SORT, não segmentação. Onde há valor real de weld é o par {modo denso bN, modo rle} competindo no FLOOR por coluna — não a máquina de segmentos.
- **RESSALVA (não medido aqui)**: este lab compara os protótipos entre si (dense/rle/seg-adapt), NÃO contra o encoder ATUAL do TCF (dict/V2-B base-94). Se o denso-bN base64 bate o dict/V2-B de hoje é uma medição SEPARADA — este reality-check só derruba a segmentação, não estabelece que bN-dense é ganho vs o TCF vigente.

**9 colunas × 2 ordens · 0 falhas (RT + passe único).** Amostra N=10000. Regenera: `python run.py`.