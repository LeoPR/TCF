# 2026-08-17-2200 — A7 (array-em-array) + F4: o plano fecha

Executa os dois itens que faltavam do
[plano de 2000](../../../notas/2026-08/2026-08-17-2000-plano-grupo-x-array.md):
**A7** (array-EM-array, que o lab 2100 não cobriu) e **F4** (a regra "última coluna omite
size" com N colunas no lugar de 1, que nunca foi exercitada).

## A forma real, sondada antes

```
[{"v": [["12.50"], ["7.99","3.00"]]}]   →   #TCF.8Hv#:3[#:6[

  v  count        size=3      ← nível 0: quantos sub-arrays por registro
  v  count1       size=6      ← nível 1: quantos itens por sub-array
  v  arr_scalars  size=None   ← os ITENS — a ÚLTIMA coluna OMITE o size
```

Três níveis dão `count`, `count1`, `count2`, e só então os itens.

## Veredito

| critério | resultado |
|---|---|
| **F1** contagem de **algum nível** mudou | **0/6** |
| **F2** perdeu RT com grupo | **0/6** |
| **F4** "última-sem-size" quebrou | **0/6** |
| RT com grupo | **6/6** |

| caso | níveis | agrupou | sem | com | última entrada |
|---|--:|:-:|--:|--:|---|
| B1 2 níveis, 1 registro | 2 | sim | 61 | 79 | `item.c1:!` |
| B2 2 níveis, 2 registros | 2 | sim | 76 | 94 | `item.c1:!` |
| B3 2 níveis, sub-array vazio | 2 | sim | 55 | 73 | `item.c1:!` |
| B4 **3 níveis** | 3 | sim | 76 | 94 | `item.c1:!` |
| B5 **3 níveis**, data ISO (3 campos) | 3 | sim | 114 | 129 | `item.c2:!` |
| B6 template não-uniforme | 2 | **não** | 60 | 60 | `item:!` |

**F1 vale em todos os níveis simultaneamente.** No B5 (3 níveis, 3 campos de grupo):

```
count   sem=3 B  com=3 B
count1  sem=5 B  com=5 B
count2  sem=5 B  com=5 B
```

Nenhuma contagem se move quando 1 coluna de itens vira 3.

**F4 fecha**: com grupo, quem omite o size é a **última das N** (`item.c1` com 2 campos,
`item.c2` com 3), e o decode fatia até EOF normalmente. A regra não precisou de exceção.

## O que isto NÃO diz

- **Ganho não medido** — datasets de 1–2 registros; o marcador é custo fixo, então o grupo
  fica maior aqui. Mesma ressalva do lab 2100: isto mede **composição**, não byte.
- **F5** (gate por-registro) não disparou, mas o gate do mock é **global por construção** —
  não provei o comportamento do gate real.
- O mock reproduz a **ordem** de colunas do `.8H` real (contagens por nível, depois itens) e
  a regra de omissão, mas **não** o `emask` por nível (P3b) combinado com múltiplos níveis.
- Sintético, minúsculo, uma execução.

## Evidência

18 wires (por caso: `.8H-real`, `mock-sem-grupo`, `mock-com-grupo`) + 6 roundtrips.

## Conexões

- Plano: [`notas/2026-08-17-2000`](../../../notas/2026-08/2026-08-17-2000-plano-grupo-x-array.md)
- [`2100`](../2026-08-17-2100-grupo-x-array/) (A1–A10, um nível) ·
  [`1700`](../2026-08-17-1700-grupo-como-combinador-do-H/) · [`1900`](../2026-08-17-1900-vale-a-pena/)
- [roadmap-hipoteses Pacote 13](../../../notas/2026-05/roadmap-hipoteses.md)
