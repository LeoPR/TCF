# V2-RLE-STREAM — caracterização [resultado]

**Data**: 2026-06-19 · resultado (lab dirty, **read-only, NÃO tocou `src/tcf`**).
**Hipótese**: aplicar RLE no **stream de índices do V2-B** (`@dict`) reduz bytes onde há runs
adjacentes do mesmo índice (coluna clusterizada/ordenada). Script: [`analyze.py`](analyze.py) ·
medições brutas: [`result.txt`](result.txt).
**Status**: `CLOSED-INSUFFICIENT-GAIN`.

## Exemplo visual — `*N|` × stream, nos mesmos 16 itens (didático e expandido)

Duas confusões que o texto solto não resolvia:
**(i)** "isto não é o mesmo que o `*N|`?" e **(ii)** "e se for uma coluna só?".

Chave: **`*N|` e o stream são DOIS MODOS da mesma coluna, mutuamente exclusivos** — o fallback
`min(tcf, raw, @dict, %split)` escolhe UM por coluna. O `*N|` vive no modo **tcf** e atua sobre os
**valores** (linhas idênticas adjacentes). O **stream** só existe no modo **@dict**, e atua sobre
**índices** (o valor já virou um número). E **coluna única não tem dict** → nunca tem stream.

Os 16 itens da coluna `situacao` (3 valores), em **ordem natural** (lê-se descendo cada coluna):

```
#  valor       #  valor       #  valor       #  valor
1  ATIVA       5  SUSPENSA    9  ATIVA       13 SUSPENSA
2  BAIXADA     6  ATIVA       10 ATIVA       14 ATIVA
3  ATIVA       7  BAIXADA     11 BAIXADA     15 ATIVA
4  ATIVA       8  ATIVA       12 ATIVA       16 ATIVA
```
(ATIVA ×11, BAIXADA ×3, SUSPENSA ×2)

---

### Caminho 1 — UMA coluna só (`encode(["ATIVA","BAIXADA",...])`)

Single-col **não tem header, não tem dict, não tem stream**. Só OBAT/HCC, e o `*N|` junta
**linhas idênticas adjacentes** (repetições NÃO-adjacentes viram `^N`, um back-ref curto — omitido
aqui pra focar no `*N|`).

**(1a) ordem natural** — o `*N|` só pega o que está colado:
```
ATIVA          (1)
BAIXADA        (2)
*2|ATIVA       (3-4)    <- run adjacente
SUSPENSA       (5)
ATIVA          (6)
BAIXADA        (7)
*3|ATIVA       (8-10)   <- run adjacente
BAIXADA        (11)
ATIVA          (12)
SUSPENSA       (13)
*3|ATIVA       (14-16)  <- run adjacente
```

**(1b) ordenada** (`sort_by`) — tudo igual fica colado, o `*N|` esmaga a coluna inteira:
```
*11|ATIVA
*3|BAIXADA
*2|SUSPENSA
```

→ **O ponto que você levantou**: numa coluna só, **ordenar já dá o "RLE" de graça** via `*N|`.
O V2-RLE-STREAM **não existe** neste caminho (não há dict/stream pra RLE-ar).

---

### Caminho 2 — MULTI-coluna (a `situacao` é 1 de várias)

Agora o fallback compara, por coluna: `tcf (*N|/^N)` vs `raw` vs `@dict` vs `%split`. O `@dict`
troca cada valor por um índice e guarda os índices num **stream** (1 char/linha; `!`=ATIVA,
`"`=BAIXADA, `#`=SUSPENSA).

**(2a) ORDENADA** — o `*N|` do tcf vence; o dict nem entra:
```
modo tcf:    *11|ATIVA  *3|BAIXADA  *2|SUSPENSA              (~30 B, a coluna toda)
modo @dict:  tabela[ATIVA,BAIXADA,SUSPENSA] + stream(16 chars)   (~40 B)
=> min() escolhe tcf  ->  NAO HA STREAM  ->  V2-RLE-STREAM nao tem o que fazer.
```

**(2b) NATURAL** — aqui o `@dict` vence o tcf (cada valor = 1 char no stream, vs o overhead de
marcador por linha do tcf), então o stream EXISTE e fica cru:
```
stream cru (16):  ! " ! ! # ! " ! ! ! " ! # ! ! !
                      └2┘       └──3──┘     └──3──┘     (maior run = 3)
```
E **é aqui que o V2-RLE-STREAM agiria**. Mas RLE-ar um run de `m` custa
`marcador + contagem + token` = **3 chars** (width 1), então **só compensa com run ≥ 4** (run de 3
empata, run de 2 perde). O **maior run aqui é 3** → **o RLE economiza ZERO**.

> Em ordem natural os runs são curtos **por construção**: se fossem longos, o caso (2a) já teria
> mandado a coluna pro tcf-`*N|`. Por isso o stream-RLE é, na prática, um **resíduo** do `*N|`.

---

### Quando o stream-RLE finalmente ganha: coluna SKEWED

Se **um valor domina** (ex: 14 ATIVA, 1 BAIXADA, 1 SUSPENSA), os runs de ATIVA ficam longos
**mesmo sem ordenar** — e o dict ainda vence (não há um ÚNICO run gigante que o tcf colapsaria; os
ATIVA estão quebrados pelos outros dois valores):
```
stream cru (16):  ! ! ! !  "  ! ! ! ! ! !  #  ! ! ! !
                  └─ 4 ─┘     └──── 6 ────┘     └─ 4 ─┘
stream RLE:       §4!  "  §6!  #  §4!               (16 -> 11 chars, -31%)
```
→ **Este é o nicho** (a `situacao` real chegou a **+55%** no [lab forms](result_forms.txt)).
`§` = marcador reservado (na implementação, um byte fora do alfabeto, ex `0x01`).

---

### Por que, mesmo com o nicho, não vale weldar

1. **Ordenado** → tcf-`*N|` vence (nos dois caminhos) → o stream nem existe.
2. **Natural não-skewed** → runs curtos (≤3) → RLE ≈ 0.
3. **Natural skewed** → ganha no textual-puro, **mas**: (a) **morre sob brotli** (o brotli já
   comprime o stream repetido; o marcador vira overhead — −6% a −11% medido); (b) **dilui** numa
   tabela larga (o stream é fração do blob → **+1,19% weighted real**, não os 31% do stream isolado).

> **Em uma frase**: `*N|` (sobre valores) e stream-RLE (sobre índices) atacam a MESMA repetição
> adjacente; o `*N|` já vence quando ela é longa, o brotli já a pega quando há compressor a jusante,
> e o que sobra pro stream-RLE são os runs curtos da ordem natural — pequenos demais, salvo coluna
> **skewed** em **transmissão textual-pura**.

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
