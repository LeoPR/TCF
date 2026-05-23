---
title: T-EXP-NATUREZAS-RARAS-EXPLORACAO — Naturezas #5 (range) e #8 (arredondamento)
status: closed
resolution: no-go-padroes-raros-em-datasets-gerais
priority: P3
created: 2026-05-23
updated: 2026-05-23
closed: 2026-05-23
blocked-by: []
related:
  - experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md
  - experiments/lab/dirty/2026-05-23-naturezas-raras-exploracao/
  - tickets/T-EXP-PACOTE5-T03-ENUMERATED.md
  - docs/theory/data-natures-taxonomy.md
---

# T-EXP-NATUREZAS-RARAS-EXPLORACAO — Naturezas #5/#8

## Contexto / motivacao

Reflexao 2026-05-23 sobre naturezas numericas identificou 2 candidatos
nao-cobertos:
- **#5 Range constante**: IDs em range estreito (e.g., 1000..9999)
  poderiam comprimir mais com "base + N local" que prefix-comum atual
- **#8 Arredondamento implicito**: precos R$X.99, taxas %.5, valores
  com sufixo fixo. Encoder "prefix + suffix fixo" comprimiria.

Status pre-investigacao: incerto. Datasets disponiveis (D1-D9 + Adult
+ TPC-H) podem ou nao ter esses padroes em quantidade significativa.
Pacote 5 enumerated ja' refutou (M10 captura via dedup+seq-RLE).

## Hipotese / pergunta

**H-NAT-RARAS-01**: Existem colunas em datasets reais (Adult+TPC-H)
com padrao #5 (range narrow) ou #8 (arredondamento implicito) onde
M10 atual NAO captura eficientemente?

Sub-questoes:
- Quais colunas numericas tem suffix comum (e.g., todos terminam ".99")?
- Quais tem prefix comum LONGO mas valores unicos?
- Quais tem cardinalidade alta MAS range narrow (e.g., 1000..9999)?
- M10 bytes/row vs lower bound teorico de encoder dedicado?

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-23-naturezas-raras-exploracao/`

### Sub-exp 01 — caracterizacao observacional

Pra cada coluna numerica em Adult+TPC-H + D1-D9 controle:
- Detectar suffix comum (e.g., todas terminam com ".99")
- Detectar prefix comum LONGO (> 50% do valor medio)
- Range narrow (max-min < 10x median, ou todos com mesmo digit count)
- Comparar M10 bytes vs estimativa encoder dedicado

### Criterio

Se algum padrao mostra >= 5% ganho potencial weighted em colunas
afetadas: GO sub-exp 02 (prototype). Caso contrario: NO-GO documentado.

## Riscos

1. **Datasets nao tem padroes raros**: Adult+TPC-H sao "general
   purpose", padroes financeiros/cientificos raros provavelmente
   nao aparecem
2. **M10 ja' captura via OBAT prefix**: prefix comum LONGO ja' deveria
   reduzir bytes via OBAT — sem ganho adicional possivel
3. **Anti-incidente**: Pacote 2 e Pacote 5 ja' refutados; provavel
   que esta exploracao tambem refute

## Conexoes

- [Reflexao naturezas numericas](../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md)
- [T-EXP-PACOTE5-T03-ENUMERATED](T-EXP-PACOTE5-T03-ENUMERATED.md) — precedente NO-GO
- [Taxonomia natureza](../docs/theory/data-natures-taxonomy.md)

## Updates datados

### 2026-05-23 — abertura

Ticket criado seguindo convencao YAML frontmatter. Exploracao
observacional pra confirmar se padroes #5/#8 existem em datasets
disponiveis antes de prototypar encoders dedicados.

### 2026-05-23 — Sub-exp 01 caracterizacao: NO-GO

Sub-exp 01 detectou padroes em 66 colunas (9 D1-D9 + 57 real):

**#8 Suffix comum (>= 80% das strings)**: 12 cols detectadas.
- `tpch.lineitem-5k/l_quantity` suffix '.0' (100%): +26.44% isolado
- 11 outras cols categoricas (sex, class, race): encoder estimado PIOR
  porque sufixo "le", "0K" representa fim de string curta — M10 ja'
  captura via dedup MELHOR
- **Agregado real-world: -4.45% weighted (REGRESSAO)**

**#5 Range narrow numerico**: 4 cols detectadas
- `tpch.lineitem-5k/l_linenumber` (1..7): +32.91% isolado
- `adult/age` (17..90): +20-21% isolado
- `tpch.region-5k/r_regionkey` (0..4): -37.5% (pequeno demais)
- **Agregado real-world: +1.08% weighted (marginal)**

**Cols com potencial isolado >= 5%**: 3 (l_quantity, l_linenumber, age).
Total ganho potencial: ~13kB em 890kB real-world = ~1.5%.

**Veredito**: NO-GO. Padroes raros (#5, #8) existem isoladamente mas
em peso insuficiente. M10 + dedup + seq-RLE ja' captura suficientemente
em datasets gerais (Adult + TPC-H).

Encoder dedicado pra padroes especificos (e.g., suffix '.0' ou range
0..99) seria YAGNI — ganho seletivo nao justifica complexidade
arquitetural + manutencao + heuristica deteccao.

**Padroes financeiros REAIS** (precos .99, taxas %.5) precisariam
dataset financeiro real-world dedicado, NAO disponivel agora. Adiar
ate' (a) dataset disponivel OR (b) caso de uso especifico aparecer.

**Resolution**: no-go-padroes-raros-em-datasets-gerais.

**Aprendizado meta**: 6a refutacao da sessao (Pacote 2, Pacote 5,
H-DA-09c, e agora #5+#8). Padrao consistente confirma:
- TCF M10 esta proximo do otimo pra naturezas comuns
- Melhorias adicionais requerem datasets especializados OU
  refactor arquitetural maior (Cython/Rust H-PERF-06)
