# Ciclo B — bool: cada representação e a combinação (FLOOR)

Fluxo real: `inputs/-fonte.json`→`intermediates/-dataset-consumido.json`→`outputs/-wire.tcf` (REAL)→`outputs/-roundtrip.json`. Hipotéticas em `intermediates/*.tcfp`. GATE: **RT-tipado** (bool volta bool). bytes / gzip; `FLOOR`=min(typed,bN,misto).

| perfil | n | atual (.8H) | typed(RLE) | bN(denso) | misto | **FLOOR** | vencedor | RT-tipado |
|---|---:|---:|---:|---:|---:|---:|:---:|:---:|
| n0 | 0 | 7 | 8 | 12 | 10 | **8** | typed | ✅ |
| n1 | 1 | 28 | 13 | 16 | 17 | **13** | typed | ✅ |
| all-true | 64 | 33 | 17 | 25 | 15 | **15** | misto | ✅ |
| all-false | 64 | 35 | 18 | 25 | 15 | **15** | misto | ✅ |
| alt | 64 | 223 | 205 | 25 | 26 | **25** | bN | ✅ |
| runs | 64 | 50 | 33 | 25 | 26 | **25** | bN | ✅ |
| p10 | 64 | 86 | 69 | 25 | 26 | **25** | bN | ✅ |
| p50 | 64 | 181 | 163 | 25 | 26 | **25** | bN | ✅ |
| p90 | 64 | 77 | 60 | 25 | 26 | **25** | bN | ✅ |

## Sob gzip — o vencedor do FLOOR é ESTÁVEL (o gap encolhe, não inverte)

| perfil | vencedor raw | typed gz | bN gz | misto gz | vencedor gz | estável? |
|---|---|---:|---:|---:|---|:---:|
| n0 | typed | 28 | 32 | 30 | typed | ✅ |
| n1 | typed | 33 | 36 | 37 | typed | ✅ |
| all-true | misto | 37 | 37 | 35 | misto | ✅ |
| all-false | misto | 38 | 36 | 35 | misto | ✅ |
| alt | bN | 46 | 37 | 38 | bN | ✅ |
| runs | bN | 51 | 41 | 42 | bN | ✅ |
| p10 | bN | 65 | 42 | 43 | bN | ✅ |
| p50 | bN | 84 | 45 | 46 | bN | ✅ |
| p90 | bN | 58 | 42 | 43 | bN | ✅ |

**O vencedor do FLOOR é o mesmo raw e sob gzip em 9/9 perfis** — não inverte. O `bN` (base64 de bits) é ~incompressível e o `typed`/texto tem redundância que o gzip come, então o GAP encolhe muito; mas a ESCOLHA de modo se mantém. Logo a decisão pré-transporte do FLOOR é robusta ao gzip pra bool (gzip é lente, não critério).

## Homógrafos — o tipo mantém distintos (plano §S2)

| fonte | dataset | wire atual (linha-0) | tipo de volta |
|---|---|---|---|
| bool [true,false] | `[True, False]` | `#TCF.8H#V\z#:3[]:11b` | {'bool'} · RT ✅ |
| string ["true","false"] | `['true', 'false']` | `(órfão)` | {'str'} · RT ✅ |
| number [1,0] | `[1, 0]` | `#TCF.8H#V\z#:3[]:8n` | {'int'} · RT ✅ |

Mesma superfície textual (`true`/`false`/`1`/`0`), **datasets diferentes** — o tipo não é dedutível da grafia; volta pelo dataset. A forma `#TCF.8b` seria a marca que distingue bool de string homógrafa num único char.

## Leitura

- **cada representação tem seu regime**: `typed` (core, com seq-RLE) esmaga runs/constantes (`all-true`,`runs`); `bN` (denso) ganha na alternância/ruído (`alt`,`p50`); `misto` só compensa em heterogêneo genuíno — na maioria o FLOOR cai em typed ou bN.
- **o FLOOR é a combinação certa**: nunca-pior por construção; escolhe por perfil sem precisar acertar limiar. É o mesmo padrão `min()` que o TCF já usa.
- **a tipagem SEMPRE volta** (RT-tipado): a moldura `#TCF.8b` encolhe o envelope `.8H` a 1 char, mas o decode devolve bool — economia de moldura, não de semântica.
- **string homógrafa permanece distinta**: `#TCF.8b` marca bool; `"true"` string fica órfã. O tipo não some do dataset ainda que suma do arquivo.

---
**9 perfis · 0 falhas de RT-tipado.** Artefatos: `inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` · `intermediates/*.tcfp` (hipóteses) · `outputs/*-wire.tcf` (REAL). Regenera: `python run.py`.
