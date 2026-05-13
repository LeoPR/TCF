# Observações dos datasets reais

Notas de espreita em `datasets/samples/adult-census/adult-sample.csv`
e `datasets/samples/tpch-sf001/*.csv`. Servem para ancorar a geração
sintética em padrões que aparecem no real, sem copiar valores.

## Adult Census (UCI, survey real)

15 colunas, mistura de inteiros e enums. Padrões observados:

- **Idade** (inteiro 18–65): cardinalidade ~50 num dataset de
  ~32k linhas. Distribuição concentrada em 25–55.
- **Workclass** (enum baixa cardinalidade): 8 valores distintos,
  fortemente dominado por `Private`. **Tem vazios** (linhas com
  `,,` no CSV) — survey real, falha de cadastro frequente.
- **fnlwgt** (inteiro grande, sem padrão): valores como 226802,
  89814, 336951. Cardinalidade alta, sem repetição estrutural,
  sem padrão de prefixo. É o "lixo bem distribuído" do dataset.
- **Education** (enum média cardinalidade): 16 valores. Hifenizado:
  `HS-grad`, `Some-college`, `Assoc-acdm`, `7th-8th`, `Prof-school`.
  Padrão: separador `-` é estrutural.
- **education-num** (inteiro 1–16): correlacionado com Education.
  Pareado.
- **Marital-status, Occupation, Relationship, Race**: enums
  hifenizados. Occupation tem vazios também.
- **Sex** (cardinalidade 2): `Male`/`Female`. Caso canônico de dict
  cardinalidade 2.
- **capital-gain, capital-loss** (inteiros com muitos zeros):
  distribuição extremamente bimodal — maioria zero, alguns valores
  grandes. RLE em zeros aproveita.
- **hours-per-week** (inteiro 1–99): concentrado em 40 (regra
  trabalhista).
- **native-country** (enum alta cardinalidade): ~40 países, mas
  >90% `United-States`. Distribuição Pareto extrema.
- **class** (cardinalidade 2): `<=50K`/`>50K`. Padrão com caracteres
  especiais (`<=`, `>`).

**Padrões a importar para o sintético**:
- enum hifenizado é comum (não usar só CamelCase ou underscore).
- vazios em colunas categóricas survey é normal.
- Pareto em país (1 valor domina) é realista.
- bimodal extremo em capital-gain/loss (>90% zeros) ocorre.

## TPC-H sf001 (synthetic relacional, padrão indústria)

7 tabelas, schema relacional clássico (customer, orders, lineitem,
supplier, nation, region, part). Padrões observados:

- **IDs sequenciais**: `c_custkey`, `o_orderkey`, `l_orderkey` são
  inteiros monotônicos. Cardinalidade ≈ N.
- **Nome com prefixo + zero-padding**: `Customer#000000001`,
  `Supplier#000000001`, `Clerk#000000951`. Estrutura
  `<entity>#<NNNNNNNNN>`. Prefixo fixo + numérico zero-padded.
  **Caso canônico de prefix-DICT**.
- **Endereço alta entropia**: `j5JsirBM9PsCy0O1m`,
  `487LW1dovn6Q4dMVymKwwLE9OKf3QG`. Strings base64-like,
  sem padrão, sem repetição. **Caso canônico de "não comprime"**.
- **Telefone formato fixo**: `25-989-741-2988`. Padrão
  `NN-NNN-NNN-NNNN`. Não é formato BR; é convenção TPC-H.
- **Decimal monetário**: `c_acctbal=711.56`, `o_totalprice=172799.49`.
  2 casas decimais. Range varia conforme campo (acctbal pode ser
  negativo: `-283.84`).
- **Enum baixa cardinalidade**: `c_mktsegment` (5 valores:
  `BUILDING`, `AUTOMOBILE`, `MACHINERY`, `HOUSEHOLD`, `FURNITURE`).
- **Enum com prefixo numérico**: `o_orderpriority` =
  `5-LOW`, `1-URGENT`, `4-NOT SPECIFIED`, `2-HIGH`, `3-MEDIUM`.
  Padrão `<dígito>-<NOME>`. Hibridismo enum + prefixo.
- **Datas ISO**: `1996-01-02`, `1992-02-21`. Range 1992–1998.
  Cardinalidade alta mas com clusters por ano.
- **Comentário texto livre**: `"ly express platelets. deposits acc"`.
  Procedural, parece truncado (sem ponto final), pontuação
  variada. Cardinalidade ≈ N.
- **Single-char flags**: `l_returnflag` (`N`/`R`/`A`),
  `l_linestatus` (`O`/`F`). Cardinalidade 2–3, valor de 1 byte.
- **Modos de envio**: `l_shipmode` enum (`TRUCK`, `MAIL`, `AIR`,
  `FOB`, `RAIL`, `REG AIR`, `SHIP`). Note `REG AIR` com espaço.
- **Instrução de envio**: `l_shipinstruct` enum (`DELIVER IN PERSON`,
  `TAKE BACK RETURN`, `NONE`, etc.). Espaços e maiúsculas.
- **Decimais pequenos quantizados**: `l_discount` (0.00 a 0.10 step
  0.01), `l_tax` (0.00 a 0.08). Cardinalidade ~10.

**Padrões a importar para o sintético**:
- prefixo + zero-padding em IDs (`Customer#000000001`) é canônico.
- coluna alta entropia (endereços lixo) deve estar no catálogo
  como contraste — não comprime, não deve fingir que comprime.
- enum com prefixo numérico (`5-LOW`) é frequente em sistemas reais.
- decimais pequenos quantizados (discount, tax) são caso de RLE
  numérico.
- single-char flags são canônicos de dict cardinalidade 2–3.

## Síntese — o que orienta a geração sintética

| Fenômeno real | Implicação no catálogo |
|---|---|
| Vazios em enum survey | Incluir variante "com falhas" em todo enum |
| Pareto extremo em país | Distribuição não-uniforme deve estar disponível |
| Hifenização em enums | Separadores estruturais variados |
| Prefixo+padding em IDs | Caso canônico próprio |
| Alta entropia incompressível | Contra-exemplo explícito (não tudo comprime) |
| Enum com prefixo numérico | Hibridismo é realista |
| Decimal quantizado | Tratar como subcategoria numérica |
| Bimodal com >90% zero | Realista em campos contábeis |

Estes são os pontos onde "sintético deve se comportar como real" para
não enviesar testes de algoritmo.
