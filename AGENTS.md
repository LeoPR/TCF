# AGENTS.md — TCF

> **Wrapper de portabilidade**: este arquivo existe pra agentes de IA
> que seguem o padrao emergente [AGENTS.md](https://agents.md/)
> (OpenAI Codex, Cursor, outros). O conteudo canonico vive em
> [`CLAUDE.md`](CLAUDE.md) — leia ele primeiro.

## Entry points (em ordem de prioridade)

1. **[`CLAUDE.md`](CLAUDE.md)** — guia operacional completo: inventario
   "onde esta o que", checklist "antes de agir", convencoes, lista NUNCA
2. **[`STATUS.md`](STATUS.md)** — estado atual + foco
3. **[`MAP.md`](MAP.md)** — mapa de 1 pagina
4. **[`README.md`](README.md)** — overview pra humano

## Regras criticas (extraidas de CLAUDE.md)

- **NUNCA** modificar `src/tcf/` sem aprovacao explicita (canonical)
- **NUNCA** baixar dados externos quando `Z:/tcf-data/` ja' tem infra
- **NUNCA** commitar com `Co-Authored-By:`
- **NUNCA** push pra main sem confirmacao explicita
- **ANTES de propor recriar X**: `Glob`/`Grep` em `scripts/`, `datasets/`,
  `experiments/` (ver checklist completo em CLAUDE.md)

## Para agentes que carregam multiplos arquivos

Se o agente carrega ambos `AGENTS.md` e `CLAUDE.md`, **CLAUDE.md prevalece**
(este e' so' o wrapper de descoberta). Sem duplicacao deliberada — qualquer
divergencia, atualizar CLAUDE.md como fonte da verdade.

## Metodologia

Este projeto segue a oficina metodologica em
[`../Methodologies/README.md`](../Methodologies/README.md), com Strata em
[`../Methodologies/recipe/knowledge-architecture.md`](../Methodologies/recipe/knowledge-architecture.md).
Pilares aplicados: separacao por durabilidade, rastreabilidade, disciplina de pesquisa e tickets.
