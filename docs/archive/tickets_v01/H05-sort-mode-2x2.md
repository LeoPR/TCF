# H05 — Efeito do Sort Mode: Agregados vs Filtros (2×2)

**Status:** ABERTO  
**Tipo:** Fatorial 2×2 — contribuição central do paper  
**Deps:** P04, P05  
**LLM calls:** ~600

## Hipótese

Colunas ordenadas (`sorted_rle`) melhoram accuracy em queries de agregação mas prejudicam queries de filtro que requerem correlação entre linhas.

**H5_0 (nula):** Não há interação entre sort_mode e query_type.

## O 2×2

|  | Agregado (Q5, Q8, Q9) | Filtro correlacionado (Q6, Q7, Q10) |
|--|----------------------|-------------------------------------|
| **unsorted** | baseline | baseline |
| **sorted_rle** | **+ ganho esperado** | **− perda esperada** |

## Por quê

**sorted_rle melhora agregados:**
```
id_produto[sorted]: 4:11 5:22 4:33 4:44 3:55 ...
```
→ Caneta (22) = 5 vendas. Visível *diretamente* no RLE sem contar nada.

**sorted_rle quebra filtros:**
```
id_pessoa[sorted]: 3:1 2:2 2:3 ...   ← posição não correla com vl
vl: 2.5 11.0 1.0 ...                 ← posição original
```
→ "Total gasto por Ana (id=1)?" requer correlação de posição entre `id_pessoa` e `vl`.
Com sorted, as posições não se correspondem — impossível sem a coluna original.

## Design

```
2 sort_modes × 2 query_types × 10 modelos × 5 runs = 200 calls por pergunta
Perguntas: Q5(count), Q8(top_fk) para agregados; Q6(count_by_name), Q7(sum_by_name) para filtros
```

## Output esperado

Gráfico de interação 2×2 (linhas que cruzam = interação significativa):

```
accuracy
  1.0 |     sorted ____
      |              /
  0.5 |  unsorted --/------\-- unsorted
      |                     \
  0.0 |              sorted  \____
      |---agregado--------filtro--→ query_type
```
