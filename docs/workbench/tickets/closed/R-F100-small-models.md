---
title: Finding F100-F103 — modelos <2B sao inviaveis para tabular em escala
type: finding
status: CLOSED (2026-04-10)
origin: Lote 1 da Etapa 2 Expandida (qwen3:0.6b, gemma3:1b, qwen3:1.7b)
---

# Modelos Pequenos (<2B) sao Inviaveis

## Evidencia

Lote 1 da Etapa 2 Expandida: 3 modelos × 3 formatos × 8 questoes = 72 combos
Dataset: retail_sales(200) → 509 vendas

| Modelo | Params | CSV | TCF L0 | TCF L2 | Avg |
|--------|--------|-----|--------|--------|-----|
| qwen3:0.6b | 0.6B | 12% | **0%** | 12% | 8% |
| gemma3:1b | 1B | 12% | **0%** | 12% | 8% |
| qwen3:1.7b | 2B | 0% | 0% | 12% | **4%** |

## Findings

### F100: Modelos <2B sao praticamente inuteis para tabular reasoning em escala
Accuracy 4-8% em 509 vendas. Nao distinguem sinal de ruido.
**Implicacao:** limite minimo pratico ~3-4B.

### F101: TCF L0 = 0% em todos os 3 modelos pequenos
Curiosamente, L2 (com RLE) performa MELHOR (12%) que L0 (0%).
**Hipotese:** L0 tem contexto maior (mais tokens) → overload em modelos
pequenos. L2 reduz a carga cognitiva.

### F102: Modelos pequenos nao "colapsam graciosamente"
Falham totalmente em L0 mas sobrevivem marginalmente em L2.
Nao e degradacao suave — e cliff effect.

### F103: qwen3:1.7b pior que qwen3:0.6b (4% vs 8%)
Thinking em modelo pequeno **atrapalha** para este tipo de dado.
Confirma padrao de G30 — thinking exige capacidade minima para ser util.

## Implicacoes para o paper

### Narrativa honesta
TCF NAO e util para todo mundo. Precisa de modelo minimo ~3-4B.
Abaixo disso, nada funciona (nem CSV, nem TCF).

### Refuta H-speed-3
E-speed-tradeoffs hipotetizou: "small model + STATS > big model + CSV".
**Refutada** para modelos <2B. STATS nao compensam incapacidade total.

### Para o "mapa de decisao" (M-llm-scope)
Adicionar coluna "Modelos inviaveis":
- < 2B: qualquer tipo de Q&A tabular em escala
- 2-4B: so lookups simples, nao agregacoes
- > 4B: viavel com STATS

## Dados adicionais necessarios

Lote 2 (gemma3:4b) vai confirmar se 4B e viavel ou ainda no cliff.
Lote 3 (qwen3:14b) sera o topo da scaling curve.

**Decisao:** nao rodar Lote 2/3 no formato antigo. Incorporar estes
modelos em Etapa 2 Expandida v2 com TOON e prompt_tokens.
