# P02 — Response Parser: Think-Block Stripping + Error Classifier

**Status:** ABERTO  
**Tipo:** Infraestrutura  
**Bloqueia:** H03 (L1 decode accuracy), H08 (reasoning models)  
**Arquivo:** `experiments/eval/llm_eval/metrics.py`

## Problema 1 — Think blocks

Modelos reasoning (deepseek-r1, qwen3) emitem:
```
<think>
Preciso somar: 2.5 + 11.0 + ... = 217.55
</think>
217.55
```

O scorer atual tenta parsear `<think>...` como float e falha. Resposta correta (217.55) é ignorada.

## Solução 1

```python
def strip_think(text: str) -> str:
    import re
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def extract_number(text: str) -> float | None:
    text = strip_think(text)
    # Pega o último número do texto (modelos às vezes explicam antes)
    import re
    matches = re.findall(r'-?\d+(?:[.,]\d+)?', text.replace(',', '.'))
    return float(matches[-1]) if matches else None
```

## Problema 2 — Classificação de erros

Respostas erradas têm padrões distintos com implicações diferentes para o paper:

| Tipo | Padrão | Implicação |
|------|--------|------------|
| `list_instead_of_agg` | Resposta tem 10+ números separados | Modelo leu o formato mas não agregou |
| `wrong_count` | Número plausível mas errado (ex: 30 em vez de 41) | Contagem incorreta |
| `hallucinated` | Número fora do range possível | Modelo inventou |
| `arithmetic_error` | Número com parse correto mas soma errada | Fez conta errada |
| `refusal` | Nenhum número, texto explicativo | Recusou operar |
| `parse_failure` | Não extrai número nenhum | Formato não decodificado |

## Solução 2

```python
def classify_error(response: str, expected: float, question_type: str) -> str:
    nums = extract_all_numbers(response)
    if not nums:
        return "parse_failure" if len(response) > 20 else "refusal"
    if len(nums) > 5 and question_type in ("sum_field", "avg_field"):
        return "list_instead_of_agg"
    val = nums[-1]
    if abs(val - expected) / max(abs(expected), 1) < 0.01:
        return "correct"
    if question_type == "count_rows" and val != expected:
        return "wrong_count"
    if val < 0 or val > expected * 10:
        return "hallucinated"
    return "arithmetic_error"
```

## Critério de Aceitação

- Resposta `<think>...soma=217.55</think>\n217.55` → extrai `217.55` → `correct`
- Resposta `"2.5, 11.0, 1.0, ..."` → `list_instead_of_agg`
- Resposta `"30"` para count_rows=41 → `wrong_count`
