# Resultado — spec_bin Formato A vs B + reuso do HCC [probatório]

Números: `artifacts/` (`python run.py`). Nota do owner: onde os literais moram + reuso do HCC.

## 1. O HCC já dá os índices naturais (`01-hcc-native-refs.txt`)

`encode(['male']*3+['female']*2+['male']*2+['female']*3)`:
```
*3|male   → 3× male    (literal, = ^1 = bit 0)
*2|fe1    → 2× female  (fe1 = fe+afixo p/ male, = ^2 = bit 1)
*2|^1     → 2× ref ^1  (male)
*3|^2     → 3× ref ^2  (female)
```
**Os "nós já têm nomes e índices naturais" (owner)**: male=^1=bit0, female=^2=bit1, e a corrente `*N|^k`
**é** o bit-stream em forma RLE. Pra dado **ordenado, o HCC-nativo já resolve** (textual, explicável).

## 2. Formato A vs B — mesmos bytes, layout diferente (`02-formato-A-B.txt`)

Caso `grupos` (bits `0001100111` → packed hex `19c0`), corpo A=B=12B, ambos RT-OK:

```
Formato B                    Formato A
#TCF.8 sexo:spec_bin:B       #TCF.8 sexo:spec_bin:A
male                         male
female                       @byte:19          ← 1º byte empacotado
@bytes:19c0                  female            ← 2º declarado AQUI (mesmo p/ 2º tardio)
                             @bytes:c0
```

- **B** (2 literais no topo, ordem predeterminada 0/1): precisa dos 2 valores **antes** de empacotar
  (2 passadas / buffer). Simples.
- **A** (literal na 1ª ocorrência; 2º declarado no 1º byte-escape **mesmo sem ter ocorrido**): **streaming
  single-pass**, e casa com o layout **nativo do HCC** (literal na 1ª ocorrência + refs). **Owner prefere A**:
  reusa o que o HCC já produz — "associar depois no HCC (ou após) pra virar bytes".
- Caso "2º tarde" (`4m,1f`): em A o byte-escape declara `female` junto do 1º byte; em B já está no topo. RT-OK.

## 3. Decisão — spec_bin é camada PÓS-HCC, não substituto (`03`)

- **ordenado/agrupado** → deixa o **HCC-nativo** (RLE de `^refs`, textual, **mantém a quebra**/grupos).
- **espalhado** (muitos runs curtos) → **pack A** das refs em bytes (**V2-L**, binário; 16× em adult.sex, medido
  no [motor](../2026-07-06-2354-spec-bin-motor/result.md)). O header textual `sexo:spec_bin` roteia/inspeciona.
- **Formato A é o natural** porque reusa literais+refs que o HCC já pôs; só empacota os bits — pós-HCC ou
  dentro dele. Liga com o vetor **streaming** (T-FLOW S1: single-pass).

## Síntese

O bit-stream do enum **já existe** dentro do HCC (refs `^k`). O `spec_bin` não reinventa: **ordenado usa a
RLE nativa** (textual); **espalhado empacota as refs** (V2-L). **Formato A** (literal-1ª-ocorrência + 2º no
1º byte-escape) é o layout que **reusa o HCC e faz streaming** — a escolha do owner.

## Limites

- O pack aqui deriva os bits do valor (nível-valor); parsear o stream `*N|^k` real do HCC é o próximo passo.
- A/B em amostras pequenas; enum-k>2 e o pack materializado (V2-L binário) pendentes.
