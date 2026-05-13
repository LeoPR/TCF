# H08 — Família do Modelo × Formato

**Status:** ABERTO  
**Deps:** H02, P06  
**LLM calls:** ~450

## Hipótese

Modelos de raciocínio (deepseek-r1, qwen3-thinking) são menos sensíveis ao formato do que modelos gerais, porque o chain-of-thought compensa dificuldades de leitura.

**H8_0 (nula):** Não há interação entre família do modelo e formato.

## Famílias

| Família | Modelos | Característica |
|---------|---------|----------------|
| `reasoning` | deepseek-r1, qwen3 (thinking), marco-o1 | CoT, `<think>` blocks |
| `general` | llama3.x, gemma3, mistral, phi3 | Instrução geral |
| `code` | qwen2.5-coder, deepseek-coder | Treinados em dados estruturados |
| `multilingual` | aya-expanse, modelos PT-strong | PT vs EN no prompt |

## Design

```
3 famílias × 6 formatos × 10 perguntas × 5 runs
= 900 calls (com 5 modelos selecionados)
```

## Evidência Preliminar (resultados existentes)

O deepseek-r1 nos resultados anteriores (`experiments/results/deepseek-r1_latest/`) mostrou:
- Produz `<think>...</think>` blocks com aritmética explícita passo-a-passo
- Conta 30 rows em vez de 41 → falha de decode, não de aritmética
- Conecta diretamente a H03: decode failure em modelos de raciocínio

**Implicação:** Reasoning models têm o pipeline certo (sabem somar) mas falham no parse do formato → TCF poderia ajudá-los mais em L1.

## Dependência Técnica

Modelos reasoning emitem `<think>` blocks. O scorer atual tenta parsear o texto inteiro como float e falha. **P02** (response parser com stripping de think-blocks) é pré-requisito.

## Variante Adicional: Prompt em PT vs EN

Testar se instruções em português melhoram accuracy vs inglês para modelos multilingual. Adicionar como fator opcional dentro desta hipótese.
