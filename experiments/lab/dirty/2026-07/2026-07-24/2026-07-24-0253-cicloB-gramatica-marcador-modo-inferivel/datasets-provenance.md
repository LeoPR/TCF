# Proveniência — gramática do marcador de modo

**Fonte**: 100% sintético/determinístico, `inputs/*-fonte.json`. Nenhum dado real, sem `random` global
(perfil aleatório via LCG local seed fixa). Bool `w=1`.

**Datasets (amostram os comportamentos-fronteira da GRAMÁTICA)**:
- `n1-true` / `n1-false` — **as colisões**: core=`'true'`/`'false'`, alfabeto base64 puro.
- `n2-alt` — core multi-linha (não colide).
- `all-true` — core=`'*8|true'` (marcador `*` quebra base64).
- `n8-alt` / `n9-alt` — fronteiras de padding do bit-pack (8 bits=1 byte, 9 bits=2 bytes).
- `p50-64` — denso favorável; `runs-64` — core/RLE favorável.

**O que se mede** (não é sobre COMPRESSÃO, é sobre GRAMÁTICA): (1) o modo é distinguível pela forma do
corpo? (2) `n` é dedutível em cada modo? (3) RT das 3 gramáticas candidatas; (4) teste decisivo:
forçando core nas colisões, a dedução por forma (G3) quebra?

**Protótipos lab-local**: os corpos usam `encode`/`decode` REAIS do `src/tcf` para o modo core (mode A)
e `pack_w` do kit `pecas.py` (lab 1759) para o denso. As gramáticas G1/G2/G3 e o header `#TCF.8b`/`~`
são HIPÓTESE (o #4 não foi soldado) — vivem só em `intermediates/`.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte. RT provado por gramática; a corrupção do
G3 é mostrada explicitamente (forçando core). Zero toque em `src/tcf`.
