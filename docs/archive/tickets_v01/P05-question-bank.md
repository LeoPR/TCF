# P05 — Banco de Perguntas Completo (Q1–Q10)

**Status:** PARCIALMENTE FEITO (Q1–Q5 implementados)  
**Tipo:** Infraestrutura  
**Bloqueia:** H02–H10  
**Arquivo:** `experiments/eval/llm_eval/prompts.py`

## Perguntas Completas

### Layer 0 — math_control (sem formato, só números)
| ID | Pergunta | Ground Truth |
|----|----------|--------------|
| L0_sum | "Some estes valores: {vl_list}. Responda só com o número." | 217.55 |
| L0_count | "Quantos números há nesta lista: {vl_list}?" | 41 |

### Layer 1 — decode_only (formato dado, sem conta)
| ID | Pergunta | Ground Truth |
|----|----------|--------------|
| L1_list | "Liste TODOS os valores da coluna 'vl', separados por espaço." | 41 valores |

### Layer 2 — compute (formato + operação)
| ID | Pergunta | Ground Truth | Requer FK? |
|----|----------|--------------|------------|
| Q1 | "Qual é a soma de vl?" | 217.55 | não |
| Q2 | "Qual é a média de vl?" | 5.3061 | não |
| Q3 | "Qual é o maior valor de vl?" | 12.40 | não |
| Q4 | "Qual é o menor valor de vl?" | 1.00 | não |
| Q5 | "Quantas linhas existem?" | 41 | não |
| Q6 | "Quantas vendas Ana fez?" | 3 | sim |
| Q7 | "Qual o total gasto por Ana?" | 8.70 | sim |
| Q8 | "Qual produto aparece mais vezes?" | Caneta | sim |
| Q9 | "Quantas pessoas distintas compraram?" | 27 | não |
| Q10 | "Qual pessoa gastou mais no total?" | calcular | sim |

## System Prompts por Formato

Adicionar ao `SYSTEM_PROMPTS` dict em `prompts.py`:
- `tcf`: já adicionado
- Expandir `math_control` (não usa formato, usa lista plana)

## Formato da Pergunta L0 (math_control)

Diferente das demais — não recebe data_block. Recebe lista plana de números:
```python
def build_math_control_prompt(vl_list: str, question: str) -> str:
    return (
        f"Dados estes números: {vl_list}\n\n"
        f"{question}\n\n"
        "Responda APENAS com o número, sem texto."
    )
```

## Critério de Aceitação

`list_questions()` retorna todas as 13 perguntas (L0×2, L1×1, Q1–Q10).  
Cada pergunta tem `layer`, `requires_fk`, `question_text`, `question_key`.
