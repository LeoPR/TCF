# T-DENSO-B2 — denso ternário `#TCF.8b2<n>`, o ganho medido (2026-07-31-2350)

O denso **b1** (bool puro SEM null) está soldado com domínio implícito — 47 B para n=200. O ternário (bool COM null) cai no core — 546 B. O lab vizinho `2026-07-28-0829` levou o ternário a 94 B com o bN tipado de domínio **declarado** (`#TCF.8bB2c8`). Este lab mede a pergunta que ficou: se o domínio é conhecido a priori (`null`/`false`/`true` são tipos puros do JSON), **declarar o domínio é redundante** — dá pra congelar `0=null, 1=false, 2=true` e ir a **2 bits/símbolo** na mesma grafia posicional do b1.

```
#TCF.8 b 2 c8
       │ │ └── n em hex (200)
       │ └──── modo = 2 bits/símbolo, ÍNDICE 7  <- o slot JA' existe
       └──────── tag de tipo, índice 6
```

Símbolo **3 = reservado** — fail-loud no decode (seção D). O mecanismo é o MESMO `pack_w`/`unpack_w` soldado do b1 (`src/tcf/bitpack.py`), só com `w=2`.

## A — o ganho, por coluna (n=200)

| coluna | n | tag | hoje | bN tipado | b2 | Δ hoje→bN / →b2 | RT b2 |
|---|---:|:-:|---:|---:|---:|---|:-:|
| `bool-null` | 200 | `b` | 546 | 94 | 79 | -452 / **-467** | OK |
| `bool-null-esparso` | 200 | `b` | 601 | 94 | 79 | -507 / **-522** | OK |
| `bool-puro` | 200 | `b` | 47 | 58 | — | +11 | — |
| `bool-constante` | 200 | `b` | 18 | — | — | — | — |

O `bool-puro` e o `bool-constante` têm `b2 = —` **de propósito**: sem null, o protótipo RECUSA — o denso b1 soldado é estritamente menor (2 bits vs 1 bit por símbolo). O b2 só compete onde o b1 não alcança: **bool com null**.

## B — onde o b2 PERDE ou não se aplica

Varredura de `n`, densidade de null ~1/3 (ternário completo). Sem estes, a tabela A não significa nada.

| coluna | n | tag | hoje | bN tipado | b2 | Δ hoje→bN / →b2 | RT b2 |
|---|---:|:-:|---:|---:|---:|---|:-:|
| `bool-varre-n0003` | 3 | `b` | 21 | 28 | 14 | +7 / **-7** | OK |
| `bool-varre-n0010` | 10 | `b` | 39 | 30 | 14 | -9 / **-25** | OK |
| `bool-varre-n0050` | 50 | `b` | 146 | 45 | 31 | -101 / **-115** | OK |
| `bool-varre-n0200` | 200 | `b` | 546 | 94 | 79 | -452 / **-467** | OK |
| `bool-varre-n1000` | 1000 | `b` | 2679 | 362 | 348 | -2317 / **-2331** | OK |

**O b2 vence em TODO o intervalo medido, inclusive n=3** (14 B vs 21 do core) — diferente do bN tipado, que perde em n pequeno porque o domínio declarado viaja (28 B em n=3). O domínio implícito zera esse custo fixo: header de ~11 B + `ceil(2n/8)` bytes de payload. Onde o b2 NÃO se aplica: bool puro sem null (recusa — o b1 de 1 bit domina) e `k≤1` sem null (recusa — o RLE do core é ótimo). O b2 é **mais um candidato do `min()`**, não substituto de nada.

## C — colunas REAIS

Conversão idêntica à do lab vizinho (`datasets/samples/adult-census/adult-sample.csv`), com nulls injetados **deterministicamente a cada 7º elemento** para formar o ternário real-ish. Escolha DO LAB, não do dado — declarado em `datasets-provenance.md`.

| coluna | n | tag | hoje | bN tipado | b2 | Δ hoje→bN / →b2 | RT b2 |
|---|---:|:-:|---:|---:|---:|---|:-:|
| `real-adult-sex-bool-ternario` | 100 | `b` | 250 | 61 | 47 | -189 / **-203** | OK |
| `real-adult-class-bool-ternario` | 100 | `b` | 232 | 61 | 47 | -171 / **-185** | OK |

## D — fail-loud

Evidência em `outputs/fail-loud.txt` e assert no `run.py` (sai 1 se qualquer caso decodificar calado):

```
# fail-loud — denso b2 (gerado por run.py)

[OK] símbolo 3 no payload (RESERVADO)
     ValueError: simbolo 3 no denso b2: RESERVADO, wire invalido
[OK] payload truncado (1 byte a menos)
     ValueError: payload denso b2 de tamanho errado: 48 bytes, esperado 50
[OK] b64 não-canônico (`!` no payload)
     ValueError: Only base64 data is allowed
```

## Round-trip e resumo

`RT` compara **valor, tipo e comprimento**. Roundtrip é ARQUIVO: `outputs/<nome>-dataset.roundtrip.json` byte-idêntico a `intermediates/<nome>-dataset-consumido.json` (assert no `run.py`).

- estimativa prévia para n=200: header `#TCF.8b2c8\n` (11 B) + b64 de 50 B (68 chars) ≈ **79 B**. Medido: **79 B** (core 546 B, bN tipado 94 B).
- fail-loud: **3/3** casos rejeitados com `ValueError`.
- RT estrito: **100%**.

## Limites

- **Nada soldado**; `src/tcf` intocado. Os `-b2.tcf` são proposta — o `decode` público ainda não conhece o modo `2`.
- Domínio congelado `0=null, 1=false, 2=true` — se um dia o b1 mudar a ordem, o b2 tem de seguir (os dois compartilham o conceito de domínio implícito).
- gzip e CPU não medidos.
- Colunas reais: nulls injetados pelo lab (a cada 7º elemento), não do dado.

