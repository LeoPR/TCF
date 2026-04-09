---
title: Ablacao de apresentacao — idioma, decoracao, sintaxe RLE
type: experiment
status: OPEN
priority: MEDIUM
origin: Consolidacao de H-G36 (idioma) + H-G37 (notacao/decoracao)
---

# Ablacao de Apresentacao ao LLM

## Contexto

Varias hipoteses sobre como apresentar dados/perguntas ao LLM foram
registradas separadamente. Todas variam a mesma dimensao: o PROMPT,
nao os dados nem o modelo. Consolidadas aqui.

## Variaveis a testar

### 1. Idioma (ex-G36)
- Perguntas em pt-BR vs en-US
- Dados com nomes pt-BR (Ana, Caneta) vs en-US (Alice, Pen)
- Hipotese: LLMs treinados majoritariamente em ingles podem performar melhor

### 2. Decoracao do formato (ex-G37)
- TCF cru (como esta)
- TCF em code fence (```tcf ... ```)
- TCF em tag XML (<data>...</data>)
- TCF com header explicativo ("The following is TCF format where N*val means...")

### 3. Sintaxe RLE
- `3*Ana` (atual)
- `Ana x3`
- `Ana (repeated 3 times)`
- Hipotese: notacao mais "natural" pode ajudar modelos menores

### 4. Few-shot examples
- Zero-shot (atual)
- 1-shot: exemplo pequeno com resposta correta
- Hipotese: exemplo mostra ao LLM como interpretar o formato

### 5. Formulacao da pergunta (wording)
A literatura mostra que wording pode variar accuracy de 24% a 100%
(Washington 2023). Precisamos medir se nossos resultados sao robustos.

Para q1_sum (representativa), testar:
- A: "Qual e a soma de todos os valores da coluna 'total'?" (atual, formal pt-BR)
- B: "Soma tudo da coluna total" (informal pt-BR)
- C: "Compute SUM(total)" (tecnico/SQL-like)
- D: "What is the sum of all values in the 'total' column?" (formal en-US)
- E: "Add up all the total values" (informal en-US)

Se variancia entre A-E < 10pp → robusto, reportar no paper.
Se variancia > 20pp → wording e confounding, mitigar (media ou escolher neutro).

### Literatura relevante

- Sui et al. 2024 "Table Meets LLM" — variacao de input design afeta performance.
  Self-augmentation (explicar formato + key values) melhorou 3.26%.
- Washington 2023 — mesma tarefa, wording diferente: 24% vs 100% (LLaMA-2-13B).
- "Same Meaning Different Scores" (2026) — lexical > syntactic sensitivity.
- OpenAI/Anthropic — recomendam output format no final, XML tags, role constraints.
- MLCommons PSB (2025) — benchmark de estabilidade de prompts (industria).

## Design experimental

Modelo fixo: gemma3:12b (melhor em Etapa 2)
Formato fixo: TCF L2 (onde ha mais espaco para melhorar)
Questao fixa para wording: q1_sum (5 formulacoes)
Questoes para demais variaveis: q1_sum, q5_count, q6_top_product

Variar UMA dimensao por vez (ablacao):
- Baseline: pt-BR formal, sem decoracao, 3*Ana, zero-shot
- Idioma: en-US formal, sem decoracao, 3*Ana, zero-shot
- Code fence: pt-BR, code fence, 3*Ana, zero-shot
- XML tag: pt-BR, XML tag, 3*Ana, zero-shot
- Explicacao: pt-BR, header explicativo, 3*Ana, zero-shot
- Sintaxe alt: pt-BR, sem decoracao, Ana x3, zero-shot
- Few-shot: pt-BR, sem decoracao, 3*Ana, 1-shot
- Wording B-E: 4 formulacoes alternativas de q1_sum

Total: 7 configs x 3 questoes + 4 wording = 25 combos (~1h)

## Tarefas

- [ ] Implementar variantes de prompt em formats.py ou script dedicado
- [ ] Rodar 21 combos com gemma3:12b
- [ ] Analisar: alguma decoracao melhora significativamente?
- [ ] Se sim, adotar como default nos proximos experimentos
- [ ] Documentar em article/07
