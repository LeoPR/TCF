# 2026-07-05 16:50 — Multi-col + marcador `N` (a via mais simples) [probatório]

**Peça 4** do grupo [estudo-tcf-hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) ·
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md). **Auto-contido**: `mnlib.py` +
`tcf` (biblioteca; **não toca `src/`**). `python run.py` regenera tudo.

## A ideia (do owner) — muito mais simples que a peça 3

Não são blocos empilhados com header de linking (peça 3). É **a estrutura multi-col que já existe**, só
com um **complemento barato**:
1. flag **`N`** no shebang (`#TCF.8 M N`) — irmão do `M`;
2. uma linha **`#H`** de hierarquia que **reagrupa as colunas** (que já vêm em ORDEM) na árvore.

As colunas continuam **nomeadas** (obrigatório — o nome aparece na referência principal / no meta), e são
**agrupadas pela ordem**. Colunas podem ter comprimentos diferentes (raiz/objeto = 1 linha; array = N) — o
`N` sinaliza isso, e o byte-size do meta delimita. **É a estrutura que já temos, só com um complemento que explica.**

## O modelo (S4, mínimo — `03-tcf-mn-S4.tcf.txt`)

```
#TCF.8 M N
#H nome telefones[tel]        ← hierarquia: nome (escalar raiz) + telefones (array c/ coluna tel)
9=nome,tel                     ← meta multi-col NORMAL (nomes + sizes; última coluna sem size)
leonardo                       ← corpo da coluna nome (1 valor → escalar)
(\41) \9999*\9*-\9999          ← corpo da coluna tel (2 valores → array)
1\4*3
```
Generaliza p/ árvore (S6 — `03-tcf-mn-S6.tcf.txt`):
```
#TCF.8 M N
#H nome endereco{rua cidade geo{lat lon}} telefones[tel]
9=nome,19=rua,9=cidade,8=lat,8=lon,tel
<corpos das 6 colunas, na ordem DFS; ragged>
```
Notação `#H` (draft): escalar = `nome` · objeto = `nome{...}` · array = `nome[col1 col2]`.

## Estágios (= a ordem em `artifacts/`)

```
01 ENTRADA    inputs/{S4,S6} → 01-entrada-{S4,S6}.json
02 TRADUÇÃO   doc → colunas em ordem + a linha #H → 02-traducao-{S4,S6}.txt
03 TCF-MN     1 multi-col com flag N + #H → 03-tcf-mn-{S4,S6}.tcf.txt
04 DECODE     split por bytes → colunas → reagrupa pela #H → JSON → 04-decode-roundtrip-{S4,S6}.txt (OK)
```

## vs peça 3 (linking) — o trade

| | P3 (blocos empilhados + linking) | **P4 (multi-col + N)** |
|---|---|---|
| forma | N TCFs `@block` + header de arestas | **1** multi-col + 1 linha `#H` |
| simplicidade | mais cerimônia | **reusa o que já existe** |
| seek por tabela | bloco independente/buscável | colunas num blob só |
| dedup entre colunas | separado por bloco | o multi-col já compartilha |

## Aberto (pro redesenho / compactação)

- **Redundância de nomes**: os nomes aparecem no `#H` **e** no meta. O owner sugeriu "a **primeira
  coluna** marcada é o indicador de hierarquia" → **fundir** #H no meta (1ª entrada = hierarquia; demais
  = sizes), ou o #H referenciar colunas por **posição** (`0`, `1`) em vez de nome. Economiza.
- **Tipos**: aqui tudo é string (fixtures all-string); num/bool/null pediriam `:tipo` (como na peça 3).
- **Nomes de coluna repetidos** (dois `tel` em ramos diferentes): usar caminho/posição, não só o nome.
- **Array-dentro-de-array / N raízes**: continua precisando de link posicional (peça 5), não coberto aqui.

## Estado

- **É**: modelo multi-col+`N`+`#H`, **decoda S4 e S6** (RT OK). O mais simples até agora.
- **Será**: compactar (fundir #H no meta / posição em vez de nome); tipos; comparar bytes com P3.

Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
