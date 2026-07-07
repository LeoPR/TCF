# 2026-07-07-0016 — spec_bin Formato A vs B + reuso do stream de refs do HCC

**Ticket**: [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) · nota-mãe
[tipos-como-specs](../notas/tipos-como-specs.md) · segue o
[motor spec_bin](../2026-07-06-2354-spec-bin-motor/result.md). Nota do owner (2026-07-07): onde os 2
literais moram, como o 2º (que pode aparecer tarde) vira bit, e o reuso do HCC.

## Estado

- **era**: o motor tratava domínio + bit-stream como bloco novo.
- **foi**: descoberto que o **HCC já produz literais + REFERÊNCIAS** com índices naturais; prototipados
  os 2 layouts (A/B).
- **é**: `encode(['male'×3,'female'×2,'male'×2,'female'×3])` = `*3|male\n*2|fe1\n*2|^1\n*3|^2` →
  **male=^1=bit0, female(fe1)=^2=bit1**, e `*N|^k` **é** o bit-stream em RLE. O pack (A/B) é um passo
  **pós-HCC (V2-L)** que reusa esses literais+refs. **Formato A** (literal na 1ª ocorrência; 2º declarado
  no 1º byte-escape) casa com o layout nativo do HCC e é **streaming single-pass** → preferido pelo owner.
  **Formato B** (2 literais no topo) é 2-passadas, mais simples. Ambos RT-OK, mesmos bytes.
- **será**: pack pós-HCC lendo o stream `*N|^k` de verdade; enum-k; welding V2-L.

## Achados

1. **HCC-nativo = índices naturais** (`^1`=bit0, `^2`=bit1). Pra dado **ordenado**, o HCC-nativo (RLE de refs,
   textual, mantém a quebra) **já é a resposta** — não precisa pack.
2. **A vs B mesmos bytes** (2 literais afixo + ceil(N/8)); diferem no layout: **B** precisa dos 2 valores antes
   (2 passadas); **A** declara o 2º no 1º byte-escape (mesmo sem ter ocorrido) → single-pass + reusa o HCC.
3. **spec_bin = camada pós-HCC (V2-L)**, não substituto: ordenado→HCC-RLE textual; espalhado→pack A (binário,
   16× em adult.sex, medido no motor). Header textual `sexo:spec_bin` roteia.

## Arquivos

- `formatos.py` — encode/decode A e B, serialize (layout), pack/unpack bits.
- `run.py` — HCC-nativo + A/B + decisão. `python run.py` regenera `artifacts/`.
- `artifacts/` — `00-resumo` · `01-hcc-native-refs` · `02-formato-A-B` · `03-decisao-pos-hcc`.

## Como rodar

```
python experiments/lab/dirty/2026-07-07-0016-spec-bin-formato-A-B/run.py
```

## Escopo

Dirty. NÃO toca `src/tcf`. Formato A liga com o vetor STREAMING (T-FLOW S1: single-pass).
