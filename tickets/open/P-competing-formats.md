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

## Resultado da pesquisa — ATUALIZADO 2026-04-10

### TOON evoluiu significativamente desde outubro 2024

**Nao e mais "obscuro".** Pesquisa de 2026-04-10 revelou:

- **Papers arxiv:**
  - [2603.03306](https://arxiv.org/abs/2603.03306) (fev 2026) — "TOON vs JSON: Plain and Constrained Decoding"
  - [2601.12014](https://arxiv.org/abs/2601.12014) (jan 2026) — "Are LLMs Ready for TOON?"
- **Projeto ativo:** [github.com/toon-format/toon](https://github.com/toon-format/toon)
- **Site oficial:** [toonformat.dev](https://toonformat.dev/guide/benchmarks)
- **SDK TypeScript** + site com benchmarks
- **Blogs tecnicos:** LogRocket, Medium, dev.to (cobertura ampla)

### Benchmarks oficiais do TOON (do projeto)

- **54% reducao media de tokens** vs JSON (benchmarks em 50 datasets)
- **76.4% accuracy** (vs JSON 75.0%)
- **27.7 acc%/1K tokens** (vs JSON 16.4) — melhor ratio
- **Ate 73.4% reducao** em casos otimos (tabular, surveys)

### Pontos fracos conhecidos do TOON (arxiv independente)

- **Colapsa em estruturas nao-alinhadas:** 0% accuracy em casos de hierarquias
  profundas (precisa retries, final 48.6%)
- **"Prompt tax":** instrucao explicativa do TOON consome tokens
  em contextos curtos, reduzindo a economia
- **Sem testes em wide tables (>100 colunas)**
- **So benchmarks do proprio projeto** — validacao independente limitada
- **Sem compressao textual interna** (RLE, dict, sort)
- **Sem hints meta-cognitivos** (nada equivalente aos STATS)

### Oportunidades concretas para TCF vs TOON

| Dimensao | TOON | TCF | Oportunidade? |
|----------|------|-----|---------------|
| Token efficiency | -54% vs JSON | ? (medir — ver E-token-count) | INCERTO |
| Accuracy | 76% | 88% (gemma3, com STATS) | TCF provavelmente melhor |
| Escala (rows) | Benchmarks ~100-500 rows | Testamos ate 5000 | TCF forca em grande |
| Repeticao de dados | Sem compressao | RLE + dict + sort | TCF para dados repetitivos |
| Wide tables (>100 cols) | Nao testado | Nao testado | Ambos a investigar |
| Hints meta-cognitivos | Nao tem | STATS (F81-F94) | **TCF unico com isso** |
| Parsing hierarquias | Bom (se alinhado) | Nao aplica (flat) | TOON para nested |
| Peer review | Arxiv | Em preparacao | Empate |

**Conclusao:** TOON e forte em tokens e accuracy mas **nao** tem RLE,
nao tem STATS, e ainda nao foi testado em escala ou wide tables.
Essas sao as brechas reais do TCF.

## Sui et al. (2024) — Table Meets LLM

Testaram CSV, JSON, Markdown, HTML, NL. Todos row-oriented.
Markdown e HTML performaram melhor. Diferenca < 10-15pp. Modelo importa
mais que formato.
**Nenhum formato columnar testado.** Nenhum formato com hints embutidos.

## Posicionamento honesto do TCF

**NAO podemos mais dizer:**
- ~~"TCF e o primeiro formato columnar textual para LLMs"~~ (provavel, mas validar)
- ~~"TOON e um projeto obscuro"~~ (falso — tem papers, benchmarks, adocao)
- ~~"TCF e mais eficiente em tokens que todos"~~ (precisa medir vs TOON)

**PODEMOS dizer (com evidencia):**
- "TCF e o primeiro formato a combinar colunar + RLE + hints meta-cognitivos"
- "TCF tem melhor accuracy que TOON em dados >500 rows" (se confirmado)
- "TCF e o unico formato textual com STATS embutidos que compensam limitacoes
  aritmeticas dos LLMs"
- "TCF + gzip tem melhor ratio que JSONL + gzip (29% menor em 5000 rows)"
  (F70-F73 ja comprovado)

## Hipoteses TESTAVEIS (nova redacao)

**H-vs-toon-1:** TCF L0 com STATS > TOON em accuracy para agregacoes
(sum, avg, count), porque so TCF tem hints.

**H-vs-toon-2:** TCF L2/L3 > TOON em compressao apos gzip para dados
com alta repeticao (retail, logs).

**H-vs-toon-3:** TCF escala melhor que TOON — accuracy mantida em 500-1000 rows
enquanto TOON degrada (precisa verificar com benchmarks reais).

**H-vs-toon-4:** Para estruturas nao-tabulares (nested, wide), TOON
ou JSON sao melhores. TCF e especialista em tabular flat, nao generalista.

## Tarefas atualizadas

- [x] Pesquisar papers/repos do TOON (feito 2026-04-10)
- [x] Pesquisar outros formatos para LLMs 2023-2026 (feito)
- [ ] Implementar encoder TOON real (o stub atual nao e real)
- [ ] Rodar Etapa 2 com TOON incluido (12 modelos × 8 questoes)
- [ ] Comparar TCF+STATS vs TOON em accuracy de agregacoes (H-vs-toon-1)
- [ ] Comparar TCF+gzip vs TOON+gzip em compressao (H-vs-toon-2)
- [ ] Comparar escalabilidade (H-vs-toon-3)
- [ ] Documentar honestamente no paper: onde TCF > TOON, onde TOON > TCF

## Referencias adicionais (2025-2026)

- **TableEval (EMNLP 2025)** — real-world benchmark for complex table QA.
  Verificar se testam formatos diferentes ou so NL.
- **ST-Raptor (SIGMOD 2025)** — LLM-powered semi-structured table QA.
  Usa SQL hibrido, nao testa formatos de serializacao.
- **Sui et al. 2024 detalhe:** self-augmentation (explicar formato ao modelo)
  melhorou 3.26% — relevante para nosso E-prompt-presentation (variavel 2:
  header explicativo).
