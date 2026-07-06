# 2026-07-05 18:30 — Colchetes no meta (M/N deduzidos) [probatório]

**Peça 5** do grupo [estudo-tcf-hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) ·
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md). Auto-contido: `bracketlib.py`
+ `tcf` (**não toca `src/`**). `python run.py` regenera tudo.

## A ideia (do owner) — ainda mais simples que P4

Nem flag `M`/`N` explícito, nem linha `#H` separada. O **próprio meta das colunas** carrega a hierarquia
via **colchetes**:
```
#TCF.8
[nome:9,telefones[tel]]              ← S4: raiz [nome (folha), telefones (grupo[tel])]
leonardo
(\41) \9999*\9*-\9999
1\4*3
```
```
[nome:9,endereco[rua:19,cidade:9,geo[lat:8,lon:8]],telefones[tel]]   ← S6 (árvore)
```

## Três deduções (o barato)

- **`M` deduzido**: várias colunas ⇒ multi-col. (o `M` "é só preparo pra multicolumn")
- **`N` deduzido**: presença de `[...]` aninhado ⇒ hierárquico.
- **array vs objeto DEDUZIDO do nº de linhas dos filhos**: grupo cujas folhas diretas têm **>1 linha** =
  **array** (1:N); **1 linha** = **objeto** (1:1). ("repetir pode ser deduzido dos filhos gerados")
- **`nome:9`** = size do corpo daquela coluna (última folha em DFS omite, estilo multi-col). O nome do
  grupo (telefones, endereco) reconstrói o campo. A raiz é objeto (1 instância).

## A hierarquia é OPCIONAL

Os colchetes só importam **se for pra reconstruir o JSON**. Sem eles (meta plano `nome,rua,...`) é um
multi-col comum. → a semântica de hierarquia é uma **camada opt-in** por cima do que já existe.

## Estágios (`artifacts/`)

```
01 ENTRADA   → 01-entrada-{S4,S6}.json
02 TRADUÇÃO  colunas em ordem + cardinalidade (nº linhas) → 02-traducao-{S4,S6}.txt
03 TCF-P5    1 multi-col; hierarquia nos colchetes → 03-tcf-p5-{S4,S6}.tcf.txt
04 DECODE    parse colchetes → split bytes → dedução array/objeto → JSON → 04-decode-roundtrip-{S4,S6}.txt (OK)
```

## Tamanho (não é o foco, mas ilustra) vs peças anteriores

S4: **68B** (P5) < 82B (P4, `#TCF.8 M N` + `#H`) < 122B (P3, blocos+linking). O ganho é tirar o `#H`
separado, o flag e a redundância de nomes.

## Ambiguidades honestas (a refinar)

- Grupo de **1 linha**: não distingue **objeto** de **array-de-1** → deduz objeto (comum). Precisa de
  marca só nesse caso (ex.: `nome[]` vazio-marcado) ou aceitar a convenção.
- Grupo **só com subgrupos** (sem folha direta) → deduz objeto.
- **Nome de coluna repetido** em ramos diferentes → hoje o meta indexa por nome; precisaria posição/caminho.
- **Tipos** (num/bool/null): fixtures all-string; num/bool/null pediriam `:tipo` (fora daqui).
- **Array-dentro-de-array / N raízes**: link posicional (peça 6), não coberto.

## Estado

- **É**: hierarquia nos colchetes do meta, M/N + cardinalidade **deduzidos**, **decoda S4 e S6** (RT OK).
  A construção mais enxuta até agora.
- **Será**: resolver as ambiguidades acima (marca mínima só onde precisa) + tipos; decidir entre P3/P4/P5.

Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
