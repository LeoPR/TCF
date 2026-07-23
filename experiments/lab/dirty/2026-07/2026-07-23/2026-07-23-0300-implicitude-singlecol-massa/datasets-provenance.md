# Proveniência — single-column em massa por tipo

**Origem**: 100% sintético/determinístico (seed 20260723 pros aleatórios; fórmulas fixas pro resto).
Nenhum dado real, nenhum download. N=500 por caso.

**Viés declarado**: dados construídos pra cobrir os REGIMES de cada tipo (sequencial/aleatório/
repetido pro int; baixa/alta cardinalidade pra string) — pra ver comportamento de wire, não pra
medir compressão de produto. Volume moderado (massa suficiente pra o overhead FIXO do `.8H` aparecer
diluído nas colunas grandes e dominante nas pequenas).

**Placeholders sensíveis**: CPF = dígitos repetidos mod-11-válidos (`111.111.111-11`…), nunca reais;
CNPJ = synthetic DV-válido não-vinculado; IP = faixa privada `10.x.x.x`. Mesma convenção do catálogo
`2026-07-23-0204` e da suíte.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte. RT provado em `outputs/*.roundtrip.json`
(== ao input E ao RT do JSON). Bytes só reportados com equivalência ✅.
