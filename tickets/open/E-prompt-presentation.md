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

### 2b. Nivel de explicacao da compressao (NOVO 2026-04-10)

Sub-ablacao especifica para a **quantidade de explicacao** no system prompt:

| Nivel | Prompt do formato | Tamanho |
|-------|-------------------|---------|
| **E0: Zero** | "Voce recebera dados." | ~30 chars |
| **E1: Nome so** | "Voce recebera dados em formato TCF. Responda baseado nos dados." | ~80 chars |
| **E2: Mencao RLE** | "Voce recebera dados em formato TCF (colunar com RLE)." | ~90 chars |
| **E3: Notacao explicita (atual)** | "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes." | ~200 chars |
| **E4: Detalhado** | E3 + "STATS lines dao sum, avg, count pre-computados. Dict lines mapeiam indices para valores. Colunas sao listadas uma por bloco." | ~400 chars |
| **E5: Tutorial completo** | E4 + exemplo pequeno de entrada e como interpreta-lo. | ~800 chars |

**Hipoteses:**
- **H-explain-1:** E0 → muitos FAIL (modelo nao entende N*val)
- **H-explain-2:** E3 (atual) e suficiente — E4/E5 tem diminishing returns
- **H-explain-3:** E5 ajuda modelos menores (<4B) mas nao modelos grandes (>12B)

**Teste:**
- 3 modelos (gemma3:1b, gemma3:4b, gemma3:12b) × 6 niveis E0-E5 × 3 questoes
- Total: 54 combos
- Accuracy esperada: crescente ate certo ponto, depois platea

**Sub-dimensao: misturar contextos (mais complexo)**
- E3-markdown: TCF dentro de bloco MD explicando contexto em volta
- E3-csv-compare: mostrar primeiro CSV e depois TCF "e o mesmo em TCF"
- E3-llm-style: prompt no estilo dos exemplos da Anthropic/OpenAI

Relacionado a Sui 2024 self-augmentation (+3.26%).

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
