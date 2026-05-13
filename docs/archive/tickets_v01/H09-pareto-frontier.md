# H09 — Fronteira de Pareto: Accuracy × Token Count

**Status:** ABERTO (derivado de H02)  
**Deps:** H02, P01  
**LLM calls:** 0 extras (usa resultados de H02)

## Hipótese

Alguma variante TCF ocupa posição Pareto-dominante: maior accuracy E menor token count que pelo menos um formato baseline.

**H9_0 (nula):** Nenhuma variante TCF é Pareto-dominante sobre todos os baselines.

## Métricas

- **Eixo X:** `prompt_eval_count` (tokens do prompt, reportado pela API Ollama)
- **Eixo Y:** accuracy média sobre todas as perguntas e modelos

## Medições por Formato (estimar antes de rodar)

| Formato | Chars (vendas) | Tokens (estimado) | Accuracy esperada |
|---------|---------------|-------------------|-------------------|
| csv_expanded | ~600 | ~180 | baseline |
| jsonl_expanded | ~2336 | ~700 | baseline |
| toon | ~800 | ~240 | similar CSV |
| tcf_raw | ~500 | ~150 | a medir |
| tcf_sorted | ~436 | ~130 | a medir |
| tcf_sorted_dict | ~900* | ~270* | a medir |

*tcf_sorted_dict inclui blocos DICT para FK — mais chars mas com semântica extra

## Output esperado

Gráfico Pareto (scatter):
```
accuracy
  1.0 │                    ● tcf_sorted_dict
  0.8 │         ● tcf_sorted
  0.6 │    ● tcf_raw    ● toon
  0.4 │              ● csv_expanded
  0.2 │                        ● jsonl_expanded
      └────────────────────────────────────────→ tokens
      0    200   400   600   800
```

Linha da fronteira Pareto conecta os pontos onde nenhum formato é estritamente melhor em ambos os eixos simultaneamente.

## Como capturar tokens

Adicionar ao `OllamaClient.generate()`:
```python
return {
    "text": data.get("response", ""),
    "prompt_tokens": data.get("prompt_eval_count", 0),
    "response_tokens": data.get("eval_count", 0),
}
```
Ver **P01**.
