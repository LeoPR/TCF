# 2026-07-05 16:08 — Ligação PAI/FILHO no cabeçalho (blocos TCF empilhados) [probatório]

**Peça 3** do grupo [estudo-tcf-hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) ·
guarda-chuva [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md). **Auto-contido**:
`linklib.py` (local) + `tcf` (biblioteca; **não toca `src/`**). `python run.py` regenera tudo.

## O que estuda (o buraco que faltava)

Já temos meta que relaciona **colunas** dentro de uma tabela; **não** temos como relacionar **tabelas**
entre si. Como a hierarquia JSON é **contenção** (quem contém quem), não FK numérica, basta dizer
**quem é pai/filho**. Este lab implementa **uma técnica explícita** de ligação e prova que **decoda**.

## Técnica (draft) — hint + adjacência lado-do-pai

- **Hint no shebang**: `#TCF.8 N` (o `N` = nested, análogo ao flag `M` de multi-coluna).
- **Ligação por bloco**: `@bK <kind> <campos>`, onde cada campo é `nome:tipo` (escalar) ou `nome>J`
  (o campo é um filho → aponta pro bloco J). O kind (`root`/`obj`/`arr`) do filho está na linha dele.
  Isso carrega junto: **ordem + tipo + a aresta pai→filho**.
- Depois, os blocos empilhados: `@data K` + o TCF de cada tabela (single-col → **TCF.8** via stamp;
  multi-col → TCF.7 — peça futura uniformiza).

Exemplo (S6, `03-cabecalho-linking-S6.tcf.txt`):
```
#TCF.8 N
@b0 root nome:str endereco>1 telefones>3     ← raiz: escalar nome + filhos endereco(b1) e telefones(b3)
@b1 obj  rua:str cidade:str geo>2            ← endereco: escalares + filho geo(b2)
@b2 obj  lat:str lon:str                      ← geo — PAI é b1, não a raiz (a ligação importa!)
@b3 arr  tel:str                              ← telefones (array)
@data 0 … @data 3  (os TCFs empilhados)
```

## Estágios (= a ordem em `artifacts/`)

```
01 ENTRADA          inputs/{S4,S6} → 01-entrada-{S4,S6}.json
02 TRADUÇÃO         doc → blocos + a árvore pai/filho → 02-traducao-blocos-{S4,S6}.txt
03 CABEÇALHO+LINKING a estrutura aninhada (hint + adjacência) → 03-cabecalho-linking-{S4,S6}.tcf.txt
04 DECODE           desaninha → decoda blocos → reconstrói o JSON → 04-decode-roundtrip-{S4,S6}.txt (OK)
```

## Datasets

- **S4** `pessoa{nome} ⊃ telefones[{tel}]` — 1 filho (array). Todos os blocos single-col → **TCF.8**.
- **S6** `pessoa{nome} ⊃ endereco{rua,cidade,geo{lat,lon}} + telefones[{tel}]` — **multi-filho** +
  **multi-nível** (geo dentro de endereco) → a ligação pai/filho fica **não-trivial** (pai varia).

## Escopo (honesto) — o que NÃO cobre (é peça futura)

Classe suportada: **raiz única**; objetos aninham objetos (1:1) em qualquer profundidade; arrays de
objetos **só-escalares** (folha) pendurados em objeto de instância única. **Proibido** (levanta
`NotImplementedError`): array-dentro-de-array, objeto/array dentro de elemento de array, N raízes — esses
precisam de **link POSICIONAL** (repetition level do Dremel), que é a **peça 5** do grupo, não esta.

## Estado

- **É**: técnica de ligação pai/filho no cabeçalho, hint `#TCF.8 N`, **decoda S4 e S6** (RT OK).
- **Será**: comparar notações (ver [result.md](result.md), prior-art) → **compactar** o cabeçalho (peça 4).

Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
