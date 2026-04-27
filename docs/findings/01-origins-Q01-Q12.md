---
title: Origens — capacidades fundamentais (F-Q1..F-Q12)
type: findings-block
range: F-Q1..F-Q12
parent: docs/findings/README.md
---

# Origens — capacidades fundamentais (F-Q1..F-Q12)

## F-Q1 `{shared}` — Intrinsic thinking é característica arquitetural, não hiperparâmetro

**Conclusão:** Modelos `deepseek-r1:*` (e outros da classe *intrinsic-thinking*)
colapsam para prompt-echo ou geração degenerada quando `think=False`. O
pipeline de inferência assume tokens de thinking presentes.

**Implicação metodológica:** Catálogo de modelos deve classificar thinking em
`{none, toggle, intrinsic, graded}`. Controles experimentais só aplicam
`think=False` em categoria `toggle`.

**Evidência:** `deepseek-r1:7b` × 5 seeds: `think=False` → eco de prompt;
`think=None` → "Brasília". Determinístico.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q1](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q2 `{shared}` — Arquitetura multimodal degrada text-only em alguns modelos

**Conclusão:** `qwen3-vl:8b` apresenta timeouts patológicos (45s+) em prompts
text-only triviais, enquanto `qwen3:8b` (mesmo tamanho, sem vision) responde
em ~1.3s. `llama3.2-vision:11b` NÃO apresenta essa degradação — não é
universal entre modelos vision-augmented.

**Implicação metodológica:** Modelos multimodais devem ser validados
individualmente para uso text-only antes de entrarem em painéis de qualificação.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q2](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q3 `{shared}` — Ausência de viés PT vs EN em accuracy canônica

**Conclusão:** 5 top-performers × 7 perguntas × 2 idiomas (PT/EN) mostram
accuracy 100% idêntica. Latência PT inicial é artefato de cold-start, não
de idioma.

**Implicação metodológica:** Prompts TCF em PT são cientificamente
equivalentes a EN para fins de accuracy; a escolha de idioma é operacional.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q3](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q4 `{shared}` — Ambiguidade linguística em contagem lexical vs conteúdo

**Conclusão:** "Conte as palavras em 'A raposa marrom pula'" recebe 4
(lexical) de alguns modelos e 3 (conteúdo, exclui artigo) de outros. Ambas
interpretações são válidas.

**Implicação metodológica:** Scoring de questões de contagem em PT deve
aceitar tolerância `[N-1, N]` quando há artigos. Em TCF, prompts sobre
"linhas" precisam desambiguar "linhas físicas do formato" vs "linhas
lógicas de dados".

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q4](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q5 `{shared}` — Capacity floor existe abaixo de 1B parâmetros

**Conclusão:** `qwen3:0.6b` responde "Brasil" para "capital do Brasil" —
confunde entidade país/cidade. É limite de capacity, não de configuração.

**Implicação metodológica:** Modelos < 1B não devem entrar em painel
principal sem qualificação específica; reservados para benchmarks de
edge deployment.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q5](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q6 `{shared}` — Cold-start na primeira chamada PT

**Conclusão:** A primeira chamada em PT após troca de modelo/sessão custa
20-60s; chamadas subsequentes ficam em 2-8s.

**Implicação metodológica:** Medições de latência devem descartar primeira
chamada OU usar warmup prompt em PT antes da medição.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q6](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q7 `{shared}` — Catálogo de modelos modernos vs obsoletos

**Conclusão:** Famílias têm gerações sucessivas que tornam anteriores
redundantes (phi3 → phi4; qwen2.5 → qwen3; llama3.1 → llama3.2). Manter
versões antigas em teste principal polui ranking sem novo sinal.

**Implicação metodológica:** `qualified_models.json` deve excluir gerações
obsoletas; manter apenas em `obsolete_models.json` para ablação histórica.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q7](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q8 `{shared}` — Thinking consome budget de `num_predict`

**Conclusão:** Em modelos reasoning, `num_predict` limita **thinking +
response**, não apenas response. Budget insuficiente trunca a resposta
após thinking (aparentemente o modelo "falhou" mas na verdade o servidor
cortou na metade).

**Evidência:** `phi4:latest` em TCF L3 n=100 q_count: response TRUNCATED
(done_reason="length") com thinking_length=0 — thinking não aconteceu, mas
a resposta estava longa demais para o default num_predict.

**Implicação metodológica:**
1. Sempre instrumentar `thinking_length`, `done_reason`, `truncated` em
   todo record de experimento.
2. Budget explícito `num_predict=4096+` para modelos reasoning;
   `num_predict=8192+` se thinking_length observado passar de ~3500c.
3. Record truncado ≠ model failure — é **instrumentation failure** da parte
   do experimento.

**Referência:** implementado em `llm_eval/ollama_client.py::GenerateResult`
e `run_frontier_search.py::LLM_OPTIONS` (2026-04-21).

---

## F-Q9 `{shared}` — `keep_alive` em `options` é silenciosamente ignorado

**Conclusão:** Ollama trata `keep_alive` como campo top-level da payload.
Colocá-lo dentro de `options` gera warning no servidor e o valor é
descartado — modelos descarregam após default (5min).

**Implicação metodológica:** `keep_alive` viaja em `client.generate(...,
keep_alive="30m")`, nunca em `options={"keep_alive": ...}`.

**Referência:** fix em `llm_eval/ollama_client.py::_TOPLEVEL_KEYS`.

---

## F-Q10 `{shared}` — Non-convergent thinking em modelos 7B-reasoning (escopo narrow)

**Conclusão (escopo narrow):** `deepseek-r1:7b` em TCF L3 com perguntas de
contagem implícita apresenta thinking não-convergente (budget scaling
não-monotônico: 2121→31950→70052→1917 chars). Pattern específico à
combinação *modelo × tarefa × formato*; não generalizar.

**Caveat crítico:** Este achado é observação em escopo narrow (1 modelo ×
1 task domain × 2 perguntas × seed=42). Qualquer menção externa precisa
incluir essas limitações explicitamente.

**Implicação metodológica:** Reasoning models têm modo de falha
"thinking degenerado" distinto de "capacity floor" — ambos terminam em
resposta errada, mas representam problemas diferentes. Instrumentação
F-Q8 permite distinguir.

**Referência:** [`2026-04-21-thinking-non-convergence.md`](../research-notes/2026-04-21-thinking-non-convergence.md)

---

## F-Q11 `{shared}` — Determinismo CPU↔GPU não-verificado formalmente

**Conclusão:** Com `temperature=0, seed=42`, Ollama é empiricamente
determinístico dentro do mesmo backend. CPU↔GPU pode divergir em 1-2
tokens por conta de drift numérico de floating-point nas camadas
transformer, mas não há medição formal do impacto em accuracy de task.

**Implicação metodológica:** Records do mesmo combo gerados em backends
diferentes devem ser anotados (`compute_backend` field). Comparações
cross-backend precisam de replicação.

**Referência:** observado durante Phase 6 (CPU→GPU mid-run em
deepseek-r1:14b; 5 records cached de CPU mantidos após mudança).

---

## F-Q12 `{A}` — Aritmética sobre colunas com muitas linhas falha universalmente

**Conclusão:** 12 modelos locais (phi4 a gemma3:1b) têm 0% acurácia em
`sum()` e `avg()` sobre coluna numérica de 255 linhas em TCF L3.
Tarefas de retrieval (max, top) funcionam; aggregation não.

**Mecanismo hipotético:** O modelo precisa simultaneamente (a) expandir o
RLE mentalmente, (b) manter state de soma ao longo de 255 passos, (c)
formatar a resposta. Capacidade representacional combinada estoura em 7B-14B.

**Implicação metodológica:**
- Aggregation não é "failure point de modelo" — é **failure point de
  arquitetura cognitiva** de LLMs dessa classe.
- Resposta deve ser tool-calling ou program-of-thoughts (emitir código
  Python, executar externamente).
- Futuros experimentos TCF devem testar PoT como baseline de sucesso.

**Referência:** Phase 6 resultados (2026-04-21), `manifest.jsonl` phase=6.

---
