# P01 — Captura de Token Count da API Ollama

**Status:** ABERTO  
**Tipo:** Infraestrutura  
**Bloqueia:** H09 (Pareto), H02 (métrica secundária)  
**Arquivo:** `experiments/eval/llm_eval/ollama_client.py`

## Problema

O `OllamaClient.generate()` retorna apenas o texto da resposta. A API Ollama já inclui na resposta:
- `prompt_eval_count` — tokens do prompt
- `eval_count` — tokens gerados

Sem isso, não é possível medir token efficiency (DV2, DV3).

## Mudança

```python
# ANTES
def generate(self, model, prompt, options=None) -> str:
    ...
    return data.get("response", "")

# DEPOIS
def generate(self, model, prompt, options=None) -> dict:
    ...
    return {
        "text":            data.get("response", ""),
        "prompt_tokens":   data.get("prompt_eval_count", 0),
        "response_tokens": data.get("eval_count", 0),
        "total_duration_ns": data.get("total_duration", 0),
    }
```

## Impacto

Todos os chamadores de `generate()` precisam ser atualizados para usar `result["text"]` em vez de `result` diretamente. Verificar:
- `experiments/eval/llm_eval/runner.py`
- `experiments/eval/run_eval.py`

## Critério de Aceitação

`client.generate(model, prompt)["prompt_tokens"]` retorna inteiro > 0 para qualquer prompt não-vazio.
