# 2026-07-23-1533 — Decisão RLE-vs-denso é determinística e de passe único?

Micro-lab EXPERIMENTAL (viabilidade, dados pequenos). Pergunta do owner: antes de mexer em
`src/tcf`, ver se **dá pra decidir o modo (RLE / denso-base64 / misto) deterministicamente e barato**,
sem revisitar os dados já lidos — respeitando o vetor **latência** (pouca revisitação). Continua
[modo denso/marcador `0345`](../../../notas/2026-07/2026-07-23-0345-modo-denso-marcador-binarizacao.md).

## Hipótese testada

Um único passe sobre a fonte → **lista de runs** `(val,len)`. Dessa lista:
1. o **tamanho** de cada modo é calculado por FÓRMULA (denso = `b64_len(n)`, puro f(n); rle/misto =
   soma sobre runs) — sem materializar os candidatos;
2. os 3 modos são **materializados a partir da lista de runs**, não da fonte.
Se o tamanho previsto == real e a fonte é lida 1×, a decisão `min()` cabe logo após o scan de runs,
sem loop novo sobre stream já lido.

## Evidência (ver `result.md`, 6/6 ✅)

| gate | resultado |
|---|---|
| preditor EXATO (fórmula == real, 3 modos) | ✅ todos |
| vencedor previsto == medido | ✅ todos |
| passe único (`reads/n == 1.0`, zero revisitação) | ✅ todos |
| RT (decode == orig == JSON) | ✅ todos |
| **vencedor VARIA por regime** | denso (`const-sm`,`alt-big`,`noisy`) · rle (`const-big`,`few-big`) · misto (`prefix-mix`) |

O `prefix-mix` (run longo + ruído) confirma o **misto** ganhando de verdade (23 vs denso 44 vs rle 125).

## Achado colateral (latência)

O scan de runs **ingênuo** (lookahead relido como início do próximo run) DOBRA a leitura nas
fronteiras (`alt` → `reads/n=2.0`). O passe único de verdade guarda o valor já lido. Registrado no
código — é o tipo de detalhe que decide se "1 passe" é real ou só aparente.

## Onde mexer (indicação, ainda SEM tocar core)

A decisão encaixa como um passo O(nº de runs) **logo após o scan de runs** que o pipeline já faz pro
RLE — 3 fórmulas, não um loop novo. Mantém FLOOR/min() nunca-pior, mas sem materializar os perdedores.
Troca de vetor explícita: **mais compressão** (misto) → cede latência (segmentação greedy); **menos
latência** → decide por fórmula e emite 1 modo.

## Como rodar

```
python run.py     # 6 casos · esperado 0 falhas (preditor-exato + passe-único + RT + venc-match)
```

## Layout

`inputs/<caso>.json` · `outputs/<caso>.{denso,rle,misto}.tcfp` (wire de cada modo) · `result.md`.
Protótipos lab-local — NÃO tocam `src/tcf`.
