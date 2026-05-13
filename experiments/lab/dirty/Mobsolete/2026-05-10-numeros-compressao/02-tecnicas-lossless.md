# Catálogo — técnicas lossless de compressão numérica

Inventário do que existe na literatura e na prática. Marcado:
- ✓ compatível com TCF texto
- △ adapta para texto com adaptação
- ✗ binário-only (precisaria dialeto TCF-binary)

---

## Categoria 1 — Codificação de comprimento variável

### VarInt / LEB128 (Little Endian Base 128) ✗

Inteiros codificados em 1-10 bytes, mais bits para valores maiores.
Cada byte usa 7 bits para dados + 1 bit "continua".

- Padrão em Protocol Buffers, MessagePack, etc.
- **Binário-only.** TCF texto não usa.
- Reservado para "TCF-binary" hipotético.

### ZigZag encoding (companion ao VarInt) ✗

Mapeia inteiros com sinal para não-negativos, otimizando VarInt.
- 0 → 0, -1 → 1, 1 → 2, -2 → 3, 2 → 4, ...
- Idem: binário-only.

---

## Categoria 2 — Frame-of-Reference (FOR)

### FOR clássico △

Em um bloco de N valores:
1. Calcula min e max do bloco
2. Armazena `min` (referência) + `(v - min)` para cada valor
3. Cada `v - min` cabe em ⌈log₂(max - min + 1)⌉ bits

Compatível com TCF se "bits" virar "chars" — ainda economiza.

Exemplo: tensão IoT [108, 109, 110, 111, 112]
- min = 108
- offsets = [0, 1, 2, 3, 4]
- TCF text: `108 +0 +1 +2 +3 +4` (mistura de absoluto + delta de baseline)

→ É **delta com baseline fixo**, não acumulativo. Útil para oscilações.

### Patched FOR (PFOR) △

FOR + lista separada de outliers.
- Bloco usa bits suficientes para 95% dos valores
- 5% extremos vão num "patches" anexado
- Recupera ganho mesmo com outliers raros

Adaptável para TCF: "valor outlier ⟶ posição + valor original" como
linha extra. Mas custa pareamento posicional. Mesa de implementação
detalha.

---

## Categoria 3 — Delta encoding

### Delta acumulativo ✓

Já em mesa anterior (datas). Generaliza:
- Sequência: v₀, v₁, v₂, ...
- Codificada: v₀, Δ₁, Δ₂, Δ₃ onde Δᵢ = vᵢ - vᵢ₋₁

Para TCF, sintaxe `+N` ou `-N`. Pré-transformação na flag δ.

### Delta de baseline (não acumulativo) △

Sequência: v₀, v₁, v₂, ...
Codificada: B (baseline), (v₀-B), (v₁-B), (v₂-B), ...

Para oscilações em torno de média conhecida (tensão 110V).

Sintaxe TCF possível:
```
# ext: tensao=delta-baseline:110
tensao:
+0.2     ← v = 110 + 0.2 = 110.2
-0.3     ← v = 109.7
+0.5
```

OU baseline implícito do 1º valor (como o δ atual mas sem acumular):
```
tensao:
110.2    ← baseline = 110.2 (1º absoluto)
+1.0     ← v = 110.2 + 1.0 = 111.2? OU baseline + 1.0 = 111.2?
```

Ambíguo. Precisaria flag para distinguir acumulativo vs baseline.

→ **Pergunta aberta**: a flag δ atual é acumulativa por convenção. Adicionar
sub-modo `δ-baseline` ou ficar separado?

### Delta-of-delta (Δ²) △

Para sequências com aceleração constante (raras em dados de aplicação,
comuns em séries temporais físicas):

v: 0, 1, 3, 6, 10, 15
Δ: 1, 2, 3, 4, 5
Δ²: 1, 1, 1, 1

Δ² captura padrão linear-acelerado. Compõe com RLE.

→ Útil para **timestamps acelerantes** ou **sequências polinomiais**.
Provavelmente raro em dados de TCF típico. Reservado.

---

## Categoria 4 — Bit-packing direto ✗

Para inteiros num range conhecido [0, N], usar ⌈log₂(N+1)⌉ bits.
Exemplo: bounded counter [0, 12] → 4 bits/valor.

**Binário-only.** Em TCF texto, equivale a representação compacta do
índice (cobertto por flag A — ticket S-representacao-de-indice).

---

## Categoria 5 — Específicas para float

### Gorilla XOR-delta (Facebook TSDB) ✗

Para floats de telemetria:
- Calcula XOR entre valor atual e anterior
- Codifica leading zeros, trailing zeros, número de bits significativos
- Comprime muito quando valores são similares

Binário. Para texto, abandona. Reservado para dialeto binário futuro.

### FPC (Fast Predictive Compression) ✗

Predição (FCM ou DFCM) + XOR + Huffman. Binário.

### ZFP △ (lossless mode)

Block-based, transformada de bit-plane. Em modo lossless, ainda
binário. Em modo lossy (próxima seção), pode adaptar para text.

---

## Categoria 6 — Algébrica / regressional

### Regressão linear + resíduos △

Sequência: v_i ≈ a*i + b. Encoder armazena (a, b) e os resíduos
v_i - (a*i + b).

Funciona quando há tendência linear forte. Os resíduos são pequenos e
podem ter dist concentrada (compressível).

Sintaxe TCF possível:
```
# ext: medida=linear:a=0.5,b=100
medida:
+0.1     ← residuo (valor real = 100 + 0.5*0 + 0.1 = 100.1)
-0.2
+0.05
```

→ Pesquisa: detectar quando regressão vale a pena. Custo do (a, b) +
resíduos vs delta puro?

### Polinomial / Spline △

Para curvas mais complexas. Storage de coeficientes + resíduos.
Para TCF, geralmente over-engineered. Reservado para datasets
científicos.

### Fourier / Wavelet ✗

Para séries cíclicas, base ortogonal compacta. Binário típico.
Reservado.

---

## Categoria 7 — Predictive coding

### Predictor + residual △

Prediz próximo valor de um modelo (média móvel, AR, Markov):
- Pred(v_i) = f(v_{i-1}, v_{i-2}, ...)
- Armazena v_i - Pred(v_i)

Funciona para séries autocorrelacionadas. Resíduos pequenos.

Para TCF: requer modelo declarado em header. Decoder roda mesmo modelo.
Complexidade alta para o ganho variável.

→ **Tendência**: deixar para casos especializados (telemetria), não no
core do TCF.

---

## Categoria 8 — Combinações

### Delta + dict ✓

Já fazemos. δ + RLE/dict é a regra unificada para dates.

### FOR + dict △

Após FOR, os offsets podem ter padrão repetitivo. Dict captura.

### Delta + bit-packing dos resíduos △

Resíduos pequenos → bit-pack. Para texto, equivale a usar índices
curtos. Cobertto por A.

---

## Compatibilidade com TCF v0.5

Resumindo o que vai para o catálogo TCF:

| Técnica | Status TCF | Flag/extensão |
|---|---|---|
| Delta acumulativo | ✓ tem (δ) | já existe |
| Delta de baseline | △ proposta | sub-modo de δ ou nova flag |
| Delta-of-delta | △ proposta | sub-modo de δ |
| FOR clássico (em texto) | △ proposta | possível flag F |
| PFOR (com outliers) | △ complexo | reservado |
| Regressão linear + resíduos | △ proposta | flag R-lin (reservada) |
| Bit-packing | ✗ | "TCF-binary" futuro |
| Gorilla XOR | ✗ | "TCF-binary" futuro |
| FPC, ZFP, etc | ✗ | "TCF-binary" futuro |

→ Próximas mesas (priorizadas em `04`):
1. Delta de baseline para oscilações (B do `01`)
2. FOR adaptado em texto (B, D)
3. Regressão linear (F com tendência) — talvez

---

## Lacunas teóricas a investigar

1. **Compor δ-acumulativo com δ-baseline**: combinação faz sentido?
2. **Dict de resíduos**: depois de regressão ou FOR, os resíduos podem
   ter padrão. Dict no resíduo?
3. **Bit-vs-char**: sempre que técnica binária ganha, vale dialeto
   binário do TCF?
4. **Detecção automática**: encoder com 1-passada decide entre delta,
   baseline, regressão? Ou precisa header?

→ `04-perguntas-e-roadmap.md` lista essas perguntas formalmente.
