---
title: Comparacao com formatos concorrentes (TOON e outros)
type: research
status: OPEN
priority: MEDIUM
---

# Comparacao com Formatos Concorrentes

## Objetivo

Mapear todos os formatos existentes para serializacao de dados tabulares
para LLMs, comparar com TCF de forma honesta, e incorporar no artigo.

## Formatos a comparar

| Formato | Tipo | Origem | Status |
|---------|------|--------|--------|
| CSV | Row, standard | Universal | Baseline (implementado) |
| JSONL | Row, self-describing | Universal | Baseline (implementado) |
| Markdown Table | Row, visual | Universal | Implementado em formats.py |
| TOON | Row, header tipado | github.com/toon-format/toon | Implementado em formats.py |
| TCF | Column, RLE | Este projeto | Core |

## O que ja temos

1. **Implementacao de TOON** em `experiments/eval/llm_eval/formats.py`
2. **Tamanhos comparados** (41 vendas): CSV 949, TOON 1129, TCF L0 870, TCF L2 714, JSONL 2383
3. **Accuracy com LLMs** para CSV, JSONL, TCF L0/L2 (G21, Etapa 1+2)
4. **FALTA:** accuracy de TOON e MD Table com LLMs

## Tarefas

| ID | Titulo | Status |
|----|--------|--------|
| P-CF-01 | Pesquisar papers/repos do TOON | OPEN |
| P-CF-02 | Pesquisar outros formatos para LLMs (2023-2026) | OPEN |
| P-CF-03 | Coletar resultados publicados de Sui et al. 2024 | OPEN |
| P-CF-04 | Rodar TOON e MD Table no mesmo benchmark (Etapa 2 data) | OPEN |
| P-CF-05 | Comparativo honesto: tabela com metricas iguais | OPEN |
| P-CF-06 | Documentar no artigo (cap 2 related work + appendix D) | OPEN |

## Abordagem

1. Se os concorrentes ja tem benchmarks publicados:
   - Usar os resultados deles diretamente (referenciar)
   - Replicar com nosso dataset para comparacao direta

2. Se nao tem benchmarks:
   - Rodar com nosso pipeline (mesmos modelos, dados, perguntas)
   - Documentar condicoes identicas

3. Comparar em 3 eixos:
   - **Compressao** (bytes por formato)
   - **Accuracy LLM** (mesmas perguntas)
   - **Escalabilidade** (como se comporta com 200+ rows)

## Resultado da pesquisa (2026-04-09)

**TOON:** Projeto obscuro (github.com/toon-format/toon), sem paper academico,
sem pip package, sem adocao relevante. Formato: JSON com `columns` + `rows` matrix.
Row-oriented, sem compressao. Nos nossos testes legados: 50% accuracy gemma3 (= JSONL).

**Sui et al. (2024):** Testaram CSV, JSON, Markdown, HTML, NL. Todos row-oriented.
Markdown e HTML performaram melhor. Diferenca < 10-15pp. Modelo importa mais que formato.
**Nenhum formato columnar testado.**

**Hegselmann (2023):** Templates de texto para classificacao. Nenhum formato novo proposto.

**Conclusao:** TCF e o **primeiro formato columnar com compressao para LLMs**.
Nao ha concorrente direto. A comparacao mais honesta e:
- TCF vs CSV (row baseline, familiar)
- TCF vs JSONL (row, self-describing)
- TCF vs Markdown Table (row, familiar, visual)
- TCF vs TOON (row, header tipado, nicho)

## Hipoteses

- TOON e JSON compacto — accuracy provavelmente similar a JSONL
- MD Table familiar para LLMs — pode performar melhor que CSV em escala
- **TCF e o unico com compressao** — posicionamento forte no paper
- A comparacao honesta mostra que TCF traz algo novo (columnar + RLE),
  nao que "e melhor em tudo" — pode perder em familiaridade

## Referencias adicionais (2025-2026)

- **TableEval (EMNLP 2025)** — real-world benchmark for complex table QA.
  Verificar se testam formatos diferentes ou so NL.
- **ST-Raptor (SIGMOD 2025)** — LLM-powered semi-structured table QA.
  Usa SQL hibrido, nao testa formatos de serializacao.
- **Sui et al. 2024 detalhe:** self-augmentation (explicar formato ao modelo)
  melhorou 3.26% — relevante para nosso E-prompt-presentation (variavel 2:
  header explicativo).
