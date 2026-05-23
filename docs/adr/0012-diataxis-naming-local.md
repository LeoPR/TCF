# 0012 — Diataxis naming local (docs/algorithms, docs/theory)

**Status**: accepted
**Date**: 2026-05-23
**Deciders**: project owner
**Tags**: documentation, diataxis, naming, convention

## Context and Problem Statement

A metodologia subjacente do projeto (`../../README.methodology.md`)
adota Diataxis (Procida) como framework de documentacao com 4
categorias canonicas:
- `reference/` — descricoes tecnicas exatas (specs, API)
- `explanation/` — fundamentos teoricos, contexto
- `how-to/` — guias orientados a tarefa
- `tutorials/` — passo-a-passo pra novato

Este projeto usa convencao local DIVERGENTE dos nomes Diataxis:
- `docs/algorithms/` — funciona como `reference/` (specs OBAT, HCC, TCF-format)
- `docs/theory/` — funciona como `explanation/` (perspectivas, taxonomias)
- `docs/how-to/` — alinhado com Diataxis (mantido)
- `docs/tutorials/` — nao existe (criar quando necessario)

Sem ADR explicito, novo contribuidor (humano ou IA) pode tentar criar
`docs/reference/` paralelo, gerando dual source confuso.

## Considered Options

### Opcao A — ADR explicito documentando mapeamento (RECOMENDADO)

Este ADR. Custo: 1 doc. Beneficio: convencao auditavel + decisao
documentada.

### Opcao B — Nota em MAP.md + CLAUDE.md sem ADR

Mais barato. Menos formal. Risco: nota pode ser ignorada/perdida.

### Opcao C — Renomear pastas pra padrao Diataxis

Custo ALTO: quebra links em ADRs (0001-0011), tickets, notas dirty,
imports indiretos. Beneficio marginal (so' alinhamento de nome).

### Opcao D — Manter ambiguidade

Risco alto de dual source.

## Decision Outcome

**Opcao A — ADR explicito** (este doc).

Metodologia (`README.methodology.md` §13.2 "Convencoes locais vencem
nomes deste doc") autoriza explicitamente convencoes locais. Custo
ZERO de renomear; beneficio de declarar mapeamento previne dual source.

### Mapeamento canonical

| Pasta neste projeto | Equivalente Diataxis | Conteudo tipico |
|---|---|---|
| `docs/algorithms/` | **reference** | Specs algoritmo (OBAT.md, HCC.md, TCF-format.md) |
| `docs/theory/` | **explanation** | Fundamentos teoricos, taxonomias, perspectivas |
| `docs/how-to/` | **how-to** | Guias tarefa (audit-memorias, fluxo-hipotese-producao) |
| `docs/adr/` | (transversal) | Architecture Decision Records (todas categorias) |
| `docs/findings/` | (cross-cut) | Resultados consolidados de pesquisa |
| (sem) | **tutorials** | Nao criado — adicionar quando primeiro tutorial existir |

### Justificativa pra preservar nomes locais

1. **Consolidacao**: `docs/algorithms/` + `docs/theory/` ja' tem
   conteudo extenso (5+ arquivos cada), refs em ADRs (0001-0011) e
   tickets. Renomear quebraria todos.
2. **Leitura ergonomica**: "algorithms" e "theory" sao mais descritivos
   pra contexto deste projeto (compressao + tokenizacao) que termos
   abstratos "reference" e "explanation".
3. **Diataxis e' framework, nao prescricao**: o que importa e' separar
   por TIPO COGNITIVO (referencia rapida vs. fundamentos), nao usar
   NOMES exatos.

## Tutorials (decisao adicional)

Pasta `docs/tutorials/` **nao sera criada agora**. Criterio pra criar
no futuro:
- Primeiro tutorial real existe (passo-a-passo end-to-end pra novato)
- API publica estabilizada (v1.0+)
- Demand observavel (issues pedindo "como comecar")

Ate' la', `README.md` cumpre papel de "tutorial minimo" via API minima
no topo.

## Pros and Cons

| Opcao | Pros | Cons |
|---|---|---|
| **A (este ADR)** | Auditavel; zero refactor; respeita §13.2 | 1 doc adicional |
| B (nota informal) | Ainda mais barato | Menos auditavel; risco dilui |
| C (renomear) | Alinhamento literal Diataxis | Custo alto; quebra links |
| D (ambiguo) | Zero custo | Risco dual source |

## Riscos residuais

- **Sobre-formalizar nao-decisao**: mitigacao — ADR e' curto, foca em
  declarar mapeamento.
- **Tutorials criados de outra forma**: se primeiro tutorial nascer
  fora de `docs/tutorials/`, atualizar este ADR.

## Cross-references

- [Metodologia §"Pilar 2 Diataxis"](../../../README.methodology.md)
- [Metodologia §13.2 "Convencoes locais vencem nomes deste doc"](../../../README.methodology.md)
- [ADR-0005 estrutura discoverability](0005-discoverability-claude-md-root.md)
- [MAP.md inventario docs](../../MAP.md)
- [CLAUDE.md guia Claude Code](../../CLAUDE.md)
