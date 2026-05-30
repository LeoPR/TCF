---
title: T-RECOVER-LLM-SCHEMA-MODE — Ferramenta auxiliar LLM pra gerar SQL (EXTERNO ao TCF)
status: de-prontidao
priority: P3
created: 2026-05-27
updated: 2026-05-27 (escopo corrigido pelo owner: ferramenta auxiliar, NAO integrada ao TCF)
blocked-by: []
related:
  - tickets/T-RECOVER-SCHEMA-MULTI-TABLE.md  (outra ferramenta auxiliar)
  - docs/findings/  (Phase 1 LLM Q01-Q38 historic v0.5)
---

# T-RECOVER-LLM-SCHEMA-MODE

## Contexto + ESCOPO (corrigido 2026-05-27)

**Ferramenta AUXILIAR EXTERNA ao TCF**, sem relacao direta com o algoritmo.
Vive em pacote separado ou utilitario standalone.

Owner clarificou (2026-05-27) que esta e' uma ferramenta complementar:
dado um schema (de qualquer origem — pode ser do schema multi-tabela
auxiliar OU de qualquer outra fonte), o LLM ajuda gerar SQL inteligente.
TCF nao depende disso; isso nao depende de TCF (alem de eventualmente
consumir o output de outras ferramentas).

## Proposta

Modo schema-LLM:
```
schema (qualquer formato compativel) → LLM com prompt schema-aware →
SQL gerado (com ORDER BY, JOINs, projecoes) → executa em SQLite/DuckDB →
dados extraidos
```

**Caso de uso autonomo**: usuario tem schema (de qualquer fonte), quer
consultar via LLM sem escrever SQL na mao.

**Caso de uso TCF-adjacent (opcional)**: dados extraidos podem ser input
do `encode()`. TCF processa qualquer dict[str, list[str]], nao se importa
de onde vieram.

## Estado atual

- **Existe (em old/tcf/ + docs/findings/)**: Phase 1 LLM benchmark Q01-Q38
  (v0.5, marcado historic). Infraestrutura de qualified models + Ollama
  client. NUNCA importado por src/tcf.
- **Existe**: `pip install -e ".[eval]"` instala requests pra Ollama client
  (extra atual, nao usado pelo TCF core)
- **NAO existe**: ponte LLM ↔ schema generico (este ticket)

## Plano (futuro)

### Fase 0 — Decisao arquitetural
- **Onde vive este modulo?**:
  - Opcao A: pacote totalmente separado `tcf-llm-tools` (PyPI proprio)
  - Opcao B: extra opcional `pip install tcf[llm]` (mas no src/, isolado)
  - Opcao C: scripts/ standalone, sem instalacao
- Owner deve decidir antes de escrever codigo (vira ADR pequeno).

### Fase 1 — Prompt schema-aware
- Template: "Given this schema {schema_dict}, write SQL to {intent}"
- Reuso de qualified models do Phase 1 se estaveis

### Fase 2 — Validador SQL → schema
- Parse SQL gerado, valida contra schema
- Feedback loop se SQL invalido

### Fase 3 — CLI utility ou API
- `python -m tcf_llm_tools query <schema-file> "intent in natural language"`
- Output: SQL + dataframe execucao

## Conexao

- **NAO toca** src/tcf/
- Pode consumir output de T-RECOVER-SCHEMA-MULTI-TABLE (outra ferramenta
  auxiliar), mas nao depende formalmente
- Reuso de infra v0.5 (old/tcf/ + docs/findings/), respeitando que e'
  acessorio (CLAUDE.md NUNCA list: nao importar de old/tcf em src/tcf)

## Riscos

- Mission creep: TCF e' lib de compressao, nao plataforma LLM
- Spin-off correto evita esse risco (Opcao A acima)
- Ollama/local-LLM dependency e' setup-friction (opt-in resolve)

## Mitigations

- **Spin-off recomendado** (Opcao A): pacote separado `tcf-llm-tools`
  ou nome neutro `schema-llm-bridge` (sem amarrar a TCF)
- Documentacao explicita: "esta ferramenta NAO faz parte do TCF; e'
  utilitario complementar"

## Status

**De prontidao** (registrado 2026-05-27, escopo corrigido). Atacar
quando owner decidir; **NAO bloqueia roadmap TCF**.
