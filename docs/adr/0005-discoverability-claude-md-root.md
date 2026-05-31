# 0005 — Discoverability: CLAUDE.md root + MAP.md + hooks

**Status**: accepted
**Date**: 2026-05-18
**Deciders**: project owner
**Tags**: documentation, discoverability, claude-code, anti-incidente

## Context and Problem Statement

Em 2026-05-18, durante sessao Claude Code, foi proposta a criacao
de novo dataset / download externo quando havia infra completa em
`scripts/dataset_reader.py` + `scripts/shaper/` + `Z:/tcf-data/`.

Falha de **discoverability**. Causa raiz analisada: projeto **nao tem
`CLAUDE.md` no root** (scope project, via git). Toda memoria do
Claude estava em user scope (`~/.claude/.../memory/MEMORY.md`), que
nao mencionava a infra de datasets.

Antipatterns identificados:
- Hidden knowledge (existe mas AI nao busca)
- Single-source violation (info dispersa, sem mapa)
- Duplicate-by-ignorance (recriar infra existente)
- Documentation graveyard (existe mas sem entry point)

## Considered Options

1. **Status quo** — manter so' memoria user; confiar em busca exaustiva
2. **CLAUDE.md root + MAP.md + hooks** — sistema multi-camada
3. **Vector DB / RAG** — semantica busca em codigo
4. **Knowledge graph** (Obsidian/Logseq adaptados)

## Decision Outcome

**Opcao 2 — CLAUDE.md root + MAP.md + Claude Code hooks**.

Quatro camadas combinadas (Diataxis + ADR + Compendium + IA):

| Camada | Framework | TCF location | Purpose |
|---|---|---|---|
| 1. Wayfinding | Morville | `/CLAUDE.md` + `/MAP.md` | Descoberta — "onde esta o que" |
| 2. Stable docs | Diataxis | `/docs/{tutorials,how-to,reference,explanation}/` | Canonical user-facing |
| 3. Decisoes | ADR/MADR | `/docs/adr/NNNN-*.md` | Por que decidimos X |
| 4. Lab work | Research Compendium + FAIR4RS | `/experiments/` com YAML frontmatter | Reprodutibilidade + busca |

### Componentes implementados

- **`/CLAUDE.md`** (~170 linhas): inventario "onde esta o que" +
  checklist "antes de agir" + convencoes + lista NUNCA. Carregado
  automaticamente pelo Claude Code.
- **`/MAP.md`**: wayfinding map de 1 pagina, tabela "quero fazer X"
- **`.claude/settings.json`** com SessionStart hook que injeta
  `.claude/session-start-context.md` no contexto da sessao
- **`/docs/adr/`** com ADRs numerados (este e' o ADR-0005)
- **`/docs/vocabulary.md`** (a criar): vocabulario controlado
- **YAML frontmatter** em READMEs de experimentos (status, tags)
- **Stale markers** (`[VERIFICAR: YYYY-MM-DD]`) em claims mutaveis

### Anti-incidente — checklist "antes de agir"

ANTES de propor download/recriar/sintetizar:
1. `Glob scripts/**/*.py`
2. `Glob datasets/**`
3. `Grep` por termos relacionados
4. `Read STATUS.md`, `MAP.md`, `CLAUDE.md`
5. Checar `Z:/tcf-data/`

## Pros and Cons of the Options

| Opcao | Pros | Cons |
|---|---|---|
| Status quo | Zero overhead | Confirmado: falha em incidente real |
| **CLAUDE.md + MAP + hooks** | ROI alto, baixa complexidade, padrao oficial | Requer manutencao (atualizar CLAUDE.md/MAP.md) |
| Vector DB / RAG | Busca semantica | Overhead alto; literatura mostra que `grep` + AST funciona melhor pra codigo |
| Knowledge graph | Cross-link visual | Tool adicional; nao integra com Claude Code |

## Validacao

- CLAUDE.md root cobre incidente concreto que motivou esta decisao
- SessionStart hook injeta inventario deterministicamente
- ADRs (este sistema) substituem `feedback_*.md` ad-hoc

## Sources / Literature

- [Claude Code memory hierarchy](https://code.claude.com/docs/en/memory)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks-guide)
- [Diataxis (Procida)](https://diataxis.fr/)
- [ADR (Nygard) + MADR](https://adr.github.io/)
- [Research Compendium (Turing Way)](https://book.the-turing-way.org/reproducible-research/compendia/)
- [FAIR4RS principles](https://www.nature.com/articles/s41597-022-01710-x)
- [Ambient Findability (Morville)](https://archive.org/details/ambientfindabili0000morv)
- Memoria user: `feedback_discoverability_falha_EXP_012.md`

## Cross-references

- Checkpoint do incidente: `experiments/lab/dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md`
- Memoria user `feedback_discoverability_falha_EXP_012` (licao)
- MEMORY.md indexa novo entry
