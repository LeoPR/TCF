# Result — split estrutural + V2-B: 19.4% weighted (muito alem de datetime)

**Data**: 2026-06-14 · **Status**: confirmada-empirica · confianca: Alta ·
**Tipo**: [probatorio] · FORK (nao toca src/tcf)

## Origem

O V2-D (refutado) apontou colunas DATETIME como o unico ganho real. Investigando
o porque: o afixo longo do timestamp escapa do OBAT. Hipotese (H-DT-01): um
encoder estrutural ganha mais. **Descoberta: o efeito e' muito maior e mais geral
que datetime.**

## A "matemagica": split estrutural -> campos low-card -> V2-B

Split GENERICO format-agnostic: tokeniza cada valor em runs de DIGITOS vs
NAO-digitos. Se todos compartilham o MESMO template (separadores + contagem de
campos), os grupos de digitos viram colunas-campo, o template e' guardado 1x.

O ganho vem da **sinergia com V2-B**: dividir 1 coluna high-card em N colunas, e
cada campo tende a ser low-card (fracao `.00`-`.99`, mes 1-12, ano quase-constante)
-> o V2-B (welded hoje) esmaga cada campo. Generaliza decimais, datas, datetimes,
CPF, CNPJ, telefone, CEP.

## Resultado (8 datasets reais, ROWS=5000, RT OK em todas)

```
weighted sobre TODAS as colunas: 19.39% (346KB de 1.79MB)
so' as colunas afetadas:         50.4%
```

| coluna | base | fldV2B | gain% | template | tipo |
|---|---:|---:|---:|---|---|
| tpch l_quantity | 19142 | 5264 | **72.5%** | `.` | decimal |
| wine citric_acid | 18120 | 5499 | **69.7%** | `.` | decimal |
| tpch l_discount | 15753 | 5086 | **67.7%** | `.` | decimal |
| br data_cadastro | 46417 | 15342 | **66.9%** | `--` | data |
| receita cnpj | 97054 | 32668 | **66.3%** | `../-` | id |
| tpch l_tax | 14828 | 5077 | 65.8% | `.` | decimal |
| tpch l_shipdate | 35995 | 15276 | 57.6% | `--` | data |
| online InvoiceDate | 4293 | 2136 | 51.3% | `-- ::` | datetime |
| wine (chem, 11 cols) | — | — | 27-49% | `.` | decimal |
| br cpf | 94260 | 58148 | 38.3% | `..-` | id |

`fldV2B` << `fldSC` em quase tudo: a sinergia com V2-B e' o motor (campo isolado
single-col nao tem V2-B; campo no sub-table multi-col tem).

## Checklist confirmada-empirica
1. Real-world? **Sim** — 8 datasets reais. 2. N>=5? **Sim** (8). 3. Sint vs real?
N/A. 4. Vies? N/A. 5. Bytes >= 5% weighted? **Sim** — 19.39% weighted, 346KB.

## Notas / caveats

- **Nao toca o detector** (e' pre-transform + sub-table encode). Colunas free-text
  (Description, l_comment, StockCode) -> split_struct=None -> GATE intocado.
- **Overlap com V2-B**: parte do ganho usa V2-B nos campos; nao e' aditivo ao
  13.9% do V2-B isolado (composicao, nao soma).
- **Overlap com natures CPF/CNPJ** (ADR-0015): o split generico tambem pega
  cpf/cnpj. Avaliar se subsume ou complementa as specs existentes.
- **Header por coluna**: o sub-table de campos carrega mini-header; amortizado em
  N alto, mordia em tabela pequena -> gating min(base, split) = zero-regressao.
- **fldSC as vezes REGRIDE** (ex: l_extendedprice, wine alcohol): o ganho REAL
  depende do V2-B nos campos; sem ele, split sozinho pode perder. Welder split
  SEMPRE acoplado a escolha per-campo (min) + fallback per-coluna.

## Proposta (para aprovacao do owner)

Welder como **transform estrutural opt-in** (linha das natures, ADR-0015), OU
auto-detect gated. Per-coluna: split -> sub-table de campos (cada campo passa pelo
fallback tcf/raw/dict) -> escolhe min(coluna inteira, split). Marcador novo no
header #TCF.7. Decisao de escopo (opt-in vs auto) + desenho do formato pendentes.

## Artefatos
- `analyze.py` — base vs fields(single-col) vs fields(multi-col+V2-B), RT-checked
