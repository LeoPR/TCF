---
title: Qualification suite — achados consolidados
date: 2026-04-20
type: research-note
status: FINDINGS
related:
  - infra/model-qualification/
  - docs/methodology/llm-research-rigor.md
  - docs/research-notes/2026-04-20-tcf-retrospective.md
---

# Qualification suite V2.2 — achados consolidados

Este documento consolida o que aprendemos rodando a Model Qualification Suite
em 2026-04-20. São achados **independentes do TCF**, sobre comportamento dos
modelos/Ollama/hardware, que passam a ser referência operacional do projeto.

## F-Q1: DeepSeek-R1 é intrinsic-thinking (causalidade confirmada)

**Evidência**: `deepseek-r1:7b` com `think=False` em 5/5 seeds retorna o
prompt ecoado (`"Qual a capital do Brasil? Responda apenas..."`). Com
`think=True` em 5/5 seeds retorna `"Brasília"`. Determinístico.

**Mecanismo**: DeepSeek-R1 foi treinado com reasoning como parte obrigatória
do pipeline de geração. Desativar via `think=False` força um modo operacional
inválido — o modelo entra em echo-loop.

**Política**: `deepseek-r1:*` sempre com `think=None` (deixar default do modelo
operar). No catálogo: `category: "intrinsic"`.

**Implicação retroativa**: todos os testes TCF anteriores do deepseek-r1:14b
rodaram com `--no-think`; o 14B foi robusto (100% em Phase 1) mas o score pode
ter custo de tokens menor quando thinking fica ativo. O 7B nunca foi testado em
TCF — deve entrar no painel agora.

## F-Q2: Qwen3-VL degrada text-only severamente

**Evidência**: `qwen3-vl:8b` em 6 variações de prompt para `list_colors`:
5/6 timeoutaram em 45s, 1/6 completou em 43s. Prompts simples (b4: "Liste 3
cores separadas por vírgula.") também timeoutaram. Contraste: `qwen3:8b`
(mesmo tamanho, sem vision) responde em 1.3s.

**Mecanismo hipotético**: A arquitetura `mllama`/vision-augmented do qwen3-vl
processa prompts text-only através de encoder multimodal, introduzindo
overhead patológico em alguns casos. Diferente do `llama3.2-vision:11b` que
preserva capacidade text-only.

**Política**: **não usar qwen3-vl:8b em experimentos text-only**. Marcado
como "not qualified" na qualification suite.

## F-Q3: Nenhum viés PT vs EN em accuracy canônica

**Evidência**: 5 top performers × 7 perguntas × 2 idiomas = 70 calls.
- Accuracy PT vs EN: **100% idêntica em todos 5 modelos**
- Response length: equivalente (delta ±7 chars)
- Latency: artefato de cold-start (primeira chamada PT lenta, demais iguais)

**Implicação retroativa**: dados TCF podem permanecer em PT sem preocupação
com viés fundamental. Qualquer "verbosity em PT" observada anteriormente em
contextos TCF é resposta a **complexidade do prompt estruturado**, não ao
idioma.

## F-Q4: Counting com ambiguidade linguística (3 ou 4)

**Evidência**: "Conte as palavras em 'A raposa marrom pula'" recebe:
- **4** de: `gpt-oss`, `qwen3:1.7b`, `qwen3:14b`, `qwen3:8b`, `llama3.2:3b` (sem vision), `gemma3:12b`, outros
- **3** de: `phi4`, `gemma3:4b`, `deepseek-r1:14b`, `deepseek-r1:7b`

**Mecanismo**: em PT, "A" é artigo definido. Contagem **lexical** = 4 tokens
(todas as palavras). Contagem de **conteúdo** = 3 (exclui artigo). Ambas
são válidas linguisticamente.

**Política**: scoring aceita `[3, 4]` como válidos e registra qual foi
respondido. No futuro, se precisarmos de contagem precisa, podemos consultar
este campo para escolher modelos "rigorosos lexicais" vs "content-words".

**Implicação TCF**: quando perguntamos "quantas linhas nos dados", diferentes
modelos podem interpretar "linhas" diferentemente (linhas físicas do TCF vs
linhas lógicas de dados). Precisa de desambiguação no prompt TCF.

## F-Q5: qwen3:0.6b tem capacity floor abaixo de canônicas

**Evidência**: `qwen3:0.6b` responde "Brasil" quando pergunta "capital do
Brasil" (confunde país com cidade). Mesmo padrão em "capital da França" →
"França". Arithmetic, instruction, colors OK.

**Mecanismo**: 0.6B parameters é abaixo do threshold necessário para
disambiguar pergunta sobre-entidade (factual recall). Sem relação com
thinking ou configuração — é limite real de capacity.

**Política**: `qwen3:0.6b` marcado como "not qualified". Usar apenas se
houver necessidade específica de capacity floor (ex: edge deployment
benchmark).

## F-Q6: Cold-start na primeira chamada PT custa 20-60s

**Evidência**: ao trocar modelo ou inicializar sessão, a primeira chamada
com prompt PT leva ~20-60s. Chamadas subsequentes do mesmo modelo em PT
são 2-8s (equivalente a EN).

**Mecanismo**: KV cache do Ollama precisa processar tokens PT (menos comuns
em training data) pela primeira vez. Depois da primeira, o cache tem o
vocabulário quente.

**Política**: ao medir latência, **descartar primeira chamada** ou usar
warmup prompt em PT curto antes da medição real.

## F-Q7: Catálogo de modelos modernos vs obsoletos

Obsoletos (não testar em rodadas principais):
- `phi3:latest` → usar `phi4`
- `mistral:latest` → `mistral-small` (não instalado, >12GB)
- `qwen2.5:latest`, `qwen2.5-coder:7b` → `qwen3:8b`
- `llama3.1:8b` → `llama3.2` (pequeno) ou `llama3.2-vision` (médio)
- `gemma2:9b` → `gemma3:12b`

Manter instalados para possíveis ablações históricas, mas **não incluir**
em experimentos principais. Marcados em `obsolete_models.json`.

## Consequências imediatas

- **`experiments/eval/run_frontier_search.py`** atualizado em 2026-04-20 para
  carregar `DEFAULT_MODELS` de `qualified_models.json`.
- **Thinking flag** nunca mais será setado sem consultar o catálogo.
- **Retrospectiva** (`2026-04-20-tcf-retrospective.md`) documenta quais
  phases precisam re-run e quais conclusões se mantêm.

## Histórico

- **V0 (inicial)**: hardcoded 14 modelos em `DEFAULT_MODELS`, sem
  qualification, `think=False` default universal.
- **V1 (2026-04-20)**: 14 modelos testados, 12 qualified, 2 failed.
- **V2 (2026-04-20)**: prompts refinados (desambiguar "cores", "palavras").
- **V2.1**: counting tolerance 3|4.
- **V2.2 (atual)**: thinking catalog per-model, deepseek-r1:7b requalified.
  12 qualified, 2 not-qualified, 6 obsolete.
