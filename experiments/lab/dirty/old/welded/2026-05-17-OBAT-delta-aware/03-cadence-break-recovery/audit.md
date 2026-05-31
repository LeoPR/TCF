# Audit — oportunidades residuais pos-tentativa 02

## Resumo (todos D11a-h)

| Dataset | total lines | pairs nao-compact | A | B | C | identical |
|---|---:|---:|---:|---:|---:|---:|
| D11a-datas-dia | 9 | 4 | 0 | 1 | 3 | 0 |
| D11b-datas-borda | 14 | 13 | 1 | 11 | 1 | 0 |
| D11c-datas-mensal | 7 | 4 | 0 | 3 | 1 | 0 |
| D11d-datetime-min | 6 | 3 | 0 | 3 | 0 | 0 |
| D11e-datetime-mensal | 7 | 4 | 0 | 3 | 1 | 0 |
| D11f-datetime-ms | 6 | 3 | 0 | 3 | 0 | 0 |
| D11g-datetime-us | 6 | 3 | 0 | 3 | 0 | 0 |
| D11h-datetime-ns | 6 | 3 | 0 | 3 | 0 | 0 |

## Bytes potencialmente recuperaveis (por tipo)

| Dataset | A (bytes) | B (bytes) | C (bytes) |
|---|---:|---:|---:|
| D11a-datas-dia | 0 | 7 | 26 |
| D11b-datas-borda | 6 | 140 | 6 |
| D11c-datas-mensal | 0 | 28 | 9 |
| D11d-datetime-min | 0 | 24 | 0 |
| D11e-datetime-mensal | 0 | 28 | 9 |
| D11f-datetime-ms | 0 | 24 | 0 |
| D11g-datetime-us | 0 | 24 | 0 |
| D11h-datetime-ns | 0 | 24 | 0 |
| **TOTAL** | **6** | **299** | **50** |

Legenda:
- **A**: mesmo length, diffs todos digit → potencialmente tratavel se delta consistente
- **B**: lengths diferem, alguma sobreposicao → tratavel exigiria grammar nova OU OBAT cooperar
- **C**: fora de alcance grammar atual
- **identical**: deveria ja' ter sido pego pelo RLE puro do canonical

## Outputs por dataset

Cada dataset tem 3 arquivos em `outputs/<dataset>/`:
- `body-fork-analyzed.tcf` — copia do input (do sub-exp 02) pra inspecao auto-contida
- `pairs-detailed.md` — cada par nao-compactado com a, b, diff marker, justificativa, caminho-pra-tratar
- `residual-stats.txt` — numerico (count + bytes por tipo)

## Detalhes por dataset (so' pares nao-compactados — sintese)

### D11a-datas-dia

→ [pairs-detailed.md](outputs/D11a-datas-dia/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11a-datas-dia/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11a-datas-dia/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\2026-\0*\5*-*\1*\5` | `1..4\6` | lengths diferem (19 vs 6), 3 chars compartilhados |
| 4-5 | C |  | `7\2*\2` | `7~13\3` | mesmo length, mas diffs incluem non-digit em pos [1, 2, 3, 5] |
| 7-8 | C |  | `7\30` | `1\6*-\01` | lengths diferem, pouca sobreposicao |
| 8-9 | C |  | `1\6*-\01` | `1,20,3..5` | lengths diferem, pouca sobreposicao |

### D11b-datas-borda

→ [pairs-detailed.md](outputs/D11b-datas-borda/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11b-datas-borda/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11b-datas-borda/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\202*\4*-*\0*\1*-\31` | `1..4\2*-*\01` | lengths diferem (20 vs 12), 7 chars compartilhados |
| 2-3 | B |  | `1..4\2*-*\01` | `9..11\2*\8` | lengths diferem (12 vs 10), 5 chars compartilhados |
| 3-4 | B |  | `9..11\2*\8` | `14,15\9` | lengths diferem (10 vs 7), 3 chars compartilhados |
| 4-5 | B |  | `14,15\9` | `9\3*11~12` | lengths diferem (7 vs 9), 3 chars compartilhados |
| 5-6 | B |  | `9\3*11~12` | `8\12*6` | lengths diferem (9 vs 6), 4 chars compartilhados |
| 6-7 | B |  | `8\12*6` | `1\5*-*\0*\1*19` | lengths diferem (6 vs 14), 3 chars compartilhados |
| 7-8 | B |  | `1\5*-*\0*\1*19` | `1~21,22~23~10~11~15~16` | lengths diferem (14 vs 22), 3 chars compartilhados |
| 8-9 | B |  | `1~21,22~23~10~11~15~16` | `25,22~23~18~11~12` | lengths diferem (22 vs 17), 6 chars compartilhados |
| 9-10 | B |  | `25,22~23~18~11~12` | `25,22,20,6` | lengths diferem (17 vs 10), 3 chars compartilhados |
| 10-11 | B |  | `25,22,20,6` | `1\6*22..24,19` | lengths diferem (10 vs 13), 3 chars compartilhados |
| 11-12 | B |  | `1\6*22..24,19` | `1~35,3..6` | lengths diferem (13 vs 9), 4 chars compartilhados |
| 12-13 | C |  | `1~35,3..6` | `38,30` | lengths diferem, pouca sobreposicao |
| 13-14 | A | Δ=+4 | `38,30` | `38,34` | mesmo length (5), 1 diffs todos digit |

### D11c-datas-mensal

→ [pairs-detailed.md](outputs/D11c-datas-mensal/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11c-datas-mensal/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11c-datas-mensal/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\202*\5*-*\0*\1*-\05` | `1..4\2*6` | lengths diferem (20 vs 8), 4 chars compartilhados |
| 4-5 | C |  | `8\1*\0*6` | `8~18,5~6` | mesmo length, mas diffs incluem non-digit em pos [1, 3, 4, 5, 6] |
| 5-6 | B |  | `8~18,5~6` | `20,10,6` | lengths diferem (8 vs 7), 3 chars compartilhados |
| 6-7 | B |  | `20,10,6` | `1\6*3,4,21` | lengths diferem (7 vs 10), 4 chars compartilhados |

### D11d-datetime-min

→ [pairs-detailed.md](outputs/D11d-datetime-min/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11d-datetime-min/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11d-datetime-min/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\2026-\05-\15 \09:*\0*\0*:\00` | `1~2\1*4` | lengths diferem (29 vs 7), 4 chars compartilhados |
| 4-5 | B |  | `1\1*3,4` | `1~15,6,4` | lengths diferem (7 vs 8), 3 chars compartilhados |
| 5-6 | B |  | `1~15,6,4` | `16,7,4` | lengths diferem (8 vs 6), 4 chars compartilhados |

### D11e-datetime-mensal

→ [pairs-detailed.md](outputs/D11e-datetime-mensal/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11e-datetime-mensal/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11e-datetime-mensal/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\202*\5*-*\0*\1*-\05 \09:\00:\00` | `1..4\2*6` | lengths diferem (32 vs 8), 4 chars compartilhados |
| 4-5 | C |  | `8\1*\0*6` | `8~18,5~6` | mesmo length, mas diffs incluem non-digit em pos [1, 3, 4, 5, 6] |
| 5-6 | B |  | `8~18,5~6` | `20,10,6` | lengths diferem (8 vs 7), 3 chars compartilhados |
| 6-7 | B |  | `20,10,6` | `1\6*3,4,21` | lengths diferem (7 vs 10), 4 chars compartilhados |

### D11f-datetime-ms

→ [pairs-detailed.md](outputs/D11f-datetime-ms/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11f-datetime-ms/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11f-datetime-ms/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\2025-\05-\15 \09:\00:*\0*\0*.\000` | `1~2\1*4` | lengths diferem (34 vs 7), 4 chars compartilhados |
| 4-5 | B |  | `1\1*3,4` | `1~15,6,4` | lengths diferem (7 vs 8), 3 chars compartilhados |
| 5-6 | B |  | `1~15,6,4` | `16,7,4` | lengths diferem (8 vs 6), 4 chars compartilhados |

### D11g-datetime-us

→ [pairs-detailed.md](outputs/D11g-datetime-us/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11g-datetime-us/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11g-datetime-us/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\2025-\05-\15 \09:\00:\00.\0*\0*\0*\000` | `1~2\1*4` | lengths diferem (39 vs 7), 4 chars compartilhados |
| 4-5 | B |  | `1\1*3,4` | `1~15,6,4` | lengths diferem (7 vs 8), 3 chars compartilhados |
| 5-6 | B |  | `1~15,6,4` | `16,7,4` | lengths diferem (8 vs 6), 4 chars compartilhados |

### D11h-datetime-ns

→ [pairs-detailed.md](outputs/D11h-datetime-ns/pairs-detailed.md) | [body-fork-analyzed.tcf](outputs/D11h-datetime-ns/body-fork-analyzed.tcf) | [residual-stats.txt](outputs/D11h-datetime-ns/residual-stats.txt)

| Linhas | Tipo | A: delta? | a | b | justificativa |
|---|---|---|---|---|---|
| 1-2 | B |  | `\2025-\05-\15 \09:\00:\00.\0000*\0*\0*\000` | `1~2\1*4` | lengths diferem (42 vs 7), 4 chars compartilhados |
| 4-5 | B |  | `1\1*3,4` | `1~15,6,4` | lengths diferem (7 vs 8), 3 chars compartilhados |
| 5-6 | B |  | `1~15,6,4` | `16,7,4` | lengths diferem (8 vs 6), 4 chars compartilhados |

