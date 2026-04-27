---
title: Literatura — formatos tabulares para LLM (revisão 2024-2026)
date: 2026-04-25
type: research-note
status: REFERÊNCIA — informa decisões de M-series futuras
---

# Formatos tabulares para LLM — estado da arte e nossas lacunas

## Motivação

Antes de fazer V1-V5 (validação em escala — ver
[architecture/assembly-overview.md](../architecture/assembly-overview.md) Anexo E),
revisar o que outros publicaram sobre formatos textuais para LLMs sobre dados
tabulares. Identificar gaps que nosso paper pode preencher.

## Trabalhos sólidos (peer-reviewed)

### Sui et al. 2024 — "Table Meets LLM" (WSDM)
**URL:** [arxiv.org/abs/2305.13062](https://arxiv.org/abs/2305.13062)

Comparou 6 formatos (CSV, JSON, XML, Markdown, HTML, XLSX) em 5 tasks:
TabFact, HybridQA, SQA, Feverous, ToTTo.

Achados:
- **HTML + role prompting + schema explanations = 65.43%** (vencedor)
- 20% de spread entre formatos
- **Order matters:** -20% se markers de partição são removidos
- Schema explanations valem mais que escolha do formato

Implicação para nós: alinha com F-Q15 (fewshot mandatório) e F-Q9
(STATS hints). Confirma que **anotação semântica > formato puro**.

### TabLLM — Hegselmann et al. 2023 (PMLR)
**URL:** [proceedings.mlr.press/v206/hegselmann23a](https://proceedings.mlr.press/v206/hegselmann23a/hegselmann23a.pdf)

Few-shot tabular classification. 9 variantes de serialização.

Achado: **List Template** ("The X is Y") supera formatos elaborados.
LLM-generated serializations alucinam.

Implicação: simplicidade textual ganha em few-shot. Nosso TCF L0/L2
está no espírito disso (texto direto, não estrutura JSON aninhada).

### TOON paper — 2026 (arxiv:2603.03306)

**Único peer-reviewed sobre TOON.**

Achados:
- TOON: **30-60% redução de tokens** vs JSON (claim toolmaker)
- Validação acadêmica: "no clear winner" — "prompt tax" erode ganhos
  em contextos curtos
- Plain JSON vence em accuracy (~70%+)
- Sem benchmarks de QA tabular — só structured generation

**Lacuna crítica:** TOON nunca foi testado em tarefa de QA sobre tabela.

### ONTO — 2026 (arxiv:2604.17512)

Formato columnar acadêmico ("schema-once, data-many"). Claim 46-50%
redução tokens vs JSON. Sem benchmarks downstream.

Implicação: ONTO é "primo" do TCF (columnar). Vale comparação direta
em V2 (compressão classics).

## Comparações industriais (não-peer-reviewed mas úteis)

### Improving Agents 2025 — 11 formatos

**URL:** [improvingagents.com/blog/best-input-data-format-for-llms](https://www.improvingagents.com/blog/best-input-data-format-for-llms/)

Testou GPT-4.1-nano em 11 formatos:

| Formato | Accuracy |
|---------|----------|
| **Markdown-KV** | **60.7%** |
| XML | 56.0% |
| INI | 55.7% |
| YAML | 54.7% |
| HTML | 53.6% |
| JSONL | 45.0% |
| **CSV** | **44.3%** |
| Pipe-Delimited | 41.1% |

**Markdown-KV venceu CSV por 16.4pp.** Um achado prático grande que
não testamos no projeto.

### Surveys gerais

- **Survey 2024** (arxiv:2402.17944) — LLMs em tabular data, geral
- **Survey 2025** (arxiv:2508.00217) — tabular understanding, mais recente
  - Insight: format-performance é **model-dependent** (mesmo formato,
    modelos diferentes têm performance diferente)
  - Metadata aumenta recall em ~0.42pp

## O que testamos vs o que falta testar

| Formato | Testamos em Linha A? | Testamos em Linha B? | Literatura recomenda? |
|---------|---------------------|---------------------|----------------------|
| CSV | ✅ (etapa 1+M4) | ✅ (M4) | Baseline; Sui 2024 mostra que perde para HTML |
| JSONL | ✅ (etapa 1+M4) | ✅ (M4) | TabLLM: simples bate elaborado |
| **TOON** | ✅ (canonical Adult) | ❌ **NÃO** | Sem benchmarks QA — gap! |
| **HTML** | ❌ | ❌ | Sui 2024 vencedor com explanations |
| **Markdown-KV** | ❌ | ❌ | Improving Agents 2025: +16pp vs CSV |
| **YAML** | ❌ | ❌ | Improving Agents: +10pp vs CSV |
| **XML** | ❌ | ❌ | Improving Agents: +12pp vs CSV |
| **ONTO** | ❌ | ❌ | Columnar peer-reviewed; comparação natural com TCF |
| TCF L0-L3 | ✅ (etapa 1) | ✅ (M-series) | Nosso |

## Gaps que abrem espaço para o paper

### Gap 1: TOON em Linha B
Nenhum paper testou TOON como schema carrier + SQL. Nosso projeto pode
ser o primeiro. Hipótese: TOON terá accuracy similar ao TCF (ambos
columnar) mas perderá em compressão (TOON ≈ CSV size; TCF L3 = 25-38%
de CSV).

### Gap 2: Markdown-KV em Linha B
Improving Agents mostra +16pp em GPT-4.1-nano para Linha A. Em Linha B
(schema carrier), a diferença pode desaparecer (já que SQL gerado
executa exato em SQLite). Mas se a diferença persistir, é finding forte.

### Gap 3: HTML com schema explanations em Linha B
Sui 2024 venceu com HTML + explanations + role prompting. Nosso fewshot
+ STATS é equivalente conceitual. Comparação direta seria útil.

### Gap 4: ONTO vs TCF
Único concorrente columnar peer-reviewed. Comparação cara-a-cara em V2
é cientificamente honesta.

### Gap 5: Notação de grafo (DOT/Mermaid)
**Zero papers.** Anexo E (M10 futuro) preenche.

## Implicações para os experimentos futuros

### Para V1 (replicação em escala) — sem mudança
Continuar com TCF L0-L3 + CSV + JSON.

### Para V2 (compressão classics) — adicionar formatos
- **Adicionar:** Markdown-KV, YAML, HTML, ONTO, TOON (já temos writer)
- **Métricas:** raw bytes, gzip, brotli, zstd, tokens, accuracy LLM em Linha B
- Cobre sistematicamente o que Improving Agents fez (Linha A) mas em Linha B (nosso paradigma)

### Para V3 (notação schema) — sem mudança
DOT/Mermaid são originais nossos.

### Para V4 (modelos comerciais) — sem mudança
Adicionar mais formatos seria custoso em $$.

## Pontos de honestidade científica

1. **Nossos resultados Linha A do TOON** (Adult, 5 modelos, 11% accuracy
   média) são **inválidos para conclusões sobre TOON** — todos os formatos
   foram <15%; o teto era F-Q12 (capacity), não formato. Não citar como
   "TOON falha" no paper.

2. **TOON em Linha B é experiment limpo** — TCF e TOON ambos columnar;
   dificuldade da query é igual; LLM gera SQL no mesmo executor. Comparação
   científica honesta.

3. **Markdown-KV +16pp claim** vem de **um único paper não-peer-reviewed**
   com **um único modelo** (GPT-4.1-nano). Replicar com modelos locais é
   contribuição. Pode dar resultado diferente.

## Próximos passos práticos

Curto prazo (no Tier 1 de Anexo A):
- Adicionar nota no README sobre formatos testados e em quais linhas
- Cookbook com TOON entre os formatos exemplificados (já temos writer)

Médio prazo (V2):
- Implementar Markdown-KV writer (~50 linhas em `scripts/writers/`)
- Implementar HTML table writer (idem)
- Adicionar TOON ao M-series schema-carrier mode
- Comparar tudo em escala canonical

## Referências

- Sui 2024: https://arxiv.org/abs/2305.13062
- TabLLM 2023: https://proceedings.mlr.press/v206/hegselmann23a/hegselmann23a.pdf
- TOON 2026: https://arxiv.org/abs/2603.03306
- ONTO 2026: https://arxiv.org/html/2604.17512
- Survey 2024: https://arxiv.org/html/2402.17944v2
- Survey 2025: https://arxiv.org/html/2508.00217v1
- Improving Agents 2025: https://improvingagents.com/blog/best-input-data-format-for-llms/
