# 2026-07-25-1746 — Tag `n` weldada: rota tipada GENERALIZADA

Reexecuta a matriz do lab [`1729`](../2026-07-25-1729-lacunas-tipos-bool-null/) contra o
`src/tcf` já com a mudança, para medir o que ela trocou. 27 casos, evidência em arquivo.

## O que mudou no código

Antes havia **um ramo para bool**. Agora há **uma função de detecção de tipo**
(`_tipo_single_col`), e cada tipo novo é uma linha nela em vez de um bloco novo no `encode`:

```python
if all(type(x) is bool for x in vals):            return "b", ...
if all(type(x) is int or type(x) is float ...):   return "n", str
```

Três consequências, todas medidas:

1. **`int`/`float` ganharam a tag `n`** — saíram do `.8H`.
2. **null convive com qualquer tag** — não define tipo, mora no slot 0. Isso fechou
   `bool+null` e `int+null` de graça, pela mesma generalização.
3. **`#TCF.8s` passou a decodar** (mas o encoder não emite): string segue implícita por
   exclusão, e agora a forma explícita é aceita — fecha a coerência do modelo
   explícito/implícito, que era a única exceção.

O modo denso segue bool-only e sem null, **por construção**: 1 bit são 2 estados, e o trio
`{null, false, true}` não cabe. Com null a coluna usa o core.

## Antes vs depois

| id | antes `.8H` | depois | Δ | vs JSON antes | vs JSON depois |
|---|---:|---:|---:|---:|---:|
| `A7-int` | 31 | 16 | **−48%** | +343% | +129% |
| `A8-float` | 36 | 20 | **−44%** | +300% | +122% |
| `C6-int-null` | 42 | 16 | **−62%** | +320% | +60% |
| `C8-float-null` | 48 | 22 | **−54%** | +243% | +57% |
| `C1-bool-null-2` | 36 | 15 | **−58%** | +227% | +36% |
| `C2-bool-null-3` | 46 | 21 | **−54%** | +171% | +24% |
| `C3-bool-null-16` | 105 | 57 | **−46%** | +24% | **−33%** |
| `C4-bool-null-100` | 486 | 288 | **−41%** | −8% | **−45%** |
| `C7-int-100` | 45 | 27 | **−40%** | −85% | **−91%** |
| `C10-int-grande` | 53 | 37 | **−30%** | +18% | **−18%** |

**RT 27/27.** Gates byte-canônicos intactos (D1-D9 1586, D17a 300, real-world 89637) — nenhuma
coluna de string mudou de byte.

## O que ainda fica maior que o JSON

13 de 27 casos, e agora **12 deles são de payload minúsculo**: os 7 B de cabeçalho contra um
JSON de 2–17 B. Consequência declarada do ADR-0034, não lacuna.

**Sobrou uma única lacuna de rota**: `multi-col + null` (+47%), que continua no `.8H` — a
generalização foi só do single-col.

## Por que o wire não chega no ideal (`#TCF.8n` + `*3+1`)

No corpo, **dígito nu é referência de fragmento**, então o literal `1` precisa do escape. O
custo real é pequeno — **1–2 B no total**, não 1 B por elemento, porque o seq-RLE colapsa a
sequência num template só:

```
[1,2,3]     ->  *3+1|\1      (o \ custa 1 B)
range(10)   ->  *10+1|\0     (idem)
```

Suprimir o escape exigiria uma gramática de corpo diferente sob a tag `n` — o oposto de
reusar o core intocado.

## Rodar

```
python run.py     # 27 casos; regenera evidências + result.md
```

`inputs/` · `intermediates/` · `outputs/*-wire.tcf` (REAL) + `*-equivalente.json` +
`*.roundtrip.json`.
