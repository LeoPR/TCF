---
title: STATS ablation — accuracy com vs sem hints meta-cognitivos
type: experiment
status: IN_PROGRESS
priority: CRITICAL
origin: Finding F81 (diagnostic 3-layer) — gemma3 usa STATS como shortcut
created: 2026-04-09
---

# STATS Ablation

## Motivacao

O diagnostic 3-layer (F81) revelou que gemma3:12b (nosso melhor modelo,
88% em Etapa 2) nao calcula — le STATS hints. Precisamos quantificar
quanto da accuracy de Etapa 2 e "real" vs "inflada por STATS".

## Hipotese

H-stats: "Remover STATS lines reduz drasticamente accuracy de modelos
que nao tem thinking (gemma3, phi4), mas afeta menos modelos com
thinking real (qwen3)."

Se confirmado: STATS sao feature (nao bug), e a narrativa do paper
muda para "TCF com hints meta-cognitivos".

Se refutado (accuracy nao cai): modelos usam outro mecanismo.

## Design

Replicar Etapa 2 com include_stats=False.

### Modelos (subset representativo, nao todos 12):
- gemma3:12b — melhor em Etapa 2, confirmado leitor de STATS (F81)
- qwen3:8b — unico que genuinamente calcula (F82)
- phi4:latest — bom em Etapa 2, status de STATS desconhecido
- llama3.1:8b — medio, status desconhecido

### Formatos:
- TCF L0 com STATS (baseline — repetir para confirmar)
- TCF L0 sem STATS (ablacao)
- TCF L2 com STATS (baseline)
- TCF L2 sem STATS (ablacao)

### Questoes:
Mesmas 8 de Etapa 2 (q1-q8).

### Total:
4 modelos × 4 formatos × 8 questoes = 128 combos

## Resultado esperado

| Modelo | TCF L0+STATS | TCF L0-STATS | Delta |
|--------|-------------|-------------|-------|
| gemma3 | ~88% | ~10%? | -78pp? |
| qwen3 | ~50% | ~40%? | -10pp? |
| phi4 | ~75% | ~20%? | -55pp? |
| llama3.1 | ~75% | ~30%? | -45pp? |

Se o delta for > 30pp para gemma3, confirma F81 com forca.

## Decisao de registro

Este experimento nasceu do finding F81 (2026-04-09 diagnostic).
Ordem: F81 descoberto → hipotese H-stats formulada → este experimento.
Resultado sera registrado como R-F9x.

## Tarefas

- [x] Criar ticket com design
- [ ] Implementar runner (adaptar run_etapa2.py)
- [ ] Rodar 128 combos
- [ ] Comparar com resultados originais de Etapa 2
- [ ] Registrar findings
- [ ] Atualizar narrativa do paper se necessario
