# Result — caracterização da nature de NÚMERO (filtro básico) [probatório]

**Data**: 2026-06-16 · FORK (não toca src/tcf) · datasets reais (Z:), 5000 linhas. `analyze.py`.
**Disciplina**: caracterizar antes de weldar (≥15% weighted em 2+ reais; anti-incidente 2026-05-21).

## Como trabalhamos (e uma falha pega no caminho)
1ª medição comparou a nature com o **TCF single-col** — que **infla** colunas de dígitos
(escape `\` por run, igual ao CPF) → superestimou o ganho (~2×). **Falha**: o 0.7 real escolhe
`min(tcf, raw, dict, split)` por coluna; uma coluna low-card vira **dict**, não o tcf inflado.
**Refeito justo**: `encode({c: crus})` (0.7-fallback) vs `encode({c: packed})` (nature = pré-tx
base-94, depois o 0.7 faz o resto). É como uma nature real funciona.

Candidato: `pack_int` — inteiro não-negativo **canônico** (`str(int(v))==v`) → base-94
(largura variável, `\n`-delimitado), reversível (`base94→int`); demais → literal `_`+v (fallback).

## Resultado (0.7-fallback vs 0.7+nature, 5000 linhas)

| coluna | card% | 0.7 | 0.7+nat | nat/0.7 | +brotli |
|---|---:|---:|---:|---:|---:|
| adult.fnlwgt | 92% | 34109 | 20059 | **58.8%** | 93.6% |
| tpch.l_partkey | 37% | 22300 | 14825 | **66.5%** | 91.0% |
| tpch.l_orderkey | 25% | 9717 | 7201 | **74.1%** | 87.5% |
| adult.capital-loss | 1% | 2431 | 2282 | 93.9% | 97.3% |
| adult.age | 1% | 5361 | 5172 | 96.5% | 98.4% |
| adult.hours-per-week | 2% | 5406 | 5217 | 96.5% | 97.7% |
| tpch.l_suppkey | 2% | 10495 | 10268 | 97.8% | 98.9% |
| adult.education-num / l_linenumber / beijing.Ir/PRES | <1% | — | — | ~100% | ~neutro |
| tpch.l_quantity / beijing.Iws (DECIMAIS) | — | — | — | 100-109% | **infla** |

Ganhou (cru) em 9/14 colunas; **forte só em 3** (alta-card integer).

## Leitura / veredito
1. **Nicho = INTEGER de alta-cardinalidade** (fnlwgt −41%, l_partkey −33%, l_orderkey −26%):
   onde o 0.7 guarda o dígito inteiro, o pack base-94 quase corta pela metade.
2. **Low-card é marginal/neutro**: o 0.7 já usa **dict** (o nº de linhas domina; packar os poucos
   únicos mal ajuda). Cadência já é coberta por seq-RLE; estruturado por split.
3. **Sob brotli o ganho quase evapora** (fnlwgt −41% → −6%; l_partkey −9%): é ganho **cru**
   (transporte sem compressão binária), não pós-brotli. Mesmo padrão do TCF em geral.
4. **Decimais/floats**: nature N/A (fallback) e pode **inflar** (Iws +9%/+22%) → exige variante.

## Decisão (do owner) — borderline
Pelo critério (≥15% weighted em 2+ reais), o nicho integer-alta-card **qualifica** (adult fnlwgt +
tpch partkey/orderkey), mas: (a) é per-coluna — o weighted da TABELA depende de quanto dela é
integer-alta-card; (b) some sob brotli. **Recomendação**: se welder, **nature opt-in** focada em
transporte cru/payload pequeno de tabelas integer-heavy (header declara). Antes: medir weighted
numa tabela integer-heavy + caracterizar as VARIANTES.

## Variantes registradas (não testadas)
- **padded-int** (zeros à esquerda, ex.: códigos): como `SPEC_IP` (padding), lossless.
- **scaled-decimal** (`x*10^d` + d): cobre decimais — mas precisão fixa cruza a linha lossy →
  **Pacote 10** (v2.0), não aqui.
- **signed / thousands-sep**: normalização reversível, baixa prioridade.

## Artefatos
- `analyze.py` — classificação + medição justa (0.7 vs 0.7+nature) + brotli.
