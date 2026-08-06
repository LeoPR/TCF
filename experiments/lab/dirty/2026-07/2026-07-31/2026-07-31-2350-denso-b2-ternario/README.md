# 2026-07-31-2350 — T-DENSO-B2: denso ternário `#TCF.8b2<n>`, o ganho medido

O denso **b1** (bool puro SEM null, domínio implícito `false=0, true=1`) está soldado —
47 B para n=200. O ternário (bool COM null) cai no core — 546 B. O lab vizinho
[`2026-07-28-0829-bn-tipado-ganho-medido`](../../2026-07-28/2026-07-28-0829-bn-tipado-ganho-medido/)
levou o ternário a 94 B com o bN tipado de domínio **declarado**. Este lab mede a pergunta
que ficou: `null`/`false`/`true` são tipos puros do JSON — **declarar o domínio é
redundante**. Congelando `0=null, 1=false, 2=true` (símbolo 3 reservado, fail-loud), dá
pra ir a **2 bits/símbolo** na mesma grafia posicional do b1.

## O ganho (n=200, ternário completo ~1/3 de null)

| coluna | core hoje | bN tipado (domínio declarado) | **b2 (domínio implícito)** | Δ |
|---|---:|---:|---:|---:|
| `bool-null` | 546 | 94 | **79** | −467 |
| `bool-null-esparso` | 601 | 94 | **79** | −522 |
| `real-adult-sex-bool-ternario` (n=100) | 250 | 61 | **47** | −203 |
| `real-adult-class-bool-ternario` (n=100) | 232 | 61 | **47** | −185 |

A estimativa prévia (header 11 B + b64 de 50 B ≈ **79 B**) bateu **exatamente** — 79 B
medidos. O b2 economiza os 15 B do domínio declarado do bN tipado.

## Onde perde ou não se aplica

- **Vence em todo o intervalo medido, inclusive n=3** (14 B vs 21 do core) — o bN tipado
  perdia em n pequeno porque o domínio declarado viaja (28 B em n=3); o domínio implícito
  zera esse custo fixo.
- **Bool puro sem null: o b2 RECUSA** — o denso b1 de 1 bit/símbolo é estritamente menor
  (47 B vs o que seriam ~90 B a 2 bits). Não compete lá.
- **`k≤1` sem null: recusa** — o RLE do core é ótimo (18 B).
- É **mais um candidato do `min()`**, não substituto de nada.

## Varredura de n (densidade de null ~1/3)

| n | 3 | 10 | 50 | 200 | 1000 |
|---|---:|---:|---:|---:|---:|
| core | 21 | 39 | 146 | 546 | 2679 |
| bN tipado | 28 | 30 | 45 | 94 | 362 |
| **b2** | **14** | **14** | **31** | **79** | **348** |

## Fail-loud (3/3, evidência em `outputs/fail-loud.txt`)

- símbolo **3** no payload → `ValueError` (reservado)
- payload truncado (1 byte a menos) → `ValueError` (tamanho exato `ceil(2n/8)`)
- b64 não-canônico (`!` no payload) → `ValueError` (`validate=True`)

## Validação

RT estrito **100%** (valor, tipo e comprimento). Roundtrip é ARQUIVO:
`outputs/<nome>-dataset.roundtrip.json` byte-idêntico a
`intermediates/<nome>-dataset-consumido.json` (assert no `run.py`). O protótipo
(`denso_b2.py`) usa o MESMO `pack_w`/`unpack_w` soldado do b1 (`src/tcf/bitpack.py`) —
só com `w=2`. **`src/tcf` intocado.**

## Limites

- Nada soldado; os `-b2.tcf` são proposta — o `decode` público ainda não conhece o modo `2`.
- gzip e CPU não medidos.
- Colunas reais: nulls injetados pelo lab (a cada 7º elemento), não do dado.

## Rodar

```
python run.py
```

Sai `0` só se o RT estrito passar em todas as colunas e os 3 casos fail-loud rejeitarem.
