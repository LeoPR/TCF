# TCF — Tickets de Pesquisa e Implementacao

**Projeto:** Textual Columnar Format — encoder/decoder compacto para LLMs.
**Objetivo:** Paper cientifico sobre serializacao tabular para raciocinio de LLMs.

## Estrutura

```
tickets/
  README.md        Este arquivo — indice ordenado por prioridade
  open/            Tickets ativos da fase atual
  frozen/          Tickets congelados (futuro trabalho)
  closed/          Tickets concluidos + findings
```

## Prefixos de tipo

- `NN-` Numero de ordem/prioridade (ex: `01-`, `02-`)
- `M-` Meta-ticket (guia de fase que orquestra sub-tickets)
- `T-` Task (implementacao concreta)
- `H-` Hypothesis (algo a comprovar/refutar)
- `E-` Experiment (teste com dados/modelos)
- `P-` Pesquisa (investigacao)
- `R-` Resultado/finding

---

## FASE ATUAL: 1 — Setup de Datasets Canonicos

**Motivacao (2026-04-10):** voltamos a prancheta. Antes de fazer qualquer
experimento com formato, precisamos de **base de dados solida**. Nossos
experimentos anteriores usaram `retail_sales` sintetico com nomes
minimalistas (Ana, Bruno, Caneta), o que impede comparacao com literatura.

**Decidido:** comecar com 2 datasets canonicos:
1. **TPC-H SF=0.01** (padrao da industria desde 1999, schema relacional)
2. **Adult Census** (UCI ML, dados demograficos reais)

Outros ~18 datasets pesquisados estao documentados em
[docs/research-notes/2026-04-10-canonical-datasets.md](../docs/research-notes/2026-04-10-canonical-datasets.md)
como backlog futuro.

## Open (13) — ordem de execucao

### Meta-ticket

| Prioridade | Ticket | Tipo | Descricao |
|-----------|--------|------|-----------|
| 0 | [01-M-datasets-setup](open/01-M-datasets-setup.md) | meta | **Guia da Fase 1** |

### Sub-tickets (ordem sequencial)

| Prioridade | Ticket | Tipo | Descricao |
|-----------|--------|------|-----------|
| 1 | [02-T-datasets-structure](open/02-T-datasets-structure.md) | task | Criar estrutura de pastas |
| 2 | [03-T-datasets-deps](open/03-T-datasets-deps.md) | task | Dependencias opcionais (duckdb, sklearn) |
| 3 | [04-T-datasets-tpch](open/04-T-datasets-tpch.md) | task | Download TPC-H via DuckDB |
| 4 | [05-T-datasets-adult](open/05-T-datasets-adult.md) | task | Download Adult via sklearn |
| 5 | [06-T-datasets-sqlite](open/06-T-datasets-sqlite.md) | task | SQLite hub com tipos/PK/FK |
| 6 | [07-T-datasets-quality](open/07-T-datasets-quality.md) | task | Quality reports por dataset |
| 7 | [08-T-datasets-csv-jsonl](open/08-T-datasets-csv-jsonl.md) | task | Derivar CSV/JSONL/MD |
| 8 | [09-T-datasets-questions](open/09-T-datasets-questions.md) | task | Banco de perguntas + ground truth SQL |
| 9 | [10-T-datasets-cleanup](open/10-T-datasets-cleanup.md) | task | Mover retail_sales para poor-reference |
| 10 | [11-T-telemetry](open/11-T-telemetry.md) | task | Modulo de timing honesto (`src/tcf/timing.py`) |

### Findings DONE (mantidos como referencia)

| Ticket | Tipo | Status |
|--------|------|--------|
| [H-diagnostic-3layer-v02](open/H-diagnostic-3layer-v02.md) | hypothesis | **DONE** (F80-F84) |
| [E-stats-ablation](open/E-stats-ablation.md) | experiment | **DONE** (F90-F94) |

## Proxima fase (ainda nao definida)

Apos a Fase 1 estar completa, reavaliaremos para decidir **Fase 2**.
Opcoes provaveis:
- STATS-based hints como contribuicao central (usando os dados novos)
- Comparacao honesta de formatos (CSV, JSONL, TCF, TOON) com dados canonicos
- Outra direcao que surgir da analise dos dados novos

**Nao pensar em Fase 2 agora.** Focar em concluir Fase 1.

---

## Frozen (34) — tickets congelados como "futuro trabalho"

Em 2026-04-10 decidimos congelar 34 tickets criados em rounds anteriores.
Eles representam pesquisa valida mas prematura — ainda nao sabemos se
sao essenciais para a pergunta cientifica nuclear.

Ver [frozen/README.md](frozen/README.md) para listagem completa e
criterio de descongelamento.

Grupos congelados:
- Formato TCF especifico (advanced encodings, streaming, token-friendly, etc)
- Experimentos ambiciosos (http-protocol, code-gen, qualitative, speed)
- Metodologia ampla (utility-analysis, llm-scope, stability, tokenizer)
- Engenharia (cli-lib, adapters, multi-lang)

**Principio:** nao apagar, so congelar. Se durante a Fase 1 descobrirmos
que algum desses e essencial, descongelamos com justificativa.

---

## Closed (26) — concluidos

| Ticket | Tipo | Titulo |
|--------|------|--------|
| [E-G01](closed/E-G01-encode-decode-v01.md) | experiment | Encode/decode v0.1 |
| [E-G01b](closed/E-G01b-compression-v01.md) | experiment | Compression v0.1 |
| [E-G02](closed/E-G02-comprehension-v01.md) | experiment | Phase 1 v0.1 |
| [E-G03](closed/E-G03-ablation-v01.md) | experiment | Phase 2 v0.1 |
| [E-G04](closed/E-G04-stats-v01.md) | experiment | Stats v0.1 |
| [E-G20b](closed/E-G20b-benchmark-v02.md) | experiment | Compression v0.2 |
| [E-G21](closed/E-G21-llm-v02.md) | experiment | LLM accuracy v0.2 |
| [E-G22](closed/E-G22-decode-reverso.md) | experiment | → absorvido |
| [E-G23](closed/E-G23-perguntas-progressivas.md) | experiment | → absorvido |
| [E-G24](closed/E-G24-multi-step.md) | experiment | → absorvido |
| [E-G32](closed/E-G32-escala.md) | experiment | → absorvido |
| [E-pareto](closed/E-pareto-accuracy-tokens.md) | experiment | → absorvido |
| [H-G31](closed/H-G31-thinking-mode.md) | hypothesis | → absorvido |
| [H-G36](closed/H-G36-idioma-perguntas.md) | hypothesis | → absorvido |
| [H-G37](closed/H-G37-notacao-decoracao.md) | hypothesis | → absorvido |
| [P-H01](closed/P-H01-reversibility.md) | hypothesis | Reversibilidade |
| [P-transport](closed/P-transport-compression.md) | research | Transport gzip |
| [R-F30](closed/R-F30-tcf-escala.md) | finding | TCF escala |
| [R-F51](closed/R-F51-gemma3-melhor.md) | finding | gemma3 melhor |
| [R-F70](closed/R-F70-transport-compression.md) | finding | TCF+gzip 29% < CSV+gzip |
| [R-F80](closed/R-F80-stats-shortcut.md) | finding | STATS shortcut |
| [R-F90](closed/R-F90-stats-confirmed.md) | finding | STATS inflates all models |
| [R-F100](closed/R-F100-small-models.md) | finding | <2B unviable |
| [T-G20](closed/T-G20-encoder-v02.md) | task | Encoder v0.2 |
| [T-G40](closed/T-G40-paper.md) | task | → absorvido |
| [T-cleanup-naming](closed/T-cleanup-naming.md) | task | Rename _v02 |
| [T-P04](closed/T-P04-encoder-variants.md) | task | Variantes v0.1 |
