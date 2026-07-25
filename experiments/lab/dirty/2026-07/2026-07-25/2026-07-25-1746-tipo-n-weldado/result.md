# Tag `n` weldada — matriz de tipos remedida (2026-07-25-1746)

Estado REAL do `src/tcf` DEPOIS da generalização da rota tipada. `JSON` = equivalente compacto (`separators=(',',':')`). Cada linha tem os arquivos em `inputs/` · `intermediates/` · `outputs/`.

## A. Rota que cada tipo toma HOJE

| id | rota | TCF (B) | JSON (B) | vs JSON | RT |
|---|---|---:|---:|---:|---|
| `A1-str` | flat | 14 | 13 | **+8%** | OK |
| `A2-str-null` | flat | 13 | 14 | **-7%** | OK |
| `A3-so-null` | flat | 12 | 11 | **+9%** | OK |
| `A4-vazio` | flat | 7 | 2 | **+250%** | OK |
| `A5-bool` | tipado 'b' | 14 | 17 | **-18%** | OK |
| `A6-bool-alternado` | tipado 'b' | 23 | 353 | **-93%** | OK |
| `A7-int` | tipado 'n' | 16 | 7 | **+129%** | OK |
| `A8-float` | tipado 'n' | 20 | 9 | **+122%** | OK |
| `A9-multi-str` | .8M | 21 | 29 | **-28%** | OK |

## B. Bool — varredura de tamanho

| id | rota | TCF (B) | JSON (B) | vs JSON | RT |
|---|---|---:|---:|---:|---|
| `B1-bool-n1` | tipado 'b' | 13 | 6 | **+117%** | OK |
| `B2-bool-n2` | tipado 'b' | 14 | 12 | **+17%** | OK |
| `B3-bool-n4` | tipado 'b' | 14 | 22 | **-36%** | OK |
| `B4-bool-n8` | tipado 'b' | 14 | 45 | **-69%** | OK |
| `B5-bool-n16` | tipado 'b' | 15 | 87 | **-83%** | OK |
| `B6-bool-n64` | tipado 'b' | 23 | 353 | **-93%** | OK |
| `B7-bool-n256` | tipado 'b' | 56 | 1409 | **-96%** | OK |
| `B8-bool-n1000` | tipado 'b' | 180 | 5501 | **-97%** | OK |

O bool cruza o JSON em **~4 elementos**: abaixo disso o cabeçalho de 7 B domina; acima, o ganho vai a −97%.

## C. Null e número — o que a generalização alcançou

| id | rota | TCF (B) | JSON (B) | vs JSON | RT |
|---|---|---:|---:|---:|---|
| `C1-bool-null-2` | tipado 'b' | 15 | 11 | **+36%** | OK |
| `C2-bool-null-3` | tipado 'b' | 21 | 17 | **+24%** | OK |
| `C3-bool-null-16` | tipado 'b' | 57 | 85 | **-33%** | OK |
| `C4-bool-null-100` | tipado 'b' | 288 | 526 | **-45%** | OK |
| `C5-multi-null` | .8H | 44 | 30 | **+47%** | OK |
| `C6-int-null` | tipado 'n' | 16 | 10 | **+60%** | OK |
| `C7-int-100` | tipado 'n' | 27 | 291 | **-91%** | OK |
| `C8-float-null` | tipado 'n' | 22 | 14 | **+57%** | OK |
| `C9-int-negativos` | tipado 'n' | 17 | 10 | **+70%** | OK |
| `C10-int-grande` | tipado 'n' | 37 | 45 | **-18%** | OK |

## Antes vs depois do weld da tag `n` (2026-07-25)

`antes` = rota `.8H`, que era pra onde toda coluna tipada ia. Reconstruido forcando a entrada pro envelope hierarquico.

| id | antes `.8H` | depois | Δ | vs JSON antes | vs JSON depois |
|---|---:|---:|---:|---:|---:|
| `A1-str` | 26 | 14 | **-46%** | +100% | +8% |
| `A2-str-null` | 34 | 13 | **-62%** | +143% | -7% |
| `A3-so-null` | 28 | 12 | **-57%** | +155% | +9% |
| `A5-bool` | 38 | 14 | **-63%** | +124% | -18% |
| `A6-bool-alternado` | 223 | 23 | **-90%** | -37% | -93% |
| `A7-int` | 31 | 16 | **-48%** | +343% | +129% |
| `A8-float` | 36 | 20 | **-44%** | +300% | +122% |
| `C1-bool-null-2` | 36 | 15 | **-58%** | +227% | +36% |
| `C2-bool-null-3` | 46 | 21 | **-54%** | +171% | +24% |
| `C3-bool-null-16` | 105 | 57 | **-46%** | +24% | -33% |
| `C4-bool-null-100` | 486 | 288 | **-41%** | -8% | -45% |
| `C6-int-null` | 42 | 16 | **-62%** | +320% | +60% |
| `C7-int-100` | 45 | 27 | **-40%** | -85% | -91% |
| `C8-float-null` | 48 | 22 | **-54%** | +243% | +57% |
| `C9-int-negativos` | 32 | 17 | **-47%** | +220% | +70% |
| `C10-int-grande` | 53 | 37 | **-30%** | +18% | -18% |

## Custo do escape de dígito (por que não chega no wire ideal)

No corpo, **dígito nu é referência de fragmento**, então o literal `1` precisa do escape (barra invertida + `1`) para não ser lido como referência.

| coluna | corpo real | corpo sem escape (hipotético) | escape custa |
|---|---|---|---:|
| `[1, 2, 3]` | `'*3+1|\\1'` | `'*3+1|1'` | **1 B** |
| `[1, 2, 3, 4, 5]` | `'*5+1|\\1'` | `'*5+1|1'` | **1 B** |
| `range(10)` | `'*10+1|\\0'` | `'*10+1|0'` | **1 B** |
| `[1.5, 2.5]` | `'*2+1,0|\\1.\\5'` | `'*2+1,0|1.5'` | **2 B** |

**Custo real é pequeno**: o escape incide por LITERAL EMITIDO, e o seq-RLE colapsa a sequência num template só — daí 1-2 B no total, não 1 B por elemento. E ele é **estrutural**, não desperdício: sem ele o decode não distingue o literal `1` da referência ao fragmento 1. Suprimi-lo exigiria uma gramática de corpo diferente sob a tag `n` — o oposto de reusar o core intocado.

## D. Namespace — o que o decode aceita hoje

| grafia | resultado |
|---|---|
| `#TCF.8b` | decoda -> `[True, False]` |
| `#TCF.8n` | **fail-loud**: referencia a fragmento inexistente: 1 (declarados 1. |
| `#TCF.8s` | decoda -> `['foo', 'bar']` |
| `#TCF.8b1` (denso w=1) | aceita |
| `#TCF.8b2` (denso w=2) | **fail-loud**: #TCF.8b: largura denso invalida w=2 p/ bool  |
| `#TCF.8b4` (denso w=4) | **fail-loud**: #TCF.8b: largura denso invalida w=4 p/ bool  |
| `#TCF.8b8` (denso w=8) | **fail-loud**: #TCF.8b: largura denso invalida w=8 p/ bool  |

## Achados (fatos, sem interpretação)

1. **RT: todos os 27 casos passam** — nenhuma lacuna abaixo é perda de dado; são bytes.

2. **13 de 27 casos em que o TCF é MAIOR que o JSON compacto**:

| id | rota | TCF | JSON | vs JSON |
|---|---|---:|---:|---:|
| `A4-vazio` | flat | 7 | 2 | **+250%** |
| `A7-int` | tipado 'n' | 16 | 7 | **+129%** |
| `A8-float` | tipado 'n' | 20 | 9 | **+122%** |
| `B1-bool-n1` | tipado 'b' | 13 | 6 | **+117%** |
| `C9-int-negativos` | tipado 'n' | 17 | 10 | **+70%** |
| `C6-int-null` | tipado 'n' | 16 | 10 | **+60%** |
| `C8-float-null` | tipado 'n' | 22 | 14 | **+57%** |
| `C5-multi-null` | .8H | 44 | 30 | **+47%** |
| `C1-bool-null-2` | tipado 'b' | 15 | 11 | **+36%** |
| `C2-bool-null-3` | tipado 'b' | 21 | 17 | **+24%** |
| `B2-bool-n2` | tipado 'b' | 14 | 12 | **+17%** |
| `A3-so-null` | flat | 12 | 11 | **+9%** |
| `A1-str` | flat | 14 | 13 | **+8%** |

Eles se separam em **dois grupos**:

   - **rota `.8H`** (1 caso): so' o `multi-col + null`, que e' a unica rota ainda NAO aberta.
   - **rota flat/tipada** (12 casos): todos de payload minusculo, onde os 7 B de cabecalho (ADR-0034) competem com um JSON de 2-17 B. Consequencia DECLARADA daquela decisao, nao lacuna nova.

3. **`bool + null`, `int`, `float` e `int + null` sairam do `.8H`** nesta rodada; so' `multi-col + null` continua la'.
4. `#TCF.8n` agora e' EMITIDO; `#TCF.8s` decoda mas o encoder nao emite (string segue implicita por exclusao).
5. O denso do bool so' aceita `w=1` — e com null a coluna usa o modo CORE, porque 1 bit nao comporta o trio {null, false, true}.
6. O bool cruza o JSON em **~4 elementos** (B3); acima disso o ganho vai a -97%. O numero cruza mais tarde: `C7-int-100` ja' e' -91%, mas `A7-int` (n=3) e' +129%.

