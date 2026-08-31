---
title: M-llm-integration-future — meta-ticket de trabalho com LLMs (categoria separada)
type: meta
status: OPEN
priority: LOW
created: 2026-05-05
origin: Decisao 2026-05-05 de separar trabalho LLM do foco atual (core compression v0.4)
user_quote: "registre nos tickets uma categoria so pra trabalhar com as llms novamente, esse grupo e para trabalhar o inicio do core com ajustes"
see_also:
  - docs/workbench/tickets/open/H-compression-v04-roadmap.md (foco atual: core)
  - docs/workbench/tickets/closed/M-series/ (historico LLM Phase 1+2)
  - memory/project_phase1_findings.md
---

# Meta-ticket: trabalho com LLMs — categoria separada

## Por que existe

Foco atual (2026-04-27 →) e o **nucleo TCF puro**: ajustes de
encoder/decoder, compressao interna (v0.4), validacao cientifica via
harness. **LLM esta em segundo plano**.

Este meta-ticket existe para que ideias/trabalhos relacionados a LLM
nao se misturem com o foco do core. Tickets nesta categoria ficam
parados ate decisao explicita de retomar.

## Escopo

LLM-relacionado **inclui**:

- Phase 3/4/5 (cross-format, sample-size, model-replication)
- Re-rodadas de M-Acomm com modelos novos
- Reproducao de findings F-Q1..F-Q38 com prompts diferentes
- Novos cenarios de comprehension (filter+agg, joins, cross-table)
- Avaliacao TCF v0.4 vs v0.2 com modelos
- Integracao com OpenAI/Anthropic/Ollama (clients, prompts, scoring)
- Schema_qualifier (proposta G v0.4) — depende de avaliacao com LLM
- Stratified STATS validation com LLMs (proposta A v0.4)

LLM-relacionado **NAO inclui** (ficam no core/lab):
- Bytes/throughput de encoder/decoder (lab — pipeline simulator)
- Compressao gzip/brotli/zstd (lab — combinatorial study)
- Roundtrip exato encode→decode (core — testes unitarios)
- Auto-bypass / detect_sortedness / type-preserving (core)

## Sub-tickets propostos (pendentes — nao priorizar agora)

### Bloco LLM-1: validacao v0.4 com modelos

| Sub-ticket | Descricao |
|-----------|-----------|
| L-llm-v04-baseline | Comparar TCF v0.4 vs v0.2 nos 4 survivors (Phase 1) |
| L-llm-stratified-stats | Validar que stratified STATS sobe Linha A em filter+agg |
| L-llm-type-preserving | Testar se preservacao de tipos ajuda LLM em comprehension |

### Bloco LLM-2: extender Phase 2 com modelos novos

| Sub-ticket | Descricao |
|-----------|-----------|
| L-llm-claude-opus-4-7 | Re-rodar M-Acomm com Claude Opus 4.7 (vs 4.6) |
| L-llm-gpt-5 | Re-rodar M-Acomm com GPT-5 quando disponivel |
| L-llm-ollama-update | Atualizar Ollama models locais (Phase 3) |

### Bloco LLM-3: novos cenarios de comprehension

| Sub-ticket | Descricao |
|-----------|-----------|
| L-llm-cross-table-joins | Cenarios com 2+ tabelas e FK |
| L-llm-time-series | Datasets temporais (delta encoding pode ajudar) |
| L-llm-categorical-heavy | Datasets com muitas categoricas (DICT pode ajudar) |

### Bloco LLM-4: schema_qualifier (proposta G v0.4)

| Sub-ticket | Descricao |
|-----------|-----------|
| L-llm-schema-qualifier-design | Desenhar API e formato do qualifier |
| L-llm-schema-qualifier-impl | Implementar (vai em packages/tcf-extras) |
| L-llm-schema-qualifier-eval | Validar uplift LLM com qualifier |

## Quando reativar

Reativar este meta-ticket quando:

1. Core v0.4 estiver implementado e estavel
2. Lab (harness + estudos combinatoriais) tiver baseline cientifico
3. Decisao explicita de "agora vou voltar ao LLM"

Ate la, este ticket fica parado. Tickets relacionados que
**aparecerem** durante o trabalho de core (ex: "isso pode afetar
LLM") vao para esta lista, nao para o foco atual.

## Notas de revisao futura

Para reabrir este meta-ticket no futuro:

- Snapshot deste arquivo no commit `<ts>`
- Estado do core: ver `H-compression-v04-roadmap` (status pode estar CLOSED)
- Estado do lab: ver `experiments/lab/clean/` (deve ter EXP-001..EXP-N)
- Findings ate o momento: `docs/findings/` (catalogo F-Q*)
- Survivors atuais: `memory/project_phase1_findings.md` (4 modelos)
- Custos: `experiments/results/` ($9.46 ate M-Acomm)

Nao apagar este ticket — e o "marcador" para reativar a frente LLM.
