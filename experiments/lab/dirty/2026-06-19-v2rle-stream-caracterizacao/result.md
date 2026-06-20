# V2-RLE-STREAM — caracterização [resultado]

**Data**: 2026-06-19 · resultado (lab dirty, **read-only, NÃO tocou `src/tcf`**).
**Hipótese**: aplicar RLE no **stream de índices do V2-B** (`@dict`) reduz bytes onde há runs
adjacentes do mesmo índice (coluna clusterizada/ordenada). Script: [`analyze.py`](analyze.py) ·
medições brutas: [`result.txt`](result.txt).
**Status**: `CLOSED-INSUFFICIENT-GAIN`.

## Exemplo visual — o que a hipótese queria resolver (e por que não deu)

### Se os dados fossem assim

Uma coluna `situacao` (campo de cadastro, 16 linhas) — poucos valores distintos que se repetem:

```
linha:  1   2   3   4   5   6        7   8   9          10  11  12  13  14  15  16
valor:  ATIVA×5 ........ BAIXADA  ATIVA×2  SUSPENSA  ATIVA×6 .............. BAIXADA
```

### Como o TCF já guarda hoje (V2-B, modo @dict)

O V2-B troca cada valor por um **índice** numa tabela de únicos, e guarda os índices num **stream**
(1 char por linha, alfabeto base-94 — aqui `!`=0, `"`=1, `#`=2):

```
tabela de únicos:  0=ATIVA  1=BAIXADA  2=SUSPENSA          (guardada 1×)
stream (16 chars): ! ! ! ! ! " ! ! # ! ! ! ! ! ! "
                   └─5×ATIVA─┘ B └2×A┘ S └──6×ATIVA──┘ B
```

O stream tem **runs adjacentes** (`!!!!!`, `!!!!!!`) — repetição que o packing cru **não** explora:
gasta 1 char por linha mesmo quando o índice é o mesmo da linha anterior.

### O que o V2-RLE-STREAM tentava fazer

Aplicar **RLE no stream**: trocar um run de `m` índices iguais por `marcador + contagem + token`
(`§N!`; literal quando não compensa). No exemplo:

```
stream cru (16):     ! ! ! ! ! | " | ! ! | # | ! ! ! ! ! ! | "
stream RLE (11):     §5!         "   ! !   #   §6!            "
                     └ run 5 ┘       └lit┘     └ run 6 ┘
economia: 16 → 11 chars (−31% NO STREAM)
```

Em runs **longos** (ex: 100 ATIVA seguidos) seria dramático: 100 chars → `§d!` (~4 chars).
**A intuição é correta** — há repetição ali que ninguém estava aproveitando.

### Por que não deu certo (3 razões, medidas)

**(1) Onde os runs são LONGOS, o tcf-`*N|` já ganha — e o dict nem é escolhido.** Se a coluna está
agrupada/ordenada, as LINHAS INTEIRAS ficam idênticas e adjacentes, e o modo `tcf` (OBAT/HCC) as
encoda com o RLE de linha `*N|`, que **vence o fallback** `min(tcf, raw, @dict, %split)`:

```
coluna ordenada → modo tcf:   *13|ATIVA   *2|BAIXADA   SUSPENSA      (~25 bytes a coluna toda)
                              (o @dict nem entra → não há stream pra RLE-ar)
```

Ou seja: **stream-RLE e tcf-`*N|` disputam o MESMO fenômeno**, e o tcf já o resolve melhor onde ele
é forte. O stream-RLE só "sobra" em **runs curtos** (ordem natural) — onde o ganho absoluto é pequeno,
exceto se um valor domina (skewed: `situacao` chegou a +55% no [nicho](result_forms.txt)).

**(2) O brotli já faz isso.** O stream `!!!!!"!!#!!!!!!"` é trivialmente comprimível por qualquer
compressor a jusante (é byte repetido). RLE-ar antes só adiciona os bytes de marcador que o brotli
teria resolvido sozinho → sob brotli o resultado é **neutro a pior** (−1,4% a −11% medido).

```
                        textual-puro      sob brotli
stream cru   (16) ──►   16 B              ~6 B
stream RLE   (11) ──►   11 B  (ganha)     ~6 B  (empata/perde: marcador vira overhead)
```

**(3) Diluição.** Numa tabela real, esse stream é uma fração mínima do blob — a tabela de únicos +
as colunas high-card (ids, decimais, texto livre) dominam. 31% de 16 bytes = 5 bytes salvos num blob
de centenas. Por isso o **weighted real ficou em +1,19%** (não os 31% do stream isolado).

> **Resumo da intuição**: V2-RLE-STREAM mira repetição real no stream do dict. Mas essa repetição
> (a) é melhor capturada pelo `*N|` quando é longa (o dict nem é escolhido), (b) é capturada de graça
> pelo brotli quando há compressor a jusante, e (c) é diluída no blob quando a tabela é larga. Sobra
> um nicho estreito: payload minúsculo, textual-puro, coluna skewed em ordem natural.

## Método

`encode(table)` real → gadget `LazyTCF` identifica colunas `@dict` e extrai o stream → modelo RLE
ótimo por run (marcador reservado `0x01` + count base-94 + token; literal quando RLE não compensa).
Métricas: economia textual (% do blob) e **sobrevivência sob brotli-q11** (proxy do uso com
compressor a jusante). 7 datasets **reais** (adult, tpch lineitem/orders/customer, br-identidades,
receita-cnpj, ibge), amostra 1,5k-20k linhas/tabela.

## Resultados

| dataset/tabela | @dict cols | economia textual (% blob) | sob brotli | sort_by upper |
|---|---|---|---|---|
| adult-census/adult | 11/15 | **+7,34%** | −1,43% | relationship 13,0% |
| tpch/lineitem | 7/16 | +0,64% | −2,42% | 0,79% |
| tpch/orders | 4/9 | +0,17% | −0,86% | 0,17% |
| tpch/customer | 2/8 | +0,01% | −2,58% | 0,01% |
| br-identidades/pessoas | 1/6 | +0,00% | −0,18% | 0,0% |
| receita-cnpj/estabelecimentos | 3/8 | +1,96% | −0,73% | uf 2,06% |
| ibge/municipios | 2/8 | +0,56% | −1,82% | 0,68% |

- **Weighted textual: +1,19%** (46.375 B / 3.887.648 B). **0/7 ≥ 15%** → **não passa o gate.**
- **Downstream (brotli) agregado: −1,39%** — a economia **some e inverte**: o brotli já captura os
  runs; os marcadores RLE viram overhead.

## Leitura

- **Por coluna** há ganhos grandes no *stream* de colunas skewed/low-card (race +53,9%, situacao
  +55,0%, l_returnflag +37,0%). Mas o **stream é minoria do blob** — a tabela de únicos + as colunas
  high-card (decimais, ids, free-text) dominam os bytes. Daí o impacto no blob ser pequeno.
- O melhor caso real (adult, muitas categóricas) chega a **7,34%** — metade do gate. O **upper bound
  `sort_by`** (que maximiza runs na chave) não passa de **13,0%** (relationship), e `sort_by` é
  **order-free** (só uma chave se beneficia, reordena tudo).
- **Sob brotli é contraproducente** em 7/7. Confirma o padrão já visto (number-nature; staged-brotli):
  ganho textual modesto que não sobrevive ao compressor a jusante.

## Gate (anti-incidente 2026-05-21)

| pergunta | resposta |
|---|---|
| Real-world testado? | **Sim** — 7 datasets reais (não só sintéticos) |
| N ≥ 5 de fontes diferentes? | **Sim** (7: UCI, TPC-H, BR-id, Receita, IBGE) |
| Bytes absolutos relevantes (≥5% weighted)? | **Não** — 1,19% weighted; melhor caso 7,34% |
| Some sob compressor? | **Sim** — −1,39% sob brotli (inverte) |

→ Falha 2 de 4. **Veredito: `CLOSED-INSUFFICIENT-GAIN`.** Não justifica format change (#TCF.8) +
GATE + complexidade permanente no decoder/lazy.

## Quando reabrir (nicho estreito)

Só se surgir um caso de **transmissão textual-pura** (sem compressor a jusante) de tabelas com
colunas low-card **fortemente clusterizadas/ordenadas** (sinergia com o layout L5/`sort_by` do gadget
lazy, que já cria runs). Mesmo aí, o teto medido (~7-13%) é abaixo do gate. Não priorizar.

## Follow-up — nicho "texto curto / formulário" (refinamento do owner, 2026-06-19)

O owner apontou que o stream-RLE faz mais sentido em **texto** (formulários, frases curtas que
repetem) e em **payload pequeno**, não nas tabelas largas do teste inicial. Medido com a coluna
low-card de texto **isolada** (narrow; a coluna domina o blob) — [`analyze_forms.py`](analyze_forms.py)
· [`result_forms.txt`](result_forms.txt):

| coluna (isolada, ordem natural) | ganho textual (% blob) | sob brotli |
|---|---|---|
| receita/situacao (K=5, skewed) | **+54,9%** | −11,0% |
| adult/workclass (K=9) | **+21,6%** | −6,4% |
| ibge/mesorregiao (K=138) | +5,5% | −2,7% |
| adult/marital-status (K=7) | +5,3% | −4,0% |
| adult/education (K=16, uniforme) | +1,4% | −0,7% |

**Achado técnico-chave**: nos casos **clusterizados/`sort_by`** a coluna **flipa para `modo=tcf`** —
o `*N|` do OBAT/HCC (RLE de linha) captura os runs longos e **vence o fallback**, então o dict nem é
escolhido. Ou seja: **stream-RLE e tcf-`*N|` competem pelo mesmo fenômeno** (repetição adjacente de
valor inteiro), e o tcf já ganha onde os runs são longos. O stream-RLE só tem espaço no regime de
**runs curtos (ordem natural)** — onde o dict vence o fallback e deixa o stream cru. Aí, se a coluna
for **skewed** (um valor dominante → runs moderados mesmo sem ordenar), o ganho é real e **nada mais
o captura** (situacao +55%, workclass +22%).

**Nicho real, mas estreito**: payload pequeno + coluna low-card de texto curto + **skewed** + ordem
natural + **textual-puro** (sem compressor a jusante). Alinha com a diretriz "transmissão minúscula,
cada byte conta". Ressalvas: (1) só ordem natural (clusterizado → tcf-`*N|`); (2) só skewed (uniforme
~1%); (3) **morre sob brotli** (−6% a −11%).

## Veredito refinado

- **Uso geral (tabelas largas / com compressor a jusante): `CLOSED-INSUFFICIENT-GAIN`** —
  1,19% weighted, 0/7 ≥15%, −1,39% sob brotli.
- **Nicho textual-puro (transmissão minúscula, low-card skewed, ordem natural): ABERTO p/ decisão do
  owner** — passa ≥15% em 2 reais *nesse nicho* (situacao 55%, workclass 22%), mas é estreito,
  brotli-frágil, e overlap com tcf-`*N|` na ordem clusterizada. Weld = format change (#TCF.8) + GATE
  + re-pin → só se o owner julgar o nicho prioritário. **Não weldado; src/tcf intocado.**

## Encaminhamento

- **`src/tcf` intocado** (lab-first; nada weldado).
- `V2-RLE-STREAM`: `closed-insufficient-gain` pro geral; **nicho textual-puro registrado, decisão do
  owner pendente** (ROADMAP).
- **RLE na célula (intra-valor) = [H-INTRA-01/02/03](../notas/roadmap-hipoteses.md#pacote-11) → adiado
  a pedido do owner** ("depois revisamos o RLE na célula"). É concern distinto (repetição DENTRO do
  valor, não entre linhas).

## Referências (família RLE + cadeia de formato)

- **Estudo consolidado da família RLE**: [`rle-familia-estudo.md`](../notas/rle-familia-estudo.md)
  (linha-`*N|` welded / stream-V2-B / intra-valor) — entrar por aqui.
- **Registry**: [roadmap-hipoteses.md Pacote 11-bis](../notas/roadmap-hipoteses.md) (H-V2RLE-01/02) +
  [Pacote 11 H-INTRA](../notas/roadmap-hipoteses.md#pacote-11).
- **V2-B (base deste follow-up)**: [ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md).
- **RLE de linha (o que compete com o stream)**: [ADR-0016 seq-RLE](../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md),
  [HCC](../../../../docs/algorithms/HCC.md), [OBAT](../../../../docs/algorithms/OBAT.md).
- **Split estrutural (vizinho)**: [ADR-0026](../../../../docs/adr/0026-structural-split-weld.md).
- ROADMAP: linha `V2-RLE-STREAM` (Tier 1).
