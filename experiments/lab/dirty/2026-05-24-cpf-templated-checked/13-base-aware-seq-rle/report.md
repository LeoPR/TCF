# Sub-exp 13 — Base-aware seq-RLE (report)

**Data**: 2026-05-24
**Status**: completed — hipotese parcialmente confirmada, mas NAO compete com pre-tx padded
**Filosofia aplicada**: separacao de responsabilidades (zero `if base ==`)

## Arquitetura implementada

3 modulos com responsabilidades separadas:

- [`base_alphabet.py`](base_alphabet.py): `BaseAlphabet` @dataclass(frozen=True) — descritor puro
  (name, chars, base). Instancias: `DECIMAL`, `HEX_LOWER`, `HEX_UPPER`.
- [`seq_rle_engine.py`](seq_rle_engine.py): `SeqRLEEngine(alphabet)` — engine generica
  parametrizada. `MultiBaseSeqRLE(alphabets)` — detector multi-base.
- [`run.py`](run.py): `HCCBaseAwareSeqRLE(M8AVirtualRefsSyntax)` — subclass
  substituindo HCCSeqRLE com MultiBaseSeqRLE.

Zero `if base == 'decimal'` no codigo. Polimorfismo via alphabet param.

## Resultados

### Test 1 — REGRESSAO (decimal only == M10 canonical)

| Dataset | M10 | BaseAware[DECIMAL] | Match |
|---|---:|---:|:---:|
| D-CPF-uniform | 18936 | 18936 | byte-identical ✓ |
| D-CPF-clustered | 18042 | 18042 | byte-identical ✓ |
| D-CPF-mixed | 16304 | 16304 | byte-identical ✓ |
| D-IP-uniform | 18159 | 18159 | byte-identical ✓ |
| D-IP-subnet | 15747 | 15747 | byte-identical ✓ |

**PASS** — arquitetura strategy pattern preserva comportamento M10.

### Test 2 — Hipotese principal (HEX IPs)

| Dataset | hex_raw | M10 only | +DECIMAL+HEX | Delta | RT |
|---|---:|---:|---:|---:|:---:|
| D-IP-uniform | 9000 | 11253 | 11253 | +0 | OK |
| **D-IP-subnet** | 9000 | 10671 | **10577** | **-94 (-0.88%)** | OK |
| D-IP-mixed | 12424 | 15186 | 15191 | +5 | OK |
| D-IP-corrupt | 9238 | 11585 | 11590 | +5 | OK |
| edge-single | 9 | 12 | 12 | +0 | OK |
| edge-allsame | 9000 | 18 | 18 | +0 | OK |
| extra-large10k | 90000 | 112616 | 112747 | **+131** | OK |

### Test 3 — CROSS-TEST (decimal nao pode regredir)

| Dataset | M10 only | +HEX | Delta | Verdict |
|---|---:|---:|---:|:---:|
| D-CPF-uniform | 18936 | 18936 | +0 | OK |
| D-CPF-clustered | 18042 | 18042 | +0 | OK |
| D-CPF-corrupt | 18959 | 18959 | +0 | OK |
| D-IP-uniform | 18159 | 18159 | +0 | OK |
| D-IP-extra-large10k | 175734 | 175734 | +0 | OK |

**Zero regressao em datasets decimal.**

## Analise critica (como owner pediu)

### Hipotese **parcialmente confirmada**

Base-aware seq-RLE FUNCIONA — capta hex incremental, RT 100%. Mas ganho
modesto (-94B em subnet, -0.88%) e marginal regressao em mixed/corrupt
(+5B cada) e large10k (+131B, +0.12%).

### Por que NAO compete com C decimal padded?

- **C decimal subnet**: 229B (1.71%) — ganho dramatico de 60x
- **D hex + base-aware subnet**: 10577B (~79%) — ganho marginal

A diferenca: **C transforma input pra forma visivel-uniforme via
padding** (`192168001008`). Toda a chain (column_features.is_numeric,
detect_cadence regra 2, processar_with_hint shape-preserve, HCC
seq-RLE digit) ATIVA pra esse formato.

**D hex + base-aware** so' melhora a ultima etapa (seq-RLE). As
camadas anteriores ainda tratam hex como "string com letras"
(is_numeric=False, cadence detect falha, sem shape-preserve hint).

### Lesson META (importante)

Generalizar base-aware no HCC seq-RLE **isolado** nao basta. Pra
hex IPs ganhar como C decimal, precisaria estender:

1. `ColumnFeatures.is_numeric` (aceitar hex)
2. `detect_cadence` regra 2 (hex high-card numeric)
3. `processar_with_hint` (shape-preserve em hex)
4. `HCC seq-RLE` (este sub-exp ja' resolveu)

Chain de 4 camadas. Custo alto, ganho incerto.

### Contra-argumento da literatura

PFOR-DELTA / VByte / Gorilla operam em **integers nativos**
(ja' parsed). TCF tenta hibrido (texto + delta), incluindo o
problema de detectar QUAIS partes da string sao "integers".

Em literatura, **a detecao de "isto eh um integer em base X"**
acontece SEMPRE NO INPUT (parser), nao em camadas downstream do
compressor. Nosso sub-exp confirma: tentar adivinhar base em layer
de compressao downstream eh sub-otimo vs declarar/padronizar no
parser.

Ou seja: **pre-tx que transforma input para forma uniforme** (variante C)
eh mais poderoso que **layer aware-of-original-base** (este sub-exp).

### Verdict

- Hipotese **parcialmente refutada** pra valer ROI vs welding
- Arquitetura strategy pattern **validada** (regression PASS, zero
  regressao em decimal)
- Insight pra owner: **caminho mais barato eh pre-tx visivel-uniforme**
  (padding), nao generalizar HCC seq-RLE

## Recomendacao

NAO weld base-aware seq-RLE em src/tcf. Ganho marginal (-94B em 1
dataset; +5-131B regressao marginal em outros) nao justifica:
- Mudanca de marker format (`@h` annotation)
- Quebra backward compat M10
- Codigo adicional em canonical (anti "viavel agora > otimo eventual")

**Manter sub-exp 13 como prova de conceito**. Owner pode revisitar
se aparecer use case real onde:
1. Input nao pode ser pre-processed (e.g., format mandatory)
2. Hex/base32/base64 dominam dataset
3. Ganho cumulativo justifica complexidade

## Conexao com sub-exp 11 (detector multi-segmento)

Owner mencionou interesse em **detector cadence multi-segmento**
(cross-subnet). Esta direcao tambem **modular** mas opera em camada
DIFERENTE (detect_cadence pre-pass, nao seq-RLE post-process).

Sub-exp 13 ensina: mudanca isolada em uma camada raramente dramatica.
**Detector multi-segmento provavelmente tem mesma limitacao** — ganho
marginal se camadas adjacentes nao adaptarem.

Conservacao da hipotese owner (pre-tx > generalizacao downstream)
sugere foco em **schema_builder Fase 3** (detect natures no INPUT)
sobre layer-level changes no compressor.

## Outputs visiveis (auditoria)

- `out_tcf/D-IP-subnet-hex-baseaware.tcf` (10577B)
- `out_tcf/D-IP-subnet-hex-M10.tcf` (10671B)
- `out_tcf/D-IP-subnet-hex-*-seq_runs.json` (runs detectados por engine)
- `manifest.json` (regression + hypothesis + cross-test)
