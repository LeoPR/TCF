# B2 prototype — resultado [probatório]

**Data**: 2026-06-27. Prototype read-only do group-dict híbrido V2 com formato `&<G>` REAL +
round-trip. Decompõe o ganho em (a) dict-vs-OBAT/HCC e (b) cross-dict sharing. `src/tcf` intocado.

## Resultado (body bytes; controle = gzip)
```
caso                              RT  grp  total   = dict   + share    gzip[tot / share]  decodes
ilustrativo de/para (N=10)        ok   1   -42.7%    +0.0%   -42.7%     -18.9% / -18.9%    2->1
SNAP ca-GrQc from~to              ok   1   -43.2%   -29.6%   -19.3%     -32.4% / -21.0%    2->1
OpenFlights source~dest (IATA)    ok   1   -38.1%   -35.1%    -4.6%     -17.4% /  -7.7%    2->1
OpenFlights source_id~dest_id     ok   1   -40.3%   -36.1%    -6.6%     -20.6% /  -7.6%    2->1
>=3 col same-domain (N=2000)      ok   1   -19.0%    +0.0%   -19.0%     -14.0% / -14.0%    3->1
BORDA uniao cruza bucket (N=8000) ok   0    +0.0%    +0.0%    +0.0%      +0.0% /  +0.0%    0->0
```

## Achados

### 1. O formato `&<G>` funciona e é lossless (o que o B1 não provou)
**RT ok em todos os casos.** O prototype construiu o wire-format corrigido (prelúdio length-prefixed
no corpo + coluna `&<G>` stream-only) e decodou de volta byte-exato. O blob é inspecionável
([artifacts/05](artifacts/05-blob-b2.tcf.txt)): meta `&0:` + prelúdio `1\n18\n<tab>` + stream base-94.
As correções A da revisão (prelúdio ≠ linha de header; modo `&<G>`) **se sustentam na prática**.

### 2. O cross-dict share valida o B1 EXATAMENTE
Isolando (b) B2 vs V1 (dict per-col): **SNAP −19.3%, OpenFlights −4.6%/−6.6%** — idênticos ao B1
(que modelava dict-vs-global). O share **escala com nº de colunas** (≥3-col: −19.0%, decodes 3→1) e
com K/N. Confirma o mecanismo com formato real + RT.

### 3. O share SOBREVIVE ao controle (≠ EI)
gzip do sharing: SNAP **−21.0%**, ≥3-col −14.0%, OpenFlights −7.6/−7.7%. Diferente do EI (que
evaporava/invertia sob compressor), o cross-dict remove **redundância genuína** (a tabela duplicada),
então o ganho persiste sob gzip. Reportado como **controle** (não gate — brotli/gzip é referência,
correção owner). Sinal saudável antes do weld.

### 4. O greedy guard funciona ao escalar (a dobradiça)
BORDA (união cruza o bucket 94, N=8000): **grp=0** — o greedy **rejeitou** o pool porque, ao escalar,
o custo de largura (∝N, w 1→2) domina o dedup (fixo). Confirma a correção B da revisão: **o termo de
custo é o guard**, não o Jaccard (Jaccard=0.895 alto, mas não poolou). Em N pequeno o mesmo grupo
poolava (dedup ainda vencia) — o guard é sensível à escala, como esperado.

### 5. ACHADO SEPARADO (maior, NÃO é B2): dict per-col sem cap >> OBAT/HCC em alta cardinalidade
A componente (a) dict-vs-OBAT/HCC é **−29.6% (SNAP), −35.1%/−36.1% (OpenFlights)** — e **sobrevive
gzip** (é a maior parte do total −38..−43%). Causa: o cap `_V2B_MAX_CARD=1024` faz colunas high-card
(nós de grafo K=5242, aeroportos K=3425) caírem em OBAT/HCC, mas elas têm **alta repetição** (N/K≈5.5)
→ um dict (2 chars/valor) vence OBAT por larga margem. **O cap deixa 30%+ na mesa** pra categórico
high-card-alta-repetição. É ortogonal ao cross-dict (vale sem compartilhar). **Distinto do B2** →
merece ticket próprio (rever o gating do V2-B por N/K, não só K). Medido em 3 same-domain reais;
precisa gate próprio (N≥5, anti-incidente) antes de qualquer weld.

## Rastreabilidade
Artefatos do caso ilustrativo em [artifacts/](artifacts/): input, decisão de particionamento, **OBAT
log + HCC trace da união** ([03](artifacts/03-obat-hcc-uniao.txt) — mostra tab(união 6)=18B = tab(uma
coluna), < soma 49B: o dedup é não-linear), blobs V0/B2 byte-a-byte, RT + decomposição.

## Veredito
**Mecanismo do B2 validado ponta-a-ponta**: formato real + RT lossless + ganho reproduzido (share =
B1) + guard funciona ao escalar + share sobrevive ao controle. Pendências pro B3 (inalteradas):
- **Gate N≥5**: SNAP + OpenFlights×2 = 3 reais same-domain; **faltam ≥2** (liga a T-DATA-1).
- **Achado (5)** é uma frente SEPARADA (cap do V2-B) — registrar ticket próprio; não bloqueia o B2.
- ≥3 col e borda cobertos; RT pinável quando for weld.

Próximo natural: os ≥2 datasets same-domain que faltam (T-DATA-1, download do owner) OU abrir o
ticket do achado (5). O weld B3 (src/tcf) segue sob aprovação.
