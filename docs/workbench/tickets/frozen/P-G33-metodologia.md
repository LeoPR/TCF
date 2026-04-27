---
title: Prompting CoT/PoT, repeticoes, survey literatura
type: research
status: OPEN
priority: MEDIUM
---

# Metodologia de Prompting

## Contexto

Nossos experimentos usam zero-shot direto com system prompt + dados + pergunta.
A literatura mostra que estrategias de prompting podem melhorar accuracy
significativamente. Precisamos decidir o que testar e o que apenas citar.

## Estrategias da literatura

### 1. Chain-of-Thought (CoT) — Wei et al. 2022
- "Pense passo a passo antes de responder"
- Melhora raciocinio multi-step
- **Relevancia TCF:** pode ajudar com RLE expansion mental (L2/L3)

### 2. Program of Thoughts (PoT) — Chen et al. 2023
- LLM gera codigo Python ao inves de calcular diretamente
- Elimina erros aritmeticos (~62% dos nossos erros sao aritmeticos)
- **Relevancia TCF:** muito alta — se PoT resolve a aritmetica,
  o formato importa menos (todos teriam ~100% via codigo)
- **Problema:** muda o que estamos testando (formato vs capacidade de codigo)

### 3. Self-Consistency — Wang et al. 2023
- Gerar N respostas, majority voting
- Melhora 5-15% tipicamente
- **Relevancia TCF:** reduz ruido, mas custo N×

### 4. Few-shot examples
- 1-3 exemplos antes da pergunta real
- **Relevancia TCF:** pode ensinar a interpretar N*val notation
- Ja incluido em E-prompt-presentation

### 5. PAL (Program-Aided Language) — Gao et al. 2023
- Similar a PoT — gerar codigo e executar
- **Relevancia TCF:** mesma consideracao que PoT

## Decisao para o paper

### Incluir como experimento:
- **CoT simples:** adicionar "Pense passo a passo" ao system prompt
  → Facil de implementar, 1 variavel adicional em E-prompt-presentation

### Citar mas NAO testar (scope):
- **PoT/PAL:** muda fundamentalmente o que estamos medindo.
  Se o LLM gera `sum([...])`, nao estamos testando compreensao do formato.
  Citar como "futuro trabalho" — TCF poderia gerar pandas code direto.
- **Self-Consistency:** custo N× nao justifica para paper de formato.
  Citar como "metodo de reducao de variancia disponivel."

### Repeticoes estatisticas:
- Cada combo atual e single-run (N=1)
- Para claims de significancia: rodar 3-5 repeticoes dos combos criticos
- Usar bootstrap CI 95% como em T-figures-analysis
- McNemar's test para pares (TCF vs CSV pareado por questao)

## Nosso setup atual

```
System prompt (format-specific) → CONTEXT (data) → USER (question)
```

- Temperature: 0 (deterministic) — confirmado por G30 como melhor
- Thinking: ON para modelos que suportam — confirmado por G30
- Single-shot, no CoT, no examples

## Prompt sensitivity (pesquisa 2026-04-09)

A literatura recente mostra que wording da pergunta importa tanto
quanto o formato dos dados:

- **Washington 2023:** mesma tarefa, wording diferente → 24% vs 100%
- **PromptSET (2025):** 11K prompts x 9 variações = benchmark de sensibilidade
- **"Same Meaning, Different Scores" (2026):** lexical > syntactic
- **POSIX (2024):** indice formal de sensibilidade a prompts
- **MLCommons PSB (2025):** primeiro benchmark industrial

**Implicacao:** nossos resultados sao baseados em UMA formulacao fixa
por pergunta. Se o wording influencia, os numeros podem ser frageis.

Mitigacao: E-prompt-presentation variavel 5 testa 5 formulacoes de
q1_sum. Se variancia < 10pp → robusto. Se > 20pp → reportar como
limitacao e usar media de formulacoes.

## Self-augmentation (Sui et al. 2024)

Sui propoe que o modelo primeiro explique o formato e identifique
key values antes de responder. Melhorou 3.26% em todas as tarefas.
Nosso equivalente: header explicativo em E-prompt-presentation
("The following is TCF format where N*val means...").

## Insight de F81 (STATS como shortcut)

Se o modelo le STATS ao inves de calcular, entao:
- CoT pode NAO ajudar (o modelo ja "sabe" a resposta dos STATS)
- PoT e irrelevante (nao ha calculo a fazer)
- A unica variavel real e: o modelo ENCONTRA os STATS no contexto?

Isso muda a perspectiva: a questao nao e "como perguntar melhor"
mas "como garantir que o modelo encontre os hints no contexto".

## Tarefas

- [ ] Adicionar "CoT" como variavel em E-prompt-presentation
- [ ] Definir quais combos precisam de repeticoes (N=3 ou N=5)
- [ ] Documentar decisao no paper: por que zero-shot direto e o baseline
- [ ] Citar PoT/PAL como futuro trabalho
- [ ] STATS ablation: separar "accuracy real" de "accuracy por hints"
- [ ] Wording ablation: 5 formulacoes de q1_sum (em E-prompt-presentation)
