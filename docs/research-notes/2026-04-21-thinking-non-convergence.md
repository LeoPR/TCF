---
title: Non-convergent thinking em reasoning models — um modo de falha específico
date: 2026-04-21
type: research-note
status: OBSERVED_LIMITED_SCOPE
related:
  - infra/docs/ollama-server-behavior.md
  - docs/methodology/llm-research-rigor.md
  - infra/model-qualification/results/probe_deepseek_budget.json
warnings:
  - "Findings limitados a UMA task domain específica. Não generalizar."
  - "Resultado PRECISA ser contextualizado em qualquer citação externa."
---

# Non-convergent thinking em reasoning models

## ⚠️ Caveats críticos antes de ler

Esta nota documenta um **modo de falha observado em escopo narrow**. Leia
as seções de limitações antes de citar em qualquer lugar externo ao projeto.

**Especificamente**: observamos comportamento patológico em `deepseek-r1:7b`
resolvendo uma tarefa específica (contagem de linhas em dado tabular
comprimido TCF L3). Isso **não significa** que o modelo falhe
genericamente — para a esmagadora maioria das tasks (factual, aritmética,
código, QA) esse modelo provavelmente funciona bem.

O que observamos é específico de **prompts estruturalmente incomuns**
(L3 TCF com dict+RLE+indices) combinado com **uma pergunta específica**
(contar linhas implícitas). É plausível que estejamos numa **"zona cinzenta"**
fora da distribuição de treinamento, forçando o modelo a uma
**alucinação controlada** (geração não-convergente interpretada como
pensamento).

## Observação empírica

**Experimento** (2026-04-21, probe_deepseek_budget.py):
- Modelo: `deepseek-r1:7b`
- Prompt: L3 TCF dict+RLE, n=115 vendas, pergunta "Quantas linhas existem?"
- Variando `num_predict` (budget de tokens): 4096, 8192, 16384, 32768

Resultado:

| num_predict | thinking chars | done_reason | resposta |
|-------------|----------------|-------------|----------|
| 4096 | 2121 | stop | "16" (errado, real=115) |
| 8192 | **31950** | length | (vazio, truncado) |
| 16384 | **70052** | length | (vazio, truncado) |
| 32768 | ainda rodando | ? | ? |

**Padrão**: aumentar o budget **aumenta desproporcionalmente** o comprimento
do thinking, sem convergência. Com 8x o budget (8k→16k), o thinking usa
2.2x mais tokens. Se extrapolarmos linearmente, **nenhum budget razoável**
faria o modelo convergir nessa tarefa específica.

### Comparação com modelo maior
`deepseek-r1:14b` (mesmo family, 2x parâmetros) **acerta** essa pergunta
com thinking curto e `done=stop`. Isto sugere que **capacidade arquitetural**
(não apenas budget) é o fator determinante.

## Interpretação — hipóteses

### H1: "Zona cinzenta" fora do treinamento
A combinação `L3 dict+RLE + PT + pergunta sobre contagem implícita`
é provavelmente raríssima no corpus de treino do deepseek-r1:7b. O modelo
reconhece a estrutura vagamente mas não possui heurísticas robustas. Sem
convergência, itera indefinidamente.

### H2: Geração não-convergente como artefato
Thinking em modelos menores pode degenerar em loops semânticos — "deixa
eu verificar de novo... vou contar outra vez... hmm, ainda não tenho
certeza...". Esse comportamento pode ser **raro em tasks comuns** mas
**frequente em tasks incomuns** (como a nossa).

### H3: Bias da task específica
Prompts pedindo "quantas linhas" em dado COMPRIMIDO (não expandido)
forçam o modelo a mentalmente expandir o RLE antes de contar. Isso exige
state-tracking extenso. Para 7B, isso pode estar no limite da capacidade
de manter contexto consistente durante geração.

### H4: Task familiarity bias
Outras perguntas sobre os mesmos dados (q_distinct, q_lookup_value)
funcionaram no deepseek-r1:7b em Phase 1. Só q_count e q_lookup (que
requerem contagem implícita de RLE) travaram. **Não é o dado; é a
pergunta específica.**

## Limitações do estudo

### Amostragem muito pequena
- **1 modelo** (deepseek-r1:7b)
- **1 task domain** (L3 TCF retail sales)
- **2 perguntas testadas profundamente** (q_count, q_lookup)
- **1 seed principal** (42)
- **1 formato de prompt** (sistema em PT, pergunta em PT)

Para concluir "deepseek-r1:7b tem modo de falha X", precisaríamos:
- Testar em ≥5 task domains diferentes (code, chat, tabular, QA, math)
- Testar ≥10 seeds por combo
- Testar múltiplos formatos de prompt
- Comparar com literatura publicada sobre o modelo

### Vieses possíveis
- **Ollama-specific**: o comportamento pode ser artefato da implementação
  do Ollama, não do modelo em si (uma inferência via vLLM ou HuggingFace
  pode não reproduzir)
- **Quantização Q4_K_M**: a versão quantizada pode diferir do fp16
  original do DeepSeek — é possível que o fp16 convirja onde Q4 não
- **GGUF conversion**: o arquivo GGUF veio de conversão; perda de
  fidelidade é possível

### O que NÃO testamos
- Se o bug aparece em outros prompts de contagem em dados tabulares
  (CSV, JSONL, etc.) — pode ser específico de L3 compression
- Se temperatura > 0 resolveria (thinking mais variável pode convergir)
- Se prompts mais longos com exemplos (few-shot) ajudariam
- Se desativar o `<think>` tag manualmente (via templating) muda algo

## Ação recomendada (e NÃO recomendada)

### SIM
1. **Documentar como observação** com escopo narrow explícito (esta nota)
2. **Incluir caveats** em qualquer menção no artigo do TCF
3. **Apresentar resultados de deepseek-r1:7b** separadamente dos outros —
   não agregar com média cross-modelos sem qualificar
4. **Sinalizar como direção futura de pesquisa** digna de estudo próprio

### NÃO
1. ❌ Concluir genericamente "deepseek-r1:7b falha em tasks estruturais"
2. ❌ Usar esse dado pra rebaixar o modelo em relação aos concorrentes
3. ❌ Ignorar o fato de que o modelo funciona bem em 2/5 das nossas próprias
   perguntas (q_distinct, q_lookup_value) — não é "completo fail"
4. ❌ Extrapolar para deepseek-r1:14b ou outros reasoning models sem teste
   dedicado

## Propostas de estudo futuro

Este achado **por si só** justificaria um projeto próprio, separado do TCF:

### "Characterization of thinking non-convergence in small reasoning LLMs"

**Hipóteses principais:**
- Qual fração de prompts "out-of-distribution" trigger non-convergent
  thinking em qual família/tamanho?
- O pattern é **monotônico com tamanho** (menores mais vulneráveis)?
- Existe uma **fronteira detectável** (métrica a priori) entre "convergent"
  e "non-convergent" prompts?

**Design experimental** (não executado — futuro):
- Matriz: 5 modelos (phi4-reasoning, qwen3:*, deepseek-r1:*, gpt-oss)
  × 7 task domains × 10 prompt variations × 5 seeds
- Métricas: thinking_length distribution, convergence rate, budget scaling
- Baseline comparativo: mesmo modelo com think=false (onde suportado)

**Custo estimado**: ≥2000 combos, ~1-2 semanas de GPU.

## Implicação para o TCF

**Para o paper do TCF (atual)**:
- **Não fazer claim forte sobre deepseek-r1:7b** como "inadequado pra TCF"
- **Usar pra ilustrar** que formato e modelo interagem; nem toda combinação
  funciona independentemente
- **Focar em descobertas positivas**: formatos que funcionam, thresholds
  de capacity, etc.
- **Citar esta nota** ao mencionar o comportamento, sem generalizar

**Para a metodologia**:
- Reforça `docs/methodology/llm-research-rigor.md` seção "3 camadas de
  falha" — muitas observações TCF anteriores podem ter sido confundidas
  com esse modo de falha de thinking infra-convergente
- Ao medir TCF accuracy, **log done_reason e thinking_length** em TODO
  record — a instrumentação feita em 2026-04-21 resolve isso

## Próximo passo: separação de projetos

Este achado confirma que o estudo de modelos/infra merece projeto dedicado.
Proposta:

```
TCF (projeto atual)
  └── Consome qualified_models.json  ← input externo
  └── Reports accuracy com caveats

[NEW] Model Infra Suite (projeto separado)
  └── Qualification suite (migrada de infra/)
  └── Thinking behavior characterization (nova)
  └── Output: qualified_models.json + caveats database
```

TCF cita resultados da Infra Suite como external dependency; Infra Suite
publica como standalone ferramenta/paper.

## Referências

- `infra/model-qualification/results/probe_deepseek_budget.json` (raw data
  deste experimento quando completar)
- `docs/research-notes/2026-04-20-qualification-findings.md` F-Q1 (evidência
  anterior de comportamento de deepseek-r1)
- `docs/methodology/llm-research-rigor.md` seção "3 camadas de falha"
