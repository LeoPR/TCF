# seq-RLE sem FLOOR — dimensionando a correção (2026-07-25-2107)

`bruto` = corpo com `hcc_seq_rle=False` · `sempre` = comportamento ATUAL (compacta incondicionalmente) · `floor` = `min` dos dois, que é o que a correção emitiria. Bytes do **corpo**.

## A. SENSÍVEIS — onde o marcador de delta não paga

| id | n | bruto | sempre | floor | o FLOOR economiza | RT |
|---|---:|---:|---:|---:|---:|---|
| `A-ruido10-n100` | 100 | 310 | 316 | **310** | +6 B | OK |
| `A-ruido10-n1000` | 1000 | 3104 | 3110 | **3104** | +6 B | OK |
| `A-ruido100-n100` | 100 | 383 | 422 | **383** | +39 B | OK |
| `A-ruido100-n1000` | 1000 | 3899 | 3948 | **3899** | +49 B | OK |
| `A-ruido1000000-n100` | 100 | 793 | 867 | **793** | +74 B | OK |
| `A-ruido1000000-n1000` | 1000 | 7854 | 8573 | **7854** | +719 B | OK |
| `A-uuid-n200` | 200 | 2663 | 2663 | **2663** | — | OK |
| `A-precos-n200` | 200 | 1555 | 1279 | **1279** | — | OK |

## B. FAVORÁVEIS — onde o seq-RLE ganha (o FLOOR não pode estragar)

| id | n | bruto | sempre | floor | o FLOOR economiza | RT |
|---|---:|---:|---:|---:|---:|---|
| `B-seq-n1000` | 1000 | 4890 | 31 | **31** | — | OK |
| `B-passo5-n200` | 200 | 978 | 30 | **30** | — | OK |
| `B-ids-n200` | 200 | 1600 | 15 | **15** | — | OK |
| `B-datas-n200` | 200 | 1181 | 1110 | **1110** | — | OK |
| `B-emails-n200` | 200 | 2228 | 2095 | **2095** | — | OK |

## C. MISTOS — a fronteira

| id | n | bruto | sempre | floor | o FLOOR economiza | RT |
|---|---:|---:|---:|---:|---:|---|
| `C-seq-com-ruido` | 200 | 1121 | 1157 | **1121** | +36 B | OK |
| `C-blocos` | 200 | 1179 | 853 | **853** | — | OK |
| `C-quase-seq` | 200 | 885 | 79 | **79** | — | OK |

## Resumo

- **RT: 32/32** (as duas formas decodam — o corpo sem marcador é um wire válido, o decode só expande o que existe)
- o seq-RLE **piorava** em **7 de 16** casos
- economia total do FLOOR nesta matriz: **929 B**
- **em nenhum caso o FLOOR piora** (é `min`, nunca-pior por construção)

## Evidência — o marcador que não paga

```
'*2+498217|\\168116'
    marcador: 17 B
'*2-426119|\\988640'
    marcador: 17 B
```

Um `*2+<delta>|<template>` só compensa se `len(marcador) < len(as 2 linhas cruas)`. Com delta de 6 dígitos e template de 6 dígitos, não compensa.

