---
title: Figuras do paper — gerar graficos a partir dos manifests
type: paper
status: OPEN
priority: MEDIUM
created: 2026-04-27
origin: Pos-reorg (figuras/ vazio em docs/article/)
see_also:
  - docs/article/figuras/ (atualmente vazio)
  - docs/article/07-results.md (consume figuras)
---

# Figuras do paper — geracao a partir dos manifests

## Estado

Pasta [`docs/article/figuras/`](../../../article/figuras/) criada na reorg
(commit f3a56a6) mas vazia. Cap 7 referencia tabelas em markdown apenas.

## Figuras propostas (alta prioridade)

### F1 — Tabela 2D (heatmap)

Heatmap das 8 celulas paradigma × dataset × naturalidade. Cores: accuracy
em escala verde-vermelho. Cells anotadas com F-Q correspondente.

**Fonte**: agregacao dos 4 manifests m_acomm*. ~30 linhas de matplotlib.

### F2 — Linha A vs Linha B por modelo (bar chart)

Comparativo lado-a-lado de Linha A vs Linha B em Adult + TPC-H, por
modelo (7 modelos OpenAI+Anthropic). Mostra:
- Paridade B em Adult
- Linha B vence em TPC-H
- gpt-4o-mini = transformacao 52→86%

### F3 — Naturalidade × accuracy por dataset (line chart)

4 niveis no eixo X, accuracy no Y, uma linha por modelo. 2 paineis
(Adult + TPC-H), 2 paradigmas cada = 4 paineis total.

Mostra dramaticamente:
- Adult: linhas planas (F-Q29, F-Q32)
- TPC-H N2: queda dramatica em todos os modelos (F-Q33+F-Q34)

### F4 — Schema scope × naturalidade (heatmap 4x4)

4 levels × 4 niveis = 16 cells. Mostra F-Q38 visualmente — minimal/N3
verde (81%), full/N3 vermelho (48%).

### F5 — Custo cumulativo por modelo

Bar chart custo total $ por modelo, com barra empilhada por dataset
(Adult vs TPC-H). Anotar accuracy media. Ilustra ponto Pareto
gpt-5.4-nano.

### F6 — Compressao TCF L0..L3 vs CSV/JSON

Bar chart bytes para Adult vol=100, mostrando 5 formatos. Anotar
roundtrip ✅/❌.

## Figuras opcionais (se houver tempo)

### F7 — Mecanismo de falha schema ambiguity (sankey)

Sankey diagram: pergunta N2 → coluna escolhida (correto vs alternativa)
→ accuracy. Mostra fluxo "valor comprometido" → cost (correto, 22%) /
cost*qty (errado, 78%).

### F8 — Latencia por modelo (boxplot)

Distribuicao de `total_ms` por modelo. Mostra Anthropic mais lento que
OpenAI; reasoning models mais lentos que non-reasoning.

## Criterio de aceite

- [ ] F1-F6 geradas via script (matplotlib ou plotly)
- [ ] Cada figura tem caption + referencia explicita no Cap 7
- [ ] Salvas em `docs/article/figuras/F[1-8].png` + `.svg`
- [ ] Script reproduzivel: `scripts/generate_paper_figures.py`
  consumindo manifests JSONL

## Dependencias

- Cap 7 escrito ✅ (mas pode ser ajustado para ancorar refs)
- matplotlib ou plotly instalado (pip)
- Manifests em experiments/results/ ✅

## Impacto estimado

- 1 dia para script + 6 figuras core (F1-F6)
- 1 dia adicional para opcionais (F7-F8) e ajustes de estilo

## Notas de revisao futura

- Re-gerar com manifests atualizados se experimentos forem refeitos
- Para submissao academica: pode precisar versao tikz/matplotlib2tikz
- Acessibilidade: usar paleta colorblind-safe
