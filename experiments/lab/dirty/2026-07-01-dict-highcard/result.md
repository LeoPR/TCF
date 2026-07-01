# DICT-HIGHCARD — caracterização [probatório]

**Data**: 2026-07-01. Mede **dict-per-col SEM cap vs OBAT/HCC** por coluna (24 colunas: hubs
canônicos + 5 same-domain + contrastes), buscando onde o cap `_V2B_MAX_CARD=1024` do V2-B deixa
ganho na mesa. `gain<0` = dict vence. Controle = gzip. READ-ONLY. Sweep: [characterize.py](characterize.py),
full em [artifacts/sweep-full.txt](artifacts/sweep-full.txt).

## Resultado (recorte; gain<0 = dict vence OBAT/HCC)
```
coluna                     K      N/K    gain%     nota
-- dict VENCE (high-card SEM estrutura explorável) --
tpch l_partkey           1995     6.0   -46.3%    ids espalhados
receita cnae_principal    692    17.3   -45.2%
receita municipio_cod    2072     5.8   -40.0%
br razao_social          1400     8.6   -40.5%
tpch l_shipdate          2481     4.8   -42.1%    (data fora de ordem)
br municipio_id          4908     2.4   -29.1%
football home_team        202    59.4   -48.1%
-- OBAT/HCC VENCE (high-card COM estrutura: sequência/grupo/prefixo) --
tpch l_orderkey          3012     4.0   +15.2%    seq-RLE pega
snap from_node           1676     7.2   +74.7%    edge-list agrupada -> RLE
tpch ps_partkey          2000     4.0  +28555%    partsupp ORDENADO -> seq-RLE domina
email from_node           141    85.1   +2247%    (idem)
tpch l_comment          11917     1.0    +9.8%    quase-único (K≈N)
adult fnlwgt             9935     1.2   +26.1%    quase-único
```

## Achados

### 1. NÃO é robusto — é DATA-DEPENDENTE (não N/K)
Na "zona da hipótese" (K>1024 & N/K≥3): dict vence **6/11** — moeda ao ar, não robusto. **O −16..−36%
do B2 prototype era PARCIAL**: era o PAR (from+to), e o ganho vinha da coluna **espalhada** (`to_node`),
enquanto `from_node` (agrupada) na verdade favorece OBAT/HCC (+74.7% sozinha). O sinal se inverte por
coluna — a média conflacionava.

### 2. O eixo real é ESTRUTURA-EXPLORÁVEL, não repetição
- **Dict vence**: high-card categórico **sem estrutura** que o OBAT/HCC saiba usar — ids espalhados
  (l_partkey, municipio_cod), texto (razao_social), datas fora de ordem. −29 a −48%.
- **OBAT/HCC vence**: high-card **com estrutura** — sequencial (l_orderkey), ordenado/agrupado
  (ps_partkey, from_node de edge-list → seq-RLE/RLE demolem), quase-único (l_comment, fnlwgt).
- N/K (repetição) **não prediz** — ps_partkey e l_partkey têm N/K≈4-6 e resultados OPOSTOS.

### 3. O conserto SEGURO: descapar → candidato do min() (byte-safe)
O encoder **já faz `min(tcf, raw, v2b, split)` por coluna** ([core.py:178-191](../../../../src/tcf/multi/core.py)).
O cap (`_v2b_encode` retorna None p/ K>1024) é a ÚNICA coisa que exclui o dict como candidato high-card.
**Remover/elevar o cap → o dict entra no min() → ganho ESTRITO (min nunca regride)**: captura os
−40..−48% das colunas espalhadas, ZERO regressão nas estruturadas (min pega tcf). N/K **não é o gate**
— o `min()` decide por coluna, automático. O custo é **COMPUTE** (o sub-encode do dict em toda coluna
high-card — a razão do cap existir). Trade compute↔compressão, mitigável por heurística barata de skip
(ex.: pular o dict-encode se cadência/run-ratio alto já indica que o OBAT/HCC vence).

### 4. Alinha com a literatura (bibliografia)
**Abadi 2006**: o melhor esquema **depende dos dados** — testar vários, escolher por coluna. **Zukowski
2006 (PDICT/PFOR)**: esquemas leves com fallback. O TCF já faz o `min()`; o cap só exclui um candidato
prematuramente.

### 5. Impacto na reorganização (o alicerce é CONDICIONAL)
"1ª coluna como dict" / HCC ref-share (a [reorganização](../../notas/arquitetura-share-header-lazy.md))
assumia o dict per-col como base robusta. **Ele é condicional** (um candidato entre tcf/raw/split/dict).
Então o cross-dict/share tem de **bater um per-col que já é min-ótimo** — barra mais alta do que
pensávamos. A "1ª coluna como dict" só ajuda quando ela É dict-vencedora (espalhada).

## Veredito
DICT-HIGHCARD **reduz a "descapar o V2-B"** — otimização **pequena mas SEGURA** (byte-safe via min;
captura −40..−48% em colunas espalhadas high-card reais). **Corrige a over-claim do B2 prototype**
(não é −16..−36% robusto; é condicional). A caracterização de novo separou o afortunado do real.

**Próximo (weld, sob aprovação)**: medir o **custo de compute** de descapar + heurística de skip;
gate byte-canônico (D1-D9/D17a inalterados — são low-card; real-world snapshots podem MELHORAR →
re-pin, não regressão). Não bloqueia nada; é um ganho safe incremental.
