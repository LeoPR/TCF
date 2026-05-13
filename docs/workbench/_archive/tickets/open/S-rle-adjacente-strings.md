---
title: RLE adjacente de strings (linhas idênticas consecutivas)
type: study
status: open
priority: medium
created: 2026-05-10
---

## Contexto

Os labs 14-15 dirty exploraram RLE (Run-Length Encoding) sobre
linhas adjacentes idênticas. A partir do lab 18, o esquema mudou
para usar **line-ref** (`=N`) onde toda repeticao vira uma
referencia de linha — mas isso NAO eh RLE classico.

Diferenca:

### Line-ref (atual)
```
red
=1       ← repete linha 1
=1
=1
=1
```
4 linhas de `=1` = 12B (4 chars cada × 3 + linha 1)

### RLE adjacente (nao implementado)
```
red×4    ← run-length: red 4 vezes
```
Uma linha de `red×4` = 5B

### Line-ref com count (RLE estilo line-ref)
```
=1×4     ← idx 1 repetido 4 vezes
```

## Quando RLE adjacente brilha

Em datasets com:
- **Categoricas** com runs longos (`red red red red red`)
- **Booleans** (`true true true true`)
- **Status flags** (`active active active`)

Ganho potencial: 50-70% sobre line-ref onde runs >= 3.

## Quando NAO brilha

- Categoricas com runs curtos (1-2): line-ref ja eh otimo
- Strings unicas (URLs, IDs): nenhum RLE possivel
- Hierarquia profunda: encadeamento `*N=P+ext` ja captura

## Sintaxe proposta

Marker: `×N` ou `<N>` apos o token a repetir:
```
red×3              ← red 3 vezes adjacente
=1×5               ← idx 1 (= linha 1) 5 vezes
*green×4           ← declara green E repete 4 vezes
```

**Cuidado**: `×` nao eh ASCII basico (codepoint U+00D7). Alternativas:
- `red*3` — colide com declaracao
- `red:3` — colide com header de coluna (bug 29-B)
- `red#3` — pode ser limpo
- `red@3` — limpo se nao houver `@` em strings (impossivel garantir)
- `red~3` — limpo
- `red+3` — colide com encadeamento `*N=P+ext`

Provavel: `~N` (tilde + numero).

## Decisao automatica de quando aplicar

Encoder detecta runs adjacentes:
```python
def detect_runs(values):
    runs = []
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[j+1] == values[i]:
            j += 1
        run_len = j - i + 1
        if run_len >= 3:  # threshold
            runs.append((i, run_len, values[i]))
        i = j + 1
    return runs
```

Aplicar RLE so se run_len >= threshold (ex: 3) — abaixo, line-ref
eh equivalente ou melhor.

## Lab 24 — onde RLE faltou

Em E5 categoricas (100 valores, 5 unicos), pelo principio dos
pombos, varios runs de 2-4 linhas adjacentes existem. RLE pegaria
~10-30% extras vs line-ref.

Em E2 emails-1000, nao se aplica (cada linha unica).

Em E7 urls-1000 (shuffled), nao se aplica.

Em E6 misto, raramente se aplica (3 categorias × 500, sem ordem
implicita).

## Quando implementar

No port pra clean prototype:
- Implementar detector de runs (pre-pass)
- Aplicar RLE so onde run_len >= 3
- Validar RT
- Comparar bytes em E5 (provavel ganho)

## Relacionado

- Lab 14 (RLE+DICT combinado) — primeira exploracao
- Lab 15 (marcador deducao) — relacionado
- [H-compression-v04-roadmap](H-compression-v04-roadmap.md)
- [S-supressao-implicita-marcadores](S-supressao-implicita-marcadores.md)
