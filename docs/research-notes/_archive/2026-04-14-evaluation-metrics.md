# Pesquisa 2026-04-14: Metricas de Avaliacao para Numerical QA

Motivacao: nosso scoring binario (2% tolerancia = correct/fail) esconde
informacao critica. Modelos que respondem 37.46 (gt=38.64, erro 3%)
aparecem como "0%" quando na verdade estao "quase certos".

---

## 1. O que a literatura consagrada usa

### 1.1 WikiTableQuestions (WTQ) — Pasupat & Liang 2015

**Denotation accuracy** com 3 tipos de valor:
- **String:** exact match (case-insensitive, whitespace normalized)
- **Number:** `|a - b| < 1e-6` (muito rigido, quase exact match)
- **Date:** match por fields (year, month, day)

**Problema:** WTQ e MUITO rigido para numericos. 1e-6 de tolerancia
nao e pratico para LLMs que estimam em vez de calcular exatamente.

Fonte: [github.com/ppasupat/WikiTableQuestions/evaluator.py](https://github.com/ppasupat/WikiTableQuestions/blob/master/evaluator.py)

### 1.2 TableBench (Wu et al. 2024)

Usa multiplas metricas por categoria:
- **ecr@1 (execution correctness rate):** codigo Python roda sem erro?
- **ROUGE-L:** overlap de n-gramas com resposta de referencia
- **pass@1:** resultado do codigo passa no test case?

**Nao tem metrica de tolerancia numerica** — usa ROUGE-L que e textual.

Fonte: [tablebench.github.io](https://tablebench.github.io/)

### 1.3 TAT-QA (Zhu et al. 2021) — Financial QA

**Execution accuracy (EA):** resposta exata do programa gerado
**F1 score:** overlap de tokens entre resposta e ground truth

**Para numericos:** tolerancia nao documentada explicitamente,
mas a comunidade usa 1-5% tipicamente.

Fonte: [nextplusplus.github.io/TAT-QA](https://nextplusplus.github.io/TAT-QA/)

### 1.4 FinQA (Chen et al. 2021) — Financial Numerical Reasoning

**Execution accuracy:** resultado do programa == ground truth
**Program accuracy:** programa gerado e identico ao gold program

Fonte: [sites.cs.ucsb.edu/~william/papers/FinQA.pdf](https://sites.cs.ucsb.edu/~william/papers/FinQA.pdf)

### 1.5 SciTaRC (2025) — Scientific Tabular Reasoning

**Taxonomia de 4 classes de erro:**
1. **Comprehension:** entendeu errado a pergunta
2. **Localization:** pegou dados errados da tabela
3. **Calculation:** operacao matematica errada
4. **Memory:** perdeu resultado intermediario

"Each incorrect prediction is assigned exactly one primary error type
based on the earliest point in the reasoning chain at which the output
becomes unrecoverable."

Fonte: [arxiv 2603.08910](https://arxiv.org/html/2603.08910)

### 1.6 LLM Evaluation Best Practices (Microsoft, W&B, 2025)

**Strict accuracy (SaCC):** resposta exatamente correta
**Lenient accuracy (LaCC):** resposta parcialmente correta
(top-K predictions contem a resposta gold)
**MRR (Mean Reciprocal Rank):** posicao da resposta correta no ranking

"No single metric is a silver bullet — create a balanced scorecard."

Fonte: [medium.com/data-science-at-microsoft](https://medium.com/data-science-at-microsoft/evaluating-llm-systems-metrics-challenges-and-best-practices-664ac25be7e5)

---

## 2. Proposta de framework de metricas para TCF

Baseado na literatura, nosso framework combina:
- **Execution tiers** (do SciTaRC — separar PORQUE falhou)
- **Tolerance tiers** (da pratica financeira — quao perto chegou)
- **Separation principle** — erros tecnicos separados de erros de raciocinio

### 2.1 Execution Status (separar funcionou de nao-funcionou)

| Status | Descricao | Criterio |
|--------|-----------|----------|
| **RESPONDED** | Modelo retornou resposta parseavel | prompt_tokens > 0 AND response nao vazio |
| **TIMEOUT** | Modelo excedeu tempo | prompt_tokens = 0 OR latency > threshold |
| **ERROR** | Erro de rede/modelo | exception type |
| **EMPTY** | Resposta vazia | response = "" |
| **UNPARSEABLE** | Resposta sem numero para pergunta numerica | nenhum numero encontrado |

**Metricas derivadas:**
- **Response Rate:** % de combos que retornaram resposta parseavel
- **Error Rate:** % de combos com timeout/error/empty

### 2.2 Accuracy Tiers (SOMENTE sobre combos que RESPONDED)

Para perguntas **numericas** (sum, avg, max, min, count):

| Tier | Nome | Criterio | Analogia |
|------|------|----------|---------|
| **T1** | Exact | relative error <= 1% | WTQ/FinQA execution accuracy |
| **T2** | Precise | relative error <= 5% | Financial "close enough" |
| **T3** | Approximate | relative error <= 15% | Scientific order of magnitude |
| **T4** | Directional | relative error <= 50% | "Acertou a direcao" |
| **T5** | Wrong | relative error > 50% | Completamente errado |

**Relative error** = `|predicted - expected| / |expected|`

Para **count** (inteiro): same tiers mas com `|pred - exp| / exp`.
Para **string** (argmax, top-K): exact substring match (binario).
Para **pairs** (group-by): % de pares mencionados corretamente.

**Metricas derivadas:**
- **Acc@T1:** % de RESPONDED que sao T1 (exact)
- **Acc@T2:** % de RESPONDED que sao T1 ou T2 (precise)
- **Acc@T3:** % de RESPONDED que sao T1-T3 (approximate)
- **MAE:** Mean Absolute Error (sobre RESPONDED numericos)
- **MAPE:** Mean Absolute Percentage Error
- **Median Relative Error**

### 2.3 Error Taxonomy (SOMENTE sobre combos que RESPONDED mas erraram)

Baseado no SciTaRC 4-class taxonomy, adaptado:

| Classe | Descricao | Como detectar |
|--------|-----------|---------------|
| **Comprehension** | Entendeu errado a pergunta | Respondeu tipo errado (string para numeric) |
| **Localization** | Pegou dados errados | Numero plausivel mas de outra coluna/tabela |
| **Calculation** | Operacao errada | Numero na faixa certa mas resultado errado |
| **Format** | Nao entendeu o formato | Mesmo resultado em todos os formatos (nao e do formato) |

### 2.4 Format Comparison Metrics

Para comparar TCF vs CSV vs TOON:

| Metrica | O que mede |
|---------|-----------|
| **Acc@T2 per format** | Qual formato da mais respostas "precise" |
| **Response Rate per format** | Qual formato causa menos crashes |
| **MAPE per format** | Qual formato da erros menores em media |
| **Token efficiency** | Acc@T2 / prompt_tokens (accuracy por token) |
| **Latency efficiency** | Acc@T2 / latency_s (accuracy por segundo) |

**Token efficiency** e a metrica que TOON alega vencer — agora podemos
medir honestamente com tokens reais.

---

## 3. Relacao com tickets existentes

| Conceito | Ticket |
|----------|--------|
| M-stability-testing (N>=3 runs) | frozen/ — aplicavel apos definir metricas |
| M-tokenizer-validation (tokens reais) | frozen/ — ja estamos gravando prompt_tokens |
| E-token-count (tiktoken offline) | frozen/ — complementar ao prompt_tokens real |
| E-stats-ablation (F90-F94) | open/ — repetir com novas metricas em dados canonicos |

---

## 4. Implementacao proposta

Script: `scripts/analyze_llm_results.py`

Reads `Z:/tcf-data/benchmarks/llm-accuracy-canonical.jsonl` e produz:
1. Execution status breakdown (response rate, error rate)
2. Accuracy tiers (Acc@T1..T5) por modelo x formato
3. MAE/MAPE por modelo x formato (so sobre RESPONDED)
4. Error taxonomy (sampled)
5. Token efficiency (Acc@T2 / avg_tokens)
6. Salva resultados em JSON para graficos

**Nao re-roda nada** — analise pos-hoc sobre dados ja coletados.

---

## 5. Referencias

### Table QA Benchmarks
- [WikiTableQuestions evaluator](https://github.com/ppasupat/WikiTableQuestions/blob/master/evaluator.py)
- [TableBench](https://tablebench.github.io/) (AAAI 2024)
- [TAT-QA](https://nextplusplus.github.io/TAT-QA/) (ACL 2021)
- [FinQA](https://sites.cs.ucsb.edu/~william/papers/FinQA.pdf) (EMNLP 2021)
- [SciTaRC](https://arxiv.org/html/2603.08910) (2025)

### Error Taxonomy
- SciTaRC 4-class: Comprehension, Localization, Calculation, Memory

### LLM Evaluation Best Practices
- [Microsoft — Evaluating LLM Systems](https://medium.com/data-science-at-microsoft/evaluating-llm-systems-metrics-challenges-and-best-practices-664ac25be7e5)
- [W&B — LLM Evaluation](https://wandb.ai/onlineinference/genai-research/reports/LLM-evaluation-Metrics-frameworks-and-best-practices)
- [Confident AI — LLM Evaluation Metrics](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation)
- [arxiv 2404.09135 — Unveiling LLM Evaluation](https://arxiv.org/html/2404.09135v1)

### Statistical Error Metrics
- MAE (Mean Absolute Error)
- MAPE (Mean Absolute Percentage Error)
- Relative Error = |pred - exp| / |exp|
- NIST accuracy assessment: [tsapps.nist.gov/publication](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=150040)
