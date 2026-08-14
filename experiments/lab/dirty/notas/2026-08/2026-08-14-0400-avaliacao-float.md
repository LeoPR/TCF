# Avaliação: float — o corpus tem base real, e o ganho é modesto

**2026-08-14** · pedido do owner: *"acho que o próximo seria o float não? aqui é variado por
causa do float com '1.' ou com decimais de tamanhos diferentes, os com decimais formatados,
aqueles que são entre 0 e 1 etc… dá pra ver se conseguimos uma amostra real como base ou
pegar uma literatura pra gerar sintéticos possíveis que represente algo real."*

**Não precisa de literatura: o corpus tem 30 colunas float reais**, e elas já cobrem quase
todas as variações que você listou.

---

## 1. O que existe de verdade

Varrendo os hubs de `Z:` (o extrator do int filtrava `REAL` de propósito): **30 colunas
float**, em 4 origens independentes — `online-retail`, `tpch-sf001`, `tpch-sf01`,
`wine-quality`.

E as variações que você previu estão lá, sem precisar inventar:

| variação que você listou | onde aparece, real |
|---|---|
| **float com `1.`** (inteiro em roupa de float) | `l_quantity` = `17.0`, `p_retailprice` = `901.0`, `CustomerID` = `17850.0` — **todas as 2000 linhas** com 1 casa |
| **decimais de tamanhos diferentes** | `UnitPrice` `{1 casa: 139, 2: 1861}`; `chlorides` `{1: 15, 2: 219, 3: 1766}` |
| **entre 0 e 1** | `l_discount` (0.00–0.10), `l_tax`, `citric_acid`, `density` (0.9978) |
| **decimais formatados** | `density` `{3: 146, 4: 1082, 5: 755}` — precisão fixa de instrumento |

**Uma variação que você não listou e o corpus tem**: `alcohol` traz
`{1: 1985, 2: 9, 13: 4, 14: 2}` — seis valores como `10.0333333333333`, que são **médias
sujas** vindas do dataset. Custam 1,3% do texto em 0,3% dos valores, e — como se vê abaixo —
**quebram a escala**.

## 2. O que o núcleo faz hoje, e o que os candidatos dariam

Candidatos testados, todos generalizações do que o projeto já tem (nada inventado):

- **ESCALA**: `float → int × 10^k` — a ideia do ordinal do `data-iso`;
- **ESCALA+PAD**: depois da escala, o `IntPadSpec` soldado hoje;
- **SPLIT**: parte inteira | decimal, via o split estrutural (ADR-0026).

| coluna | núcleo | escala | split | melhor | quem |
|---|---:|---:|---:|---:|---|
| `tpch.o_totalprice` | 19.052 | **17.235** | 17.657 | 17.235 | escala |
| `tpch.l_extendedprice` | 17.076 | **15.623** | 16.137 | 15.623 | escala |
| `tpch.c_acctbal` | 11.721 | **10.351** | 11.697 | 10.351 | escala |
| `wine.density` | 9.045 | 8.870 | **7.778** | 7.778 | **split** |
| `wine.chlorides` | 4.012 | **3.449** | 4.872 | 3.449 | escala |
| `wine.pH` | 2.968 | 2.798 | **2.634** | 2.634 | **split** |
| `wine.alcohol` | 2.864 | **falha** | **2.530** | 2.530 | **split** |
| `retail.UnitPrice` | 3.075 | **2.866** | 4.351 | 2.866 | escala |
| `tpch.l_quantity` | 2.355 | 2.255 | **2.241** | 2.241 | **split** |

**Agregado: 78.782 → 72.504 B = 8,0% menor.** A escala vence em 8 de 12; o split em 4.

## 3. As três leituras que importam

**(a) O ganho é modesto.** O melhor caso individual é 1,16×; o agregado é 8%. Compare com o
que já foi soldado: o `IntPadSpec` deu mediana **1,72×** e o `data-iso` transforma 414 B em
26. Float é **outra ordem de grandeza de retorno**.

**(b) O `ESCALA+PAD` não acrescenta nada** — em todas as 12 colunas ele empatou com a escala
pura. Depois de escalar, a largura já fica uniforme, e o `int_pad_para` corretamente devolve
`None`. Ou seja: **o spec de inteiro soldado hoje não é reaproveitável para float**, ao
contrário do que eu esperava.

**(c) A precisão suja quebra a escala.** Em `wine.alcohol`, os seis valores de 13–14 casas
tornam impossível uma escala exata — a coluna inteira perde o candidato. Um spec de float
precisaria de **fallback literal por valor** (que o Protocol das natures já prevê), mas o
custo é que a coluna deixa de ter escala única.

## 4. E o split de novo

Onde a escala não serve, quem ganha é o **split** — e ele só existe na rota multi-col. É o
terceiro achado seguido apontando para o **`T-SPLIT-SINGLE-COL`** (data: 1,35×–2,7×;
datetime: **7,13×**; agora float: vence em 4 de 12 colunas).

## 5. Recomendação

1. **Não abrir spec de float agora.** 8% agregado não paga um spec novo, com o custo de
   decidir escala por coluna, lidar com precisão suja e escolher entre escala e split caso a
   caso. O `.9` é o lugar disso, se for.
2. **O `T-SPLIT-SINGLE-COL` já é o item mais bem sustentado da fila** — três avaliações
   independentes convergiram nele, e ele **não precisa de spec nenhum**.
3. **Sobre sintéticos**: como o corpus real cobre quase tudo, sintético aqui serviria só para
   os regimes ausentes — notação científica (`1e-5`), negativos com decimal, e precisão alta
   uniforme (16+ casas). Vale quando/se o float voltar à fila; hoje não é o gargalo.

## 6. Fila revisada dos tipos

| tipo | estado |
|---|---|
| bool · str · data · **int** | fechados (int soldado hoje) |
| **float** | avaliado — 8%, fica para o `.9` |
| **hora** | avaliado — 1,03% em real, fica para o fim (mas os sintéticos são devidos) |
| **datetime** | não avaliado, e o split já dá 7,13× nele |

O que sobra de maior retorno **não é um tipo** — é o `T-SPLIT-SINGLE-COL`.
