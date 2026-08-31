---
title: Speed tradeoffs — quanto accuracy se perde para ganhar velocidade?
type: experiment
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Quanto accuracy um usuario sacrifica para ter latencia menor?
---

# Speed Tradeoffs

## Pergunta central

Um usuario de producao quer resposta RAPIDA. Quais configuracoes sacrificam
quanto de accuracy para acelerar?

Eixos de variacao:
1. **Tamanho do modelo** (12B vs 4B vs 1B)
2. **Quantizacao** (FP16 vs Q8 vs Q4 vs Q2)
3. **Thinking** (ON vs OFF)
4. **num_ctx forcado** (contexto menor = menos prefill)
5. **Temperature** (0 vs 0.6 vs 1.0)
6. **Nivel TCF** (L0 vs L2 vs L3 — mais compacto = prefill mais rapido)

## Evidencia da literatura (pesquisa 2026-04-10)

### Quantizacao
- **Q8 vs FP16:** <2% perplexity increase (minimal loss)
- **Q4 vs FP16:** boa para chat, ruim para math reasoning/code
- **Q2:** perda significativa em tarefas dificeis
- **Tabular reasoning:** nao ha benchmarks especificos — presumivelmente
  sensivel como math (agregacoes exigem precisao)

Fonte: arXiv 2409.11055 (2025 benchmark), Jarvislabs guide,
ML Journey Q4 vs Q8 vs FP16.

### Thinking
- Ja testamos em G30 (qwen3:8b): think_on+t=0 = 100% em L0 vs 67% sem thinking
- Custo: 8-120x mais lento (qwen3 L0 math: 494s vs 5s sem thinking)

### num_ctx
- **Default Ollama:** 2048 (auto-expande)
- **Forcar menor:** pode truncar dados importantes
- **Forcar maior:** overhead de KV cache, mais prefill
- **Nao testado sistematicamente**

## Design experimental proposto

### Baseline
- Modelo: gemma3:12b Q4_K_M (default)
- TCF L0 com STATS
- Temperature 0
- Thinking OFF (gemma nao tem)
- num_ctx auto

### Variacoes independentes (A/B)

| Eixo | Config rapida | Config accurate | Delta esperado |
|------|---------------|-----------------|----------------|
| Tamanho | gemma3:1b | gemma3:12b | 10-30pp accuracy loss |
| Quant | phi4 Q4 (testar menor se disponivel) | phi4 FP16 | 2-5pp |
| Thinking | qwen3:8b think_off | qwen3:8b think_on | F60: 25pp em L0 |
| TCF level | L3 (menor) | L0 (expanded) | ? |
| num_ctx | 2048 forcado | auto (14K) | ? (provavelmente FAIL se truncado) |

### Metricas
- **Accuracy:** % correct
- **Latency per query:** wall-clock (s)
- **Latency per 1000 queries:** extrapolado
- **Cost** (se fosse API paga): tokens × preco

### Tabela Pareto (fronteira)
Eixo X: latency (s), Eixo Y: accuracy (%)
Cada ponto = (modelo, config). Identificar fronteira Pareto.

## Hipoteses

### H-speed-1: Quantizacao Q4 e seguro para TCF
**Porque:** se modelo le STATS (F81), nao precisa de alta precisao numerica.
**Teste:** Q4 vs Q8 do mesmo modelo — diferenca deve ser <5pp em TCF+STATS.

### H-speed-2: Thinking e caro demais para ROI
**Porque:** F60 mostrou 100% com thinking mas 8min de latencia.
**Teste:** para 1000 queries em producao, quanto melhor e ter 100% vs 75%?
Depende do custo do erro.

### H-speed-3: Modelo pequeno + STATS > modelo grande + CSV
**Porque:** o "truque" dos STATS compensa capacidade do modelo.
**Teste:** gemma3:1b + TCF L0 (com STATS) vs gemma3:12b + CSV.
Se gemma3:1b acerta MAIS (via STATS shortcut), muda tudo.

### H-speed-4: L3 (compacto) acelera sem sacrificar accuracy
**Porque:** prefill mais curto = latencia menor.
**Problema:** L3 tem indices numericos que confundem modelos (F33).
**Teste:** medir ambos em top 3 modelos.

## Relacao com outros tickets

- **H-G30**: ja cobriu thinking+temperature (qwen3:8b)
- **P-G35 H-quant**: hipotese de quantizacao ja listada
- **P-G35 H-scaling**: scaling curve por familia
- **M-stability-testing**: todas as medicoes devem ter N>=3

Este ticket **consolida** todas essas hipoteses em um experimento coeso.

## Output final

**Tabela operacional para o paper:**

| Cenario | Modelo | Quant | Think | Level | Acc | Latency | Uso recomendado |
|---------|--------|-------|-------|-------|-----|---------|-----------------|
| **Batch offline** | gemma3:12b | Q4 | - | L0 | 88% | 16s | Qualidade maxima |
| **API producao** | gemma3:4b | Q4 | - | L0 | ~60%? | 5s? | Latencia baixa |
| **Mobile/edge** | gemma3:1b | Q4 | - | L0 | ~30%? | 2s? | Minimo viavel |
| **Max accuracy** | qwen3:8b | Q8 | ON | L0 | 100% | 500s | Nao pratico |

Isso responde "qual config usar para meu caso".

## Tarefas

- [ ] Implementar matriz de combos (modelo × quant × think × level)
- [ ] Rodar ~50 combos com q1_sum + q3_max + q6_top_product
- [ ] Calcular Pareto frontier (accuracy × latency)
- [ ] Documentar como tabela operacional no paper
- [ ] Grafico scatter com fronteira Pareto (Fig nova)
