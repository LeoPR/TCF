# Lab 2026-07-13-2325 — hierarquia fortificada + cardinalidade (1:1/1:N/N:1/N:N)

**Status**: pesquisa/medido, sintético. **Ticket**:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).
**Base**: tabelão do lab `2026-07-13-2301` + teoria da peça 7/8
([teoria-cardinalidade](../notas/teoria-cardinalidade.md)). **SEM tipos/nulos** (ortogonal, depois).

Fortifica a hierarquia e recupera o estudo de dimensionalidade, a pedido do owner:
firmar a gramática do header + uso; recuperar 1:1/1:N/N:1/N:N e sua aplicação prática.

## Gramática do header `#TCF.8H` (firme — o que testamos)

```
#TCF.8H <meta>\n<bodies-por-coluna-DFS-concatenados>
```

`<meta>` é recursivo, itens separados por `,`:

| forma | cardinalidade | significa |
|---|---|---|
| `name:size` | folha escalar | coluna `name`; `size` = bytes-incl-LF do body (decimal) |
| `name{ ...itens... }` | **1:1** | objeto aninhado — os campos são colunas-pai (repetem no tabelão) |
| `name[ ...itens... ]` | **1:N** | array de objetos — os campos variam por elemento |
| `name[]:size` | **1:N** | array de escalares — a coluna `name` = elementos achatados |

Regras consagradas (opt, default-on): **última folha DFS omite `:size`** (EOF reconstrói);
**omit-closes** dropa o run final de `]`/`}` (o `\n` + EOF auto-fecham). Chaveamento por
**CAMINHO** (corrige o bug de nome-repetido do protótipo 1830). `<bodies>` = `tcf.encode`
por coluna em ordem DFS, fatiados pelos sizes — **o motor multi-col real** (RLE de pai sai de graça).

Exemplo real (`outputs/01-endereco.tcf`, RT-exato):
```
#TCF.8H nome:39,plano:20,endereco{rua:58,cidade:25,geo{lat:36,lon:36}},telefones[
*2|Ana Souza          <- pai repete: 2 telefones (RLE = multiplicidade)
Bruno Lima
*3|Carla Nunes
*3|Premium            <- plano N:1 compartilhado (dict/RLE)
...
```

## Uso (o fluxo)

`JSON aninhado -> derive_schema -> denormaliza (tabelão, pai repete) -> tcf.encode por
coluna -> #TCF.8H -> decode -> re-aninha (agrupa por chave contígua, recursivo) -> JSON`.
O teste central é `decode(encode(records)) == records`.

## Cardinalidade -> mecânica -> hierarquia (o estudo, peça 7)

Teste de contagem de distintos = descoberta de FD (`cardinality.py`): `dA, dB, dAB`;
`A→B sse dAB==dA`, `B→A sse dAB==dB`.

| classe | FD | mecânica TCF | na hierarquia |
|---|---|---|---|
| **1:1** | ambas | nativo / dict bijetivo | `{}` objeto aninhado — **ANINHA** |
| **1:N** | só B→A (pai repete) | hierarquia = dual do RLE `*N\|pai` | `[]` array — **ANINHA** |
| **N:1** | só A→B (B repete) | `@dict` low-card (o motor já emite) | coluna compartilhada — **não é ramo** |
| **N:N** | nenhuma | tabela-ponte (2 dicts + pares) | **NÃO aninha** (fail-loud) |

- **1:1 e 1:N ANINHAM** — os únicos que viram estrutura de árvore (`{}` e `[]`).
- **N:1 é uma COLUNA**, não um ramo: um valor low-card compartilhado entre registros;
  o motor multi-col comprime via @dict/RLE (`outputs/08-n1-*`). Distingue-se do pai do
  1:N: distintos < nº de registros = N:1 (compartilhado); == registros = pai (multiplicidade).
- **N:N NÃO vira árvore simples**: 2 arrays no mesmo nível = produto cartesiano que inventa
  pares → **fail-loud** (`outputs/09-nn-*`); o caminho é ponte/junction ou dois 1:N separados.

**Eixo ortogonal** (peça 8): cardinalidade (multiplicidade, RLE↔fk conservada) **⊥**
compressibilidade (largura-de-valor, @dict encolhe). O ganho de bytes do N:1 é a LARGURA
(valor largo repetido → código estreito), não o ×N.

## Casos exercitados (RT-exato, roundtrip .json byte-idêntico)

| entrada | estrutura | header |
|---|---|---|
| `inputs/01-clientes-endereco-telefones.json` | `{}` 1:1 (endereco⊃geo) + `[]` 1:N (telefones) | `nome,plano,endereco{rua,cidade,geo{lat,lon}},telefones[` |
| `inputs/02-clientes-pedidos-itens.json` | `[]` 1:N aninhado (pedidos⊃itens) | `cliente,pedidos[data,itens[produto,qtd` |
| `inputs/03-cardinalidades-flat.csv` | os 4 casos p/ classificação | — |

## Rodar

```powershell
python experiments/lab/dirty/2026-07-13-2325-hierarquia-cardinalidade/run.py
```

Zero `src/tcf` (read-only `tcf.encode`/`decode`). Ver [result.md](result.md).

## Limites (registrados — próximos passos sobre esta base)

- **Fronteira pai/filho por chave contígua**: registros/elementos adjacentes com chave
  idêntica se fundiriam (ambiguidade FD/chave da peça 7 — precisa de marcador de fronteira
  no caso geral; dados limpos distintos funcionam).
- **N:N / multi-array por nível**: fail-loud; ponte/link-posicional é a peça 9 (não aqui).
- **Sem tipos/nulos**: ortogonal, camada seguinte (labs 1835/1955/2019).
- Sintético, N=1 lab; sem gate real-world (isto é FORMA, não medida de ganho).
