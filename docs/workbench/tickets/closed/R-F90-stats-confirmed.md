---
title: Finding F90-F94 — STATS inflate accuracy in ALL models (confirmed)
type: finding
status: CLOSED (2026-04-09)
origin: E-stats-ablation
---

# STATS Inflate Accuracy in All Models

## Finding principal

A hipotese F81 (gemma3 le STATS ao inves de calcular) foi CONFIRMADA
para todos os 4 modelos testados. STATS hints elevam accuracy em
25-62pp dependendo do modelo e formato.

## Evidencia (4 modelos × 8 questoes × 2 levels × 2 stats = 128 combos)

| Modelo | L0+stats | L0-stats | Delta L0 | L2+stats | L2-stats | Delta L2 |
|--------|----------|----------|----------|----------|----------|----------|
| gemma3:12b | 88% | 62% | -25pp | 75% | 38% | -38pp |
| qwen3:8b | 75% | 12% | **-62pp** | 62% | 50% | -12pp |
| phi4:latest | 75% | 50% | -25pp | 62% | 25% | -38pp |
| llama3.1:8b | 75% | 38% | -38pp | 50% | 25% | -25pp |

## Findings detalhados

### F90: STATS inflam TODOS os modelos (sem excecao)
Delta medio: -38pp em L0, -28pp em L2. Confirma F81 universalmente.

### F91: qwen3 e o MAIS dependente em L0 (-62pp)
Refuta intuicao de que thinking models compensam ausencia de hints.
Em compute pipeline, qwen3 procura atalhos como os outros.

### F92: SUM e AVG sao impossiveis sem STATS
Para os 4 modelos: q1_sum e q2_avg = FAIL sem STATS.
Aritmetica de 509 numeros nao e factivel para LLMs neste contexto.

### F93: MAX, MIN, COUNT sobrevivem
Lookups visuais funcionam sem hints na maioria dos casos.

### F94: Sensibilidade por arquitetura
gemma3, phi4: L2 mais sensivel (-38pp) que L0 (-25pp)
qwen3: L0 mais sensivel (-62pp) que L2 (-12pp)
llama3.1: equilibrado (-38pp L0, -25pp L2)

## Implicacao para o paper

Narrativa nova:
> "TCF e uma ESTRATEGIA COMPOSTA: formato columnar compacto + hints
> meta-cognitivos (STATS) que compensam limitacoes aritmeticas."

E um finding ORIGINAL — primeiro paper a testar formatos com hints
embutidos. Nenhum competitor (CSV, JSONL, MD, TOON) tem essa feature.

## Reinterpretacao de findings anteriores

- **Etapa 2 (gemma3:12b 88%):** maioria do score vem dos STATS
- **F2 (G02 v0.1: TCF 43%):** sem STATS, esperado pior
- **R-F51 (gemma3 melhor modelo):** melhor em LER STATS, nao em calcular
- **G30 (think_on+t0=100%):** pode ser STATS reading, nao thinking real
