---
title: História do projeto TCF — origem, v0.0, v0.1, transição para v0.2
date: 2026-04-24
type: history
status: consolidado — substitui docs/archive/rascunhos, docs/archive/tickets_v01, docs/archive/legacy_results
---

# História do projeto TCF

Este documento consolida a trajetória do projeto desde o rascunho inicial
até a estrutura atual (v0.2 + série M). Substitui arquivos originalmente em
`docs/archive/rascunhos/`, `docs/archive/tickets_v01/` e
`docs/archive/legacy_results/` (removidos após consumo). As versões originais permanecem no git log.

---

## Origem (abril 2026, rascunho manual)

O projeto nasceu de um esboço em prosa sobre como comprimir tabelas relacionais
em texto de forma que uma LLM ainda pudesse interpretar. O primeiro formato
proposto manualmente era:

```
header:pessoas[nome]:produtos[nome]:vendas[qt,vl];1-*3*-2
str;3:ana;2:luiz
str;1:batata;2:maça;1:1;1:2
int;2:1;1:2;1:1;4
float[int,2];2:1.23;2.46;1.23;4.92
```

Notação: primeira linha descreve estrutura (tabelas e colunas); cada linha
seguinte indica tipo + valores com RLE textual `N:val` (N repetições de val).
Valores isolados = literais; `1:1` em coluna string = referência a índice da
coluna anterior; `.` para distinguir inteiro literal de índice.

As três perguntas-guia do rascunho original:
1. Esse formato confundiria uma LLM?
2. Existem dois formatos úteis (simples + elaborado)?
3. Separadores `,` `:` `;` são necessários ou uma "cara de CSV" funcionaria melhor?

A resposta final (v0.2) foi: (1) formato tem que ser legível sem regras
ocultas; (2) 4 níveis L0-L3 cobrem o espectro; (3) sintaxe Markdown-like com
`N*val` para RLE e colunas agrupadas por nome.

---

## Evolução por versão

### v0.0 — old_tokenizer (antes de TCF existir)

Primeira implementação era um tokenizador de CSV para formato textual
compacto. `encode.py`, `decode.py`, `vocab.py`, `schema.py`. Foco inicial
era compactação, não LLM-legibilidade. **Superseded por v0.1.**

### v0.1 — encoder progressivo (março-abril 2026)

Primeira versão com nome "TCF". Características:
- Encoder em 7 configurações de variantes (`P04-encoder-variants`)
- Dataset sintético minúsculo (41 vendas, `consolidated.json`)
- 4 níveis de encoding: raw_float, int_scaled, bins_16, etc.
- Ground truth hardcoded em runner (`P03` parcial)
- Sem STATS hints; sem compressão RLE

**Superseded por v0.2** em ~abril 2026 por três motivos:
1. Formato não escalava além de ~100 linhas (prompt explodia)
2. Sem STATS, modelos 7B falhavam em aritmética simples
3. Estrutura de tickets H01-H10 virou obsoleta ao reescrever encoder

### v0.2 — atual (abril 2026)

Encoder L0-L3 com RLE textual + STATS hints + multi-tabela + FK explícito.
Cobertura experimental: M1-M8b (810+ combos em schema carrier).
Ver [components/1-tcf-core.md](components/1-tcf-core.md) para detalhes.

---

## Tickets v0.1 — resumo científico

22 tickets na v0.1: H-series (hipóteses científicas), P-series (infraestrutura),
T-series (tecnologia/especificação). Status final antes da transição v0.2:

### Hipóteses fechadas

| Ticket | Hipótese | Resultado |
|--------|----------|-----------|
| H01 | `decode(encode(csv)) == csv` para toda célula | **CLOSED** — Phase 0 gate: 7/7 configs reversíveis, 151 testes unitários |

### Hipóteses abertas (tornaram-se obsoletas com v0.2)

| Ticket | Hipótese | Destino na v0.2 |
|--------|----------|-----------------|
| H02 | Formato afeta accuracy (main effect) | Virou Etapa 1 + M4 (F-Q17) |
| H03 | Decomposição formato × aritmética | Virou diagnostic_3layer + M5 (F-Q12, F-Q18) |
| H04 | Variantes de encoding numérico | Abandonada; L0-L3 cobrem o espaço |
| H05 | Sort mode: agregados vs filtros (2×2) | Absorvida em STATS hints (F-Q3..F-Q9) |
| H06 | Representação FK e filtros | Virou F-Q17 (JSON vs CSV vs TCF), F-Q20 |
| H07 | Tamanho modelo × formato | Virou M0 qualification + model-ranking |
| H08 | Família modelo × formato | Virou M0 (F-Q2, F-Q5, F-Q7) |
| H09 | Fronteira Pareto: accuracy × tokens | Virou frontier_search |
| H10 | Escalabilidade accuracy × chunk size | Virou scale_progression |

### Infraestrutura

| Ticket | Escopo | Destino |
|--------|--------|---------|
| P01-P02 | Token count, response parser | Integrados em `llm_eval/ollama_client.py` |
| P03 | Ground truth | Reescrito em `llm_eval/ground_truth.py` |
| **P04** | Encoder variants (3 numeric × 4 FK × 2 sorted = 24) | **CLOSED** — conceito absorvido em EncodeConfig v0.2 |
| P05 | Banco de perguntas | Absorvido em M-series (7+3+4 question types) |
| P06-P07 | Matrix runner + análise | Virou `experiments/eval/run_m*.py` + `analyze_results.py` |

### Tecnologia

Tickets T01-T06 (spec do formato, encoding numérico/FK, arquitetura, compressão)
foram integralmente substituídos pela v0.2. Spec atual em
[article/03-tcf-format.md](article/03-tcf-format.md) e
[components/1-tcf-core.md](components/1-tcf-core.md).

---

## Experimentos pré-M0 (novembro 2025 — março 2026)

Antes da estruturação M-series, rodaram-se avaliações exploratórias em
`docs/archive/legacy_results/` (removido). Dataset: `vendas` do `consolidated.json`
(41 registros, 2 chunks de 40+1 linhas). Relatório inicial datado de
**21/11/2025**.

### Formatos testados

| Formato | Descrição | Prompt médio (40 linhas) |
|---------|-----------|-------------------------|
| CSV | Tabular clássico com header | ~2 000 chars |
| JSONL | 1 JSON por linha | ~7 600 chars |
| TOON (token_object) | JSON único com `columns` + `rows` matrix | intermediário |

**TOON:** formato que se propunha compactar JSON evitando repetição de chaves,
usando matriz de valores. Foi descartado porque: (a) não tem encoder real,
apenas stub em formats.py legado; (b) LLMs interpretavam inconsistentemente;
(c) v0.2 L2/L3 dominam em compressão real.

### Modelos testados pré-M0

| Modelo | Destino | Motivo |
|--------|---------|--------|
| gemma3:12b | Avaliado extensivamente (9 runs CSV/JSONL/TOON/TOKEN) | Usado como baseline v0.1 |
| deepseek-r1:latest, deepseek-r1:8b (+toon) | **Descartado** | Thinking intrínseco (F-Q1) |
| gpt-oss:latest | Descartado | Substituído por qwen3 em M0 |
| granite3.1-dense:latest | Descartado | Performance fraca em M0 qualification |
| llama3.2 (+toon) | Descartado | Substituído por phi4 |
| phi3:latest | Descartado | Obsoleto (F-Q7: manter só geração mais recente) |
| qwen25-coder (+toon) | Evoluiu para qwen2.5-coder:7b em M3+ | Versão atual ativa |
| smollm2 (+toon), smollm2:latest | Descartado | Abaixo de capacity floor (F-Q5) |

### Sobreviventes em M-series

Três modelos finais após qualificação M0 (documentada em `research-notes/
2026-04-20-qualification-findings.md`):
- qwen3:14b
- phi4:latest
- qwen2.5-coder:7b

Ver [methodology/model-ranking.md](methodology/model-ranking.md) para análise
completa dos sobreviventes.

---

## Arquivos removidos após consumo

Os seguintes arquivos/pastas existiram no repositório até 2026-04-24 e foram
removidos após este documento ser consolidado. Permanecem acessíveis em
`git log` se reprodução exata for necessária:

- `archive/misc/` — contaminação de outro projeto (STFT imagens, Streamlit app)
- `archive/old_tokenizer/` — v0.0 tokenizer (precursor)
- `archive/output_manual/` — artefatos de teste manuais
- `archive/rascunhos/ideia_prototipo_manual.md` — origem consolidada na seção 1 deste doc
- `archive/tickets_v01/` — 22 tickets consolidados na seção 3 deste doc
- `archive/legacy_results/` — resultados pré-M0 consolidados na seção 4 deste doc

Mantidos em `docs/archive/` (2026-04-24 movido de `archive/` raiz):
- `docs/archive/article_v01/` — capítulos v0.1 do paper (5 links vivos em docs/article)
- `docs/archive/v01/` — código v0.1 (reprodutibilidade dos achados v0.1)
