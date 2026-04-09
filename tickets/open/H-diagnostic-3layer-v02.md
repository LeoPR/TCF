---
title: Diagnostico 3 camadas com v0.2 — math_control vs decode vs compute
type: hypothesis
status: DONE (2026-04-09)
priority: HIGH
origin: Revisao de H03 (v0.1)
---

# Diagnostico 3 Camadas (v0.2)

## Setup

- Dados: retail_sales(200) → 509 vendas, sum=147445.47
- Modelos: gemma3:12b, qwen3:8b, phi4, mistral, llama3.1, gemma2:9b
- Formatos: TCF L0, TCF L2 (layers 1 e 2); sem formato (layer 0)
- TCF inclui STATS lines (# STATS total: n=509 sum=147445.47 ...)
- 48 combos total

## Resultados

### Accuracy por camada

| Modelo | L0 math | L1 decode | L2 compute |
|--------|---------|-----------|------------|
| qwen3:8b | **50%** | **100%** | 50% |
| gemma3:12b | 0% | 0% | **75%** |
| phi4:latest | 0% | 50% | **75%** |
| llama3.1:8b | 0% | 50% | 50% |
| mistral:latest | 0% | 0% | 25% |
| gemma2:9b | 0% | 0% | 0% |

### Accuracy por camada x formato

| Modelo | L1 L0 | L1 L2 | L2 L0 | L2 L2 |
|--------|-------|-------|-------|-------|
| gemma3:12b | 0% | 0% | 100% | 50% |
| qwen3:8b | 100% | 100% | 100% | 0% |
| phi4 | 0% | 100% | 50% | 100% |
| llama3.1 | 0% | 100% | 50% | 50% |
| mistral | 0% | 0% | 50% | 0% |
| gemma2 | 0% | 0% | 0% | 0% |

## Findings

### F80: Modelos nao fazem aritmetica pura com 509 numeros
5/6 modelos = 0% em math_control (somar 509 numeros sem formato).
Unico que acertou: qwen3:8b somou corretamente em 494s (8 min de thinking).
qwen3 errou COUNT mesmo com thinking.

### F81: gemma3:12b usa STATS como shortcut — nao calcula
- L0 math: 0% (nao soma numeros crus)
- L1 decode: 0% (nao lista valores do TCF)
- L2 compute: 75% (acerta sum e count — mas como?)
- Resposta: os STATS lines (`# STATS total: n=509 sum=147445.47`) 
  dao a resposta pronta. O modelo le os hints, nao processa os dados.

### F82: qwen3:8b genuinamente processa dados
- L0: 50% (somou 509 numeros em 8 min com thinking)
- L1: 100% (listou TODOS os 509 valores de TCF L0 e L2)
- L2: 50% (acerta L0, falha L2 com respostas vazias 0s)
- E o unico modelo que REALMENTE compreende o formato.

### F83: phi4 e llama3.1 leem L2 melhor que L0
phi4 L1: L0=0% L2=100%. llama3.1 L1: L0=0% L2=100%.
Hipotese: RLE agrupado e mais legivel (menos linhas para processar).
Ou: esses modelos acertam o count via STATS e falham no list completo.

### F84: gemma2:9b = 0% absoluto em todas as camadas
Confirma Etapa 2 (0% TCF). Nao e problema de formato — o modelo nao
consegue fazer NADA com dados tabulares neste volume.

## Implicacao critica

### STATS sao um "cheat code"
gemma3:12b (88% em Etapa 2, melhor modelo) esta basicamente LENDO
as respostas dos STATS, nao COMPUTANDO a partir dos dados.

Isso significa:
1. TCF com STATS = alta accuracy (modelo le resposta pronta)
2. TCF sem STATS = accuracy cai drasticamente
3. A Etapa 2 inteira pode estar inflada pelos STATS hints

### Experimento necessario: STATS ablation
Rodar os mesmos modelos com TCF L0/L2 **sem** STATS lines.
Se accuracy cai de 88% para ~0%, confirma que os modelos nao 
processam os dados — so leem hints.

Se cai mas nao para zero, os modelos fazem ALGO alem de ler hints.

### Para o paper
Este finding e **central**. Muda a narrativa de "TCF comprime e 
modelos entendem" para "TCF com hints meta-cognitivos (STATS) 
permite que modelos que NAO sabem calcular ainda acertem."

O valor do TCF nao e so compressao — e prover hints que compensam
a limitacao aritmetica dos modelos.
