# Lacunas da frente de tipos — evidência em arquivo (2026-07-25-0200)

Estado REAL do `src/tcf`, medido. `JSON` = equivalente compacto (`separators=(',',':')`). Cada linha tem os arquivos em `inputs/` · `intermediates/` · `outputs/`.

## A. Rota que cada tipo toma HOJE

| id | rota | TCF (B) | JSON (B) | vs JSON | RT |
|---|---|---:|---:|---:|---|
| `A1-str` | flat | 14 | 13 | **+8%** | OK |
| `A2-str-null` | flat | 13 | 14 | **-7%** | OK |
| `A3-so-null` | flat | 12 | 11 | **+9%** | OK |
| `A4-vazio` | flat | 7 | 2 | **+250%** | OK |
| `A5-bool` | tipado 'b' | 14 | 17 | **-18%** | OK |
| `A6-bool-alternado` | tipado 'b' | 23 | 353 | **-93%** | OK |
| `A7-int` | .8H | 31 | 7 | **+343%** | OK |
| `A8-float` | .8H | 36 | 9 | **+300%** | OK |
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

## C. As lacunas — null fora da rota flat

| id | rota | TCF (B) | JSON (B) | vs JSON | RT |
|---|---|---:|---:|---:|---|
| `C1-bool-null-2` | .8H | 36 | 11 | **+227%** | OK |
| `C2-bool-null-3` | .8H | 46 | 17 | **+171%** | OK |
| `C3-bool-null-16` | .8H | 105 | 85 | **+24%** | OK |
| `C4-bool-null-100` | .8H | 486 | 526 | **-8%** | OK |
| `C5-multi-null` | .8H | 44 | 30 | **+47%** | OK |
| `C6-int-null` | .8H | 42 | 10 | **+320%** | OK |

## D. Namespace — o que o decode aceita hoje

| grafia | resultado |
|---|---|
| `#TCF.8b` | decoda -> `[True, False]` |
| `#TCF.8n` | **fail-loud**: #TCF.8: discriminador 'n' desconhecido — nao decodav |
| `#TCF.8s` | **fail-loud**: #TCF.8: discriminador 's' desconhecido — nao decodav |
| `#TCF.8b1` (denso w=1) | aceita |
| `#TCF.8b2` (denso w=2) | **fail-loud**: #TCF.8b: largura denso invalida w=2 p/ bool  |
| `#TCF.8b4` (denso w=4) | **fail-loud**: #TCF.8b: largura denso invalida w=4 p/ bool  |
| `#TCF.8b8` (denso w=8) | **fail-loud**: #TCF.8b: largura denso invalida w=8 p/ bool  |

## Achados (fatos, sem interpretação)

1. **RT: todos os 23 casos passam** — nenhuma lacuna abaixo é perda de dado; são bytes.

2. **12 de 23 casos em que o TCF é MAIOR que o JSON compacto**:

| id | rota | TCF | JSON | vs JSON |
|---|---|---:|---:|---:|
| `A7-int` | .8H | 31 | 7 | **+343%** |
| `C6-int-null` | .8H | 42 | 10 | **+320%** |
| `A8-float` | .8H | 36 | 9 | **+300%** |
| `A4-vazio` | flat | 7 | 2 | **+250%** |
| `C1-bool-null-2` | .8H | 36 | 11 | **+227%** |
| `C2-bool-null-3` | .8H | 46 | 17 | **+171%** |
| `B1-bool-n1` | tipado 'b' | 13 | 6 | **+117%** |
| `C5-multi-null` | .8H | 44 | 30 | **+47%** |
| `C3-bool-null-16` | .8H | 105 | 85 | **+24%** |
| `B2-bool-n2` | tipado 'b' | 14 | 12 | **+17%** |
| `A3-so-null` | flat | 12 | 11 | **+9%** |
| `A1-str` | flat | 14 | 13 | **+8%** |

Eles se separam em **dois grupos**, e a distinção importa:

   - **rota `.8H`** (7 casos): `bool+null`, `multi+null`, `int`, `float`, `int+null`. O envelope hierárquico custa mais do que economiza nesses tamanhos.
   - **rota flat/tipada** (5 casos): `[]`, `[None,None]`, bool com n≤2. Aqui é o cabeçalho de 7 B (ADR-0034) contra um JSON de 2-12 B — consequência declarada daquela decisão, não lacuna nova.

3. `str + null` está na rota flat (soldado 2026-07-25); `bool + null` e `multi-col + null` **não** — ainda caem no `.8H`.
4. `#TCF.8n` e `#TCF.8s` são fail-loud — só a tag `b` decoda.
5. O denso do bool só aceita `w=1`; `b2`/`b4`/`b8` são fail-loud.
6. O bool cruza o JSON em **~4 elementos** (B3); acima disso o ganho vai a −97%.

