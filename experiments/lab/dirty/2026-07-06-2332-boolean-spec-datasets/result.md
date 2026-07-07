# Resultado — boolean nos datasets + spec binária/enum [probatório]

Números: `artifacts/` (`python run.py`). Pedido do owner: estudar boolean nos NOSSOS dados.

## Catálogo — colunas domínio ≤3 (`01-catalogo-dominio2.txt`)

| fonte | coluna | N | #dist | kind | valores |
|---|---|---|---|---|---|
| adult.sex | | 48842 | 2 | enum-2 | Female\|Male |
| adult.class | | 48842 | 2 | enum-2 | <=50K\|>50K |
| receita.matriz_filial | | 200000 | 2 | enum-2 | **1\|2** (não 0/1!) |
| tpch.l_linestatus | | 60175 | 2 | enum-2 | F\|O |
| tpch.l_returnflag | | 60175 | 3 | dom-3 | A\|N\|R |
| tpch.o_orderstatus | | 15000 | 3 | dom-3 | F\|O\|P |
| D17a.categoria | | 13 | 3 | dom-3 | A\|B\|C |
| tpch.o_shippriority | | 15000 | 1 | (constante) | 0 |

## Achado principal (do dado real)

**ZERO `true`/`false`** nos nossos datasets. O único match "bool" (`o_shippriority`) é **constante** (edge do
classificador). O que existe é **enum-2/3 com superfície = DADO**. Consequências:

- **O primitivo útil não é "boolean" — é ENUM/domínio-k** (fechado, pequeno). Boolean (`true/false/1/0/t/f`)
  é a **variante semântica**, rara em tabela real.
- **`matriz_filial = 1|2`** (matriz vs filial), **não** 0/1 → assumir binário-0/1 corromperia a semântica.
  Confirma o owner: no **CSV cru** trata-se como enum (preserva superfície, sanidade); só canonicaliza se
  **typed/declarado**.

## Bytes — raw vs textual vs binário (`03-bytes-coluna-real.txt`, adult.sex N=48842)

| representação | bytes | vs raw |
|---|---|---|
| raw (Male/Female via HCC) | 97291B | 1× |
| spec **textual** (bitstring 0/1) | 48844B | **~2×** (encurta a superfície) |
| spec **binário** (bitmap N/8 + hdr) | 6122B | **~16×** (1 bit/valor) |

**Correção de intuição**: o ganho textual **não** é marginal — é **proporcional ao encurtamento da
superfície** (Male/Female→0/1 = 2×; para `true`/`false` já curto seria ~marginal). O ganho grande e
**constante** (1 bit/valor) é **binário** (bitmap, V2-L/ADR-0018). Em texto a spec ainda vale por **aceleração**.

## Design da spec (do dado)

- **ENUM/domínio-k**: k símbolos = log₂(k) bits; boolean = k=2 semântico.
- **Variante** (superfície): registry de variantes padrão (`1/0`, `t/f`, `true/false`, `True/False`, `Y/N`…).
- **Gabarito-da-spec**: variante padrão → header `@bool:<variante>` (2 valores vêm do registry, coluna não
  guarda). enum arbitrário → `@enum:v0|v1|…` (gabarito na coluna, uma vez). RT-OK (`02`).

## Eixos ORTOGONAIS de uma spec (o pedido do owner — além de compressão/aceleração)

| eixo | o que é | exemplo |
|---|---|---|
| 1 compressão | body encolhe | bool→bitmap |
| 2 aceleração | decode sem deduzir + acesso tipado | int parse rápido |
| 3 **autoridade** | mandatório / spec-natural / deduzido | typed vs CSV cru |
| 4 **normalizabilidade** | superfície livre p/ canonicalizar vs byte-locked | True→true se typed |
| 5 **fechamento de domínio** | fechado (enum/bitmap) vs aberto | enum-2 vs int |
| 6 **variante** | superfície do mesmo semântico | 1/0 · t/f · Y/N |
| 7 **reversibilidade** | round-trip (gate de indução) | "01310"→string |
| 8 **validação/sanidade** | nature alerta anomalia (só detecta) | CPF dígito errado |

## Classificação por autoridade (ataque um-a-um — owner)

- **mandatório**: declarado na entrada → **canonicaliza** (superfície livre).
- **spec-natural**: padrão conhecido (bool, datetime, CPF) → **gabarito-da-spec** (template implícito).
- **deduzido**: induzido do dado via round-trip → **preserva superfície** (sanidade).

## Limites

- Amostra de hubs (COUNT DISTINCT por coluna); `br-identidades` pode ter mais (não exaustivo).
- Enum-k>3 não varrido (só ≤3); bitmap não implementado (é V2-L). Aceleração não medida (só compressão).
