---
title: Finding F80-F84 — STATS como shortcut cognitivo, nao calculo real
type: finding
status: CLOSED (2026-04-09)
origin: H-diagnostic-3layer-v02
---

# STATS como Shortcut Cognitivo

## Finding principal

Modelos que performam bem em TCF (gemma3:12b = 88% em Etapa 2) nao
estao CALCULANDO a partir dos dados — estao LENDO os STATS hints.

## Evidencia (diagnostic 3-layer, 6 modelos, retail_200)

| Modelo | L0 math (aritmetica pura) | L1 decode (ler formato) | L2 compute (formato + calculo) |
|--------|---------------------------|------------------------|-------------------------------|
| gemma3:12b | **0%** | **0%** | 75% |
| qwen3:8b | 50% | 100% | 50% |
| phi4 | 0% | 50% | 75% |
| gemma2:9b | 0% | 0% | 0% |

## Mecanismo

TCF inclui `# STATS total: n=509 sum=147445.47 min=2.46 max=899.44 avg=289.68`

Quando o modelo recebe "Qual e a soma de total?":
- **gemma3:** nao sabe somar 509 numeros (L0=0%), nao sabe listar valores (L1=0%),
  mas encontra `sum=147445.47` nos STATS e responde corretamente (L2=75%).
- **qwen3 com thinking:** genuinamente soma 509 numeros em 494s (L0=50%),
  lista todos os 509 valores (L1=100%), mas pode falhar em L2 por outros motivos.

## Implicacoes

1. **Etapa 2 pode estar inflada** — 88% de gemma3 em TCF L0 pode ser 
   maioritariamente leitura de STATS, nao compreensao do formato
2. **STATS sao uma FEATURE, nao um bug** — se o modelo nao sabe calcular,
   dar hints meta-cognitivos e uma estrategia valida
3. **Experimento critico:** STATS ablation (include_stats=False) para 
   separar accuracy real de accuracy por hints
4. **Para o paper:** mudar narrativa de "modelos entendem TCF" para 
   "TCF com hints meta-cognitivos compensa limitacoes aritmeticas dos LLMs"
