# Result — V2-D strip de afixo comum: subsumido pelo OBAT

**Data**: 2026-06-14 · **Status**: refutada-real-world (decisao: **nao welder**) ·
confianca: Alta · **Tipo**: [probatorio] · FORK (nao toca src/tcf)

## Hipotese (ADR-0018 §V2-D)

Coluna onde TODOS os valores compartilham prefixo/sufixo (`.0`, zero-pad, `BR-`):
stripa o afixo, guarda 1x no header, restaura no decode. Lossless, barato.

## Pergunta critica respondida

O **OBAT ja' e' bidirecional** (LCP + LCS): o afixo comum ja' vira UM fragmento
compartilhado. V2-D so' valeria se stripar (afixo no header, ZERO ref/linha)
batesse o que o OBAT ja' faz. **Nao bate.**

## Resultado (8 datasets reais, ROWS=5000, RT OK)

```
weighted sobre TODAS as colunas: 0.11% (gain 1994 / base_all 1.81MB)
so' as colunas afetadas:         0.80%
```

| coluna | base | gain | % | afixo | nota |
|---|---:|---:|---:|---|---|
| online-retail.InvoiceDate | 4293 | 642 | **15.0%** | `2010-12`/`:00` | datetime |
| br-pessoas.data_cadastro | 46417 | 1638 | **3.5%** | `20` | datetime |
| wine.chlorides | 21583 | 242 | 1.1% | `0.` | |
| tpch l_quantity | 19142 | 98 | 0.5% | `.00` | |
| tpch l_shipdate | 35995 | **-286** | -0.8% | `199` | **REGRIDE** |
| tpch l_commitdate | 35462 | **-185** | -0.5% | `199` | **REGRIDE** |
| tpch l_receiptdate | 35948 | **-155** | -0.4% | `199` | **REGRIDE** |
| adult.sex / class | — | -1..-2 | ~0% | `ale`/`50K` | REGRIDE |

## Leitura

1. **Subsumido pelo OBAT**: o ganho weighted (0.11%) e' ruido. O afixo comum ja'
   e' 1 fragmento compartilhado no pipeline atual.
2. **Strip REGRIDE em varias**: stripar um PREFIXO desancora a tokenizacao do
   OBAT e piora os tokens seguintes (datas l_shipdate/commit/receipt: -155 a
   -286). Generico-strip e' ATIVO-negativo sem gating per-coluna.
3. **Mesmo com gating perfeito** (min(base, v2d) por coluna -> zero regressao), a
   soma dos ganhos POSITIVOS e' ~0.15% weighted. Negligivel.
4. **O sinal real e' DATETIME**, nao strip-generico: os unicos ganhos relevantes
   (InvoiceDate 15%, data_cadastro 3.5%) sao colunas de timestamp onde o afixo e'
   longo (`2010-12...:00`). Aponta pra um **nature de datetime** (encoder
   especializado: epoch/delta + formato), nao pra strip de afixo.

## Decisao: NAO welder V2-D

Subsumido pelo OBAT (0.11% weighted), com regressao sem gating e ~0.15% mesmo
gated. ROI insuficiente. **Marcar ADR-0018 §V2-D como refutada-real-world.**

**Redirecionamento**: registrar **datetime-nature** como hipotese futura (o ganho
real concentrado nas 2 colunas datetime sugere que timestamps merecem um encoder
proprio, na linha das natures CPF/CNPJ/IP — ADR-0015). Nao e' V2-D.

## Artefatos
- `analyze.py` — base vs strip(afixo) em 8 datasets, RT-checked
