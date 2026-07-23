# Proveniência — escada de implicitude do bool

**Origem**: 100% sintético/determinístico. N=500 por dataset. Nenhum dado real, nenhum download.
Os aleatórios usam um **LCG local** (`_lcg_bits`, seed 1234567) — reprodutível byte-a-byte, sem
`random` global.

**Datasets (regimes de entropia, propositais)**:
- `alt` — alternado periódico (p=2): pior caso pra RLE, âncora da pergunta base64.
- `all-true` — 1 run: melhor caso pra RLE e pro `.8H` atual (constante).
- `most-true` — 95% true, runs longos.
- `rand-50` / `rand-10` — ~50% / ~10% true: alta entropia, onde o bit-pack tende a ganhar.

**Viés declarado**: dados construídos pra varrer os REGIMES (entropia baixa→alta), não pra medir
produto — o objetivo é ver onde cada forma ganha/perde. Bit1=true é convenção do lab.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte. RT provado por forma (`decode==orig==
json_rt`); bytes só reportados com equivalência ✅. `gzip` é sinal de transporte, não critério.
