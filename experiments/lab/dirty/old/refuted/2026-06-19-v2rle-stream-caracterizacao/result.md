# V2-RLE-STREAM — caracterização [resultado]

**Data**: 2026-06-19 · resultado (lab dirty, **read-only, NÃO tocou `src/tcf`**).
**Hipótese**: aplicar RLE no **stream de índices do V2-B** (`@dict`) reduz bytes onde há runs
adjacentes do mesmo índice (coluna clusterizada/ordenada). Script: [`analyze.py`](analyze.py) ·
medições brutas: [`result.txt`](result.txt).
**Status**: `CLOSED-INSUFFICIENT-GAIN`.

> **Escopo e correções (2026-06-19, pós-revisão do owner)** — leia antes:
> - Este lab testou o **V2-RLE-STREAM = RLE no stream de índices do V2-B**: uma micro-otimização
>   ESTREITA. **NÃO é** a ideia mais ampla de **dicionário global/cross-column no cabeçalho** — essa é
>   outra coisa, registrada em [H-GDICT-01](../../../notas/roadmap-hipoteses.md) (não testada aqui).
> - **Correção factual**: versão anterior dizia que single-col "não tem dict". **Errado.** O TCF cria
>   um **dicionário implícito** via `^N` (índice do N-ésimo valor distinto). Os exemplos abaixo são a
>   **saída real do encoder**, não esquema.

## Exemplo visual — dict implícito (`^N`), `*N|` e o stream (saída real, 16 itens)

Coluna `situacao`, 16 linhas, 3 valores distintos (ATIVA, BAIXADA, SUSPENSA), ordem natural.

### Caminho 1 — UMA coluna (`encode(list)`): dict IMPLÍCITO via `^N`, sem stream

Single-col não tem header nem a tabela explícita do V2-B — **mas tem dicionário**: a 1ª ocorrência
define o atom, as repetições viram `^N` (índice do N-ésimo distinto). Saída real do encoder:
```
ATIVA       <- atom 1 (definido aqui)
BAIXADA     <- atom 2
*2|^1       <- run de 2 + ref ao atom 1 (ATIVA)
SUSPENSA    <- atom 3
^1          <- ATIVA
^2          <- BAIXADA
*3|^1       <- 3x ATIVA
^2
^1
^3          <- SUSPENSA
*3|^1
```
`^1`=ATIVA, `^2`=BAIXADA, `^3`=SUSPENSA — **sempre**, independente da posição. **Isto É um dicionário**
(índice → valor); os `^N` são os índices. **Você estava certo**: a compressão já te dá um dict natural.

Ordenada (`sort_by`), vira `*11|ATIVA` / `*3|BAIXADA` / `*2|SUSPENSA` (o `*N|` esmaga). De qualquer
forma, **single-col não tem stream** → V2-RLE-STREAM não se aplica aqui.

### Caminho 2 — MULTI-coluna: o V2-B pode tornar o dict EXPLÍCITO (tabela + stream)

No multi-col o fallback compara, por coluna: `tcf` vs `raw` vs `@dict` vs `%split`. O `@dict` (V2-B)
põe a tabela de únicos no topo e **packa** os índices num **stream** (1 char/linha, vs `^N\n` que são
~3). É a versão explícita+packed do mesmo dict implícito do Caminho 1.

**(2a) ORDENADA** → o fallback escolhe **tcf** (`*N|` ganha; repare: meta SEM `@`):
```
#TCF.7 M
situacao
*11|ATIVA
*3|BAIXADA
*2|SUSPENSA
```
→ não virou `@dict` → **não há stream** → V2-RLE-STREAM não tem o que fazer.

**(2b) NATURAL** → o fallback escolhe **@dict** (runs curtos; `*N|` não ajuda; o stream 1-char/linha
vence o `^N\n`):
```
#TCF.7 M
@situacao
23
ATIVA
BAIXADA
SUSPENSA           <- a tabela = o dict explícito
!"!!#!"!!!"!#!!!    <- o stream de índices (!=ATIVA "=BAIXADA #=SUSPENSA)
```
Aqui o stream existe cru — **é exatamente onde o V2-RLE-STREAM agiria**. Mas o maior run é 3, e RLE
de um run custa `marcador+contagem+token` = 3 chars → **só compensa com run ≥ 4** → **economiza ZERO**.

### O achado exato — o stream-RLE é espremido dos DOIS lados

```
runs LONGOS  ->  tcf-*N| VENCE o fallback  ->  @dict nem entra  ->  NAO HA stream
runs CURTOS  ->  @dict vence               ->  stream existe MAS run < 4  ->  RLE ~ 0
```

Verificado em 16 itens: o caso clusterizado (runs 4/6/4) **flipa pro tcf** (`*4|ATIVA ... *6|^1`); o
natural disperso fica em `@dict` mas com runs ≤3. O stream-RLE só "sobra" no meio: coluna que **fica
em @dict** com runs médios (≥4). Isso, na prática, **só aparece em escala real + valor dominante
disperso**: a `situacao` da Receita (15k linhas) ficou em `@dict` e o stream RLE-ou **+54,9%** textual
(ver [result_forms.txt](result_forms.txt)). Em 16 itens limpos não aparece. E mesmo no caso real
**morre sob brotli** (−11%) e **dilui** na tabela larga (weighted real **+1,19%**).

### O que o owner realmente queria (≠ deste lab): dicionário GLOBAL

Repare o que acontece com **2 colunas que compartilham valores** (saída real):
```
#TCF.7 M
@15=resp1,@resp2
8
SIM
NAO
!"!!"          <- resp1: tabela [SIM,NAO] + stream
8
NAO
SIM
!!"!"          <- resp2: guarda a tabela [SIM,NAO] DE NOVO  (redundância cross-column!)
```
Cada coluna guarda **sua própria** tabela. A ideia de **dicionário global no cabeçalho** elimina isso:
**uma** tabela `{SIM, NAO}` no header, ambas as colunas só carregam o stream de índices. É a ideia
[H-GDICT-01](../../../notas/roadmap-hipoteses.md) (= "cross-column dict", O-FMT-06/07) — **distinta** do
RLE-no-stream deste lab, e não caracterizada.

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

Nesse nicho (payload pequeno + low-card texto **skewed** + ordem natural + **textual-puro**) o ganho é
real (situacao +55%, workclass +22%) e **nada mais o captura** — mas é estreito e **morre sob brotli**.

## Veredito refinado

- **Uso geral (tabelas largas / com compressor a jusante): `CLOSED-INSUFFICIENT-GAIN`** —
  1,19% weighted, 0/7 ≥15%, −1,39% sob brotli.
- **Nicho textual-puro (transmissão minúscula, low-card skewed, ordem natural): ABERTO p/ decisão do
  owner** — passa ≥15% em 2 reais *nesse nicho* (situacao 55%, workclass 22%), mas é estreito,
  brotli-frágil, e overlap com tcf-`*N|` na ordem clusterizada. Weld = format change (#TCF.8) + GATE
  + re-pin → só se o owner julgar o nicho prioritário. **Não weldado; src/tcf intocado.**
- **A ideia mais ampla do owner — dicionário GLOBAL/cross-column no header — é [H-GDICT-01](../../../notas/roadmap-hipoteses.md)**,
  hipótese distinta (não testada aqui).

## Encaminhamento

- **`src/tcf` intocado** (lab-first; nada weldado).
- `V2-RLE-STREAM`: `closed-insufficient-gain` pro geral; **nicho textual-puro registrado, decisão do
  owner pendente** (ROADMAP).
- **Dicionário global/cross-column = [H-GDICT-01](../../../notas/roadmap-hipoteses.md)** — a ideia que o owner
  de fato queria; concern distinto deste lab.
- **RLE na célula (intra-valor) = [H-INTRA-01/02/03](../../../notas/roadmap-hipoteses.md#pacote-11) → adiado
  a pedido do owner** ("depois revisamos o RLE na célula"). Repetição DENTRO do valor, não entre linhas.

## Referências (família RLE + família DICT + cadeia de formato)

- **Estudo consolidado**: [`rle-familia-estudo.md`](../../../notas/rle-familia-estudo.md) — entrar por aqui.
- **Registry**: [roadmap-hipoteses.md](../../../notas/roadmap-hipoteses.md) — Pacote 11-bis (V2-RLE = H-V2RLE),
  H-GDICT-01 (dict global), [Pacote 11 H-INTRA](../../../notas/roadmap-hipoteses.md#pacote-11) (intra-valor).
- **V2-B (base)**: [ADR-0025](../../../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md).
- **RLE de linha / dict implícito `^N`**: [ADR-0016 seq-RLE](../../../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md),
  [HCC](../../../../../../docs/algorithms/HCC.md), [OBAT](../../../../../../docs/algorithms/OBAT.md).
- **Split estrutural (vizinho)**: [ADR-0026](../../../../../../docs/adr/0026-structural-split-weld.md).
- ROADMAP: linha `V2-RLE-STREAM` (Tier 1).
