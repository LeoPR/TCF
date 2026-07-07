# Resultado — fidelidade de tipos no TCF.8H (Ciclo 1a) [probatório]

Números: `artifacts/` (`python run.py`). Amostras minúsculas — consistência antes de escala.

## A lacuna (provada)

O codec EXP-015 faz `str(v)`. RT em JSON tipado (`04-roundtrip.txt`):

| caso | all-string (str(v)) | resultado |
|---|---|---|
| escalares tipados | `30`→`"30"`, `true`→`"True"`, `null`→`"None"` | **RT FALHA** |
| array tipado | `1`→`"1"`, `false`→`"False"` | **RT FALHA** |

`"True"`/`"None"` são `repr` Python — nem JSON válido. O codec só era lossless em all-string.

## O conserto (naive) e o RT

**String = default (sem tag); tipo divergente = 1 letra colada no size** (`i` int, `f` float, `b` bool,
`n` null). Body JSON-canônico (`true`/`false`; `null` = body vazio). Metas (RT=OK, `04`):

```
T1  #TCF.8H nome:4,idade:4i,ativo:5b,nota:6f,obs:1n          68B  RT-OK
T2  #TCF.8H pessoas[id:8i,vip:14b                            52B  RT-OK
T3  #TCF.8H loja:7,meta{itens:3i,aberto:5b,nota:6f},produtos[sku:8,qtd:7i,promo:11b   127B  RT-OK
```
`sku:8` (string, **sem** tag) ao lado de `qtd:7i` mostra o default-string visível e auto-descritivo.

## Custo (`05-bytes-custo.txt`)

| caso | typed (lossless) | all-str (lossy) | custo líquido |
|---|---|---|---|
| T1 | 68B | 66B | **+2B** |
| T2 | 52B | 47B | **+5B** |
| T3 | 127B | 119B | **+8B** |

## Achado — tipos amarram no reorder (C5)

O custo líquido é **maior que a soma das tags** porque, quando a **folha DFS-última é tipada**, ela perde
a `última-folha-sem-size` (o parser precisa do `:size` porque a letra vem colada nele) → paga `:size` +
tag de volta. Em T2 a última (`vip`, bool) força `vip:14b` em vez de bare `vip`; em T3 idem (`promo`).

Consequência: **`SAVING(L)` agora inclui a tag de tipo**, e o **reorder** (T-FLOW S2 / C5) ganha um motivo
novo — deixar uma folha **string** por último para preservar a última-sem-size. Cross-link
[tcf8h-header-checklist](../notas/tcf8h-header-checklist.md) (C1 `:tipo` / C5 reorder).

## Decisão em aberto (pro 1b)

Tag **explícita** (o que está aqui: 1B/folha-tipada, auto-descritivo) **vs dedução** (inferir o tipo do
body via `analyze_column`/`is_numeric`, zero header — mas **ambíguo**: `"30"` string e `30` int têm o mesmo
body, exatamente o problema self-description do hex). Provável convergência: **híbrido** — deduzir quando não
ambíguo, tag só quando o valor colide com string (mesma filosofia hex-default). Medir no 1b.

## Limites (v0 deste lab)

- Coluna homogênea (a tag é por-coluna, do 1º valor); tipo misto na mesma coluna = fora do escopo naive.
- `null` scalar via body vazio + tag `n` — RT OK; `null` **dentro** de array tipado ainda não testado (é 1b).
- Amostras minúsculas T1/T2/T3 — escala (array vazio, chave ausente, aninhamento fundo) é o 1b.
