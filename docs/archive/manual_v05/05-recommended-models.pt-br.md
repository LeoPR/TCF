# 05 — Modelos recomendados (PT-BR)

Ranqueado por accuracy × custo baseado em resultados reais do M-Acomm
(2256 records sobre Adult + TPC-H × 4 paradigmas × 7 modelos comerciais
+ 13 modelos locais). Dados completos em
[../findings/04-naturalness-Q29-Q36.md](../findings/04-naturalness-Q29-Q36.md).

## Linha A (LLM lê TCF e calcula direto)

### Melhor custo/perf — gpt-5.4-nano

```python
client.responses.parse(
    model="gpt-5.4-nano",
    instructions=tcf_payload,            # cacheado
    input=pergunta,
    reasoning={"effort": "low"},         # obrigatorio para filter+agg
    text={"verbosity": "low"},
    max_output_tokens=2048,
    text_format=AnswerCell,
    prompt_cache_key=f"tcf_{model}_{seed}",
)
```

- 86.9% Adult-A, 76.2% TPC-H-A (melhor TPC-H Linha A entre comerciais!)
- $0.0007/call cacheado → $0.06 para 84 calls
- Ponto Pareto-ótimo custo × accuracy

### Frontier — gpt-5.4

- 95.2% Adult-A — único modelo >90% em Linha A
- $0.0061/call cacheado
- Use quando accuracy importa mais que custo

### Alternativa Anthropic — claude-haiku-4-5

- 79.8% Adult-A (com `thinking={"type":"enabled","budget_tokens":2048}`
  obrigatório — sem thinking cai para 58%)
- $0.0036/call cacheado
- Melhor opção Anthropic para Linha A em single-table

### Evitar para Linha A

- **gpt-4o-mini** — non-reasoning, cai para tier dos locais (52%)
- **Todos os modelos locais** — limitados em ~57% pelo ceiling de
  aritmética sobre 100+ valores (F-Q12 / F-Q28). Schema ambiguity em
  TPC-H derruba mais ainda.

## Linha B (LLM gera SQL → SQLite executa)

### Universalmente bons — gpt-5.4 ou gpt-5.4-mini

- **100%** Adult-B ambos, 85.7% TPC-H-B
- gpt-5.4-mini a $0.0006/call cacheado é o sweet spot de custo

### Melhor para multi-tabela — claude-sonnet-4-6

- **88.1%** TPC-H-B (único modelo que supera gpt-5.4 nesse ponto)
- 96.4% Adult-B
- $0.0024/call cacheado

### Recomendação local — qwen3:14b

- **100%** Adult-B em todos os níveis de naturalidade
- 95% N0 / 62% N2 em TPC-H-B (schema ambiguity bate)
- $0 (Ollama local)
- Use quando budget = 0 e dataset é pequeno / schema é limpo

### Pequeno mas capaz — qwen2.5-coder:7b

- 86% N0 em Adult-B
- 95% N0 em TPC-H-B (com reasoning — qwen3:14b ainda preferido)
- $0 — cabe em 12 GB VRAM

## O que NÃO usar

- **gpt-oss:latest (20B)** — frontier local em tamanho mas só 28.6%
  Linha A. Quantização MXFP4 parece prejudicar. Use qwen3:14b.
- **qwen3:0.6b** — capacity floor em 7%. Não use abaixo de 1.5B params
  para tarefa tabular.
- **gpt-4o-mini para Linha A em TPC-H** — 59.5% com `hours-per-week`
  falhando consistentemente (sem aspas duplas). Para Linha A use
  gpt-5.x; para Linha B até gpt-4o-mini funciona (85.7%).

## Árvore de decisão

```
Precisa accuracy > 90%?
  Sim → gpt-5.4 (Linha A) ou gpt-5.4-mini (Linha B)
  Não → continua

Multi-tabela com schema ambíguo?
  Sim → Linha B + claude-sonnet-4-6 (melhor schema-mapping)
  Não → continua

Budget restrito ($0.05/100 calls)?
  Sim → gpt-5.4-nano (comercial) ou qwen3:14b (local)
  Não → gpt-5.4-mini

Workload com muitos JOINs?
  Sim → Linha B obrigatório (Linha A morre em 17% q_top_product)
  Não → qualquer um
```

## Tabela de preços (2026-04, USD por 1M tokens)

| Modelo | Input | Output | Cached input |
|--------|-------|--------|---------------|
| gpt-5.4-nano | $0.20 | $1.25 | $0.02 |
| gpt-5.4-mini | $0.75 | $4.50 | $0.075 |
| gpt-5.4 | $2.50 | $15.00 | $0.25 |
| gpt-4o-mini | $0.15 | $0.60 | $0.075 |
| claude-haiku-4-5 | $1.00 | $5.00 | $0.10 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $0.30 |
| claude-opus-4-7 | $5.00 | $25.00 | $0.50 |

Verifique preços atuais em
[`scripts/../experiments/eval/llm_eval/commercial_client.py`](../../experiments/eval/llm_eval/commercial_client.py).
