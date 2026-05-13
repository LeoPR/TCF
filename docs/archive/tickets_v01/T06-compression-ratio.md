# T06 — Métricas de Compactação

**Status:** ABERTO  
**Tipo:** Análise  
**Deps:** T01, T05

## Pergunta
Como medir se o TCF é realmente mais compacto que os formatos atuais?  
O que "compacto" significa no contexto de LLMs?

## Métricas Relevantes

### 1. Tamanho em chars/bytes
- CSV bruto de `vendas` = **471 chars** (medido)
- JSON Lines expandido (com nomes) = **2336 chars** (medido) — 5x maior
- TCF estimado = ~500-600 chars total (com DICTs) — verificar após T05

### 2. Token count (mais relevante para LLM)
- LLMs cobram por token, não por char
- Um float `3.75` pode ser 2-3 tokens; `3` é 1 token
- Bins inteiros são mais baratos em tokens
- Medir com `tiktoken` ou contagem aproximada do Ollama

### 3. Ratio de perda semântica
- Bins perdem precisão numérica
- Medir: quanto erro médio introduz a quantização?
- Aceitável: <5% em operações agregadas?

## Benchmark Proposto

Para os dados atuais (vendas + joins), comparar:

| Formato | Chars | Tokens (aprox) | Accuracy Q1 | Accuracy Q5 |
|---------|-------|----------------|-------------|-------------|
| CSV expandido | ? | ? | baseline | baseline |
| JSON Lines | ? | ? | ? | ? |
| TCF raw float | ? | ? | ? | ? |
| TCF bins-16 | ? | ? | ? | ? |
| TCF int*100 | ? | ? | ? | ? |

## Questões em Aberto
- [ ] Medir token count real usando Ollama tokenizer ou tiktoken
- [ ] Definir "tamanho do prompt completo" (schema + dados + pergunta)
- [ ] Qual o threshold mínimo de accuracy para considerar o formato válido?
- [ ] Incluir tempo de inferência como métrica?
