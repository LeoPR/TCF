# Proveniência — decisão RLE-vs-denso passe único

**Origem**: 100% sintético/determinístico. Nenhum dado real, nenhum download. O `noisy` usa um LCG
local (seed 987654321), reprodutível byte-a-byte, sem `random` global. Domínio bool, bit1=true.

**Dados PEQUENOS de propósito** (viabilidade efêmera, não medição de produto). Dimensionados para
**exercitar os 3 regimes** e forçar cada modo a vencer em alguma linha — o ponto é mostrar que a
decisão MUDA de vencedor e que o preditor acerta, não medir taxa de compressão:
- `const-sm` (n=24) — piso do denso vence (base64 de ≤24 bits = 4 chars).
- `const-big` / `few-big` (n~300, poucos runs) — RLE vence.
- `alt-big` / `noisy` (muitos runs) — denso vence.
- `prefix-mix` (run longo + ruído) — misto vence.

**Reprodutibilidade**: `python run.py` regenera. Cada modo tem RT provado (decode==orig==json_rt);
a fonte é instrumentada (contador de leituras) para provar passe único (`reads/n==1.0`). Bytes só
reportados com o preditor batendo o real e RT ✅.
