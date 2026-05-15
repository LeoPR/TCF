# META-DOCS-V05-OBSOLETE — Fase 2: limpar v0.5 dos docs

**Status**: CLOSED (2026-05-17)
**Criado**: 2026-05-17
**Fechado**: 2026-05-17
**Escopo**: marcar/arquivar conteudo v0.5-exclusivo em `docs/` para
que leitor novo nao se confunda. Preservar conceitos que **reconectam**
ao v0.6 (multi-coluna, tipos de dados, pre-tx).

## Resultado

Executado em 2 commits:
- Commit `8f33744`: moves T-DOC-1 a T-DOC-6 (`git mv` preservou history)
- Commit pendente (este): theory placeholder + findings notice +
  hub docs/README + README raiz links + datasets links + close

Acceptance criteria atendidos:
1. ✓ v0.5 EXCLUSIVO em `docs/archive/*_v05/`
2. ✓ `docs/findings/` + `FINDINGS_SUMMARY.md` com notice v0.5 historic
3. ✓ `docs/theory/README.md` reconectando a v0.6 + lista pendencias
   (multi-coluna, tipos de dados, pre-tx, storage)
4. ✓ Hub `docs/README.md` reescrito para v0.6
5. ✓ Links README raiz + datasets/ apontam pra archive (sem quebrar)

## Principio

- v0.6 tem **nucleo restruturado** (OBAT + HCC). Conceitos antigos
  v0.5 podem precisar reconectar mas sao acessorios.
- v0.5 EXCLUSIVO (API antiga, Linha A/B LLM, v0.4 architecture) →
  arquivar.
- v0.5 com conceitos POTENCIALMENTE RECONECTAVEIS (Phase 1 findings,
  metodologia geral, storage) → manter com notice.
- Recuperabilidade via `git mv` (preserva history).

## Sub-tarefas

### T-DOC-1: `docs/manual/` → archive (v0.5 API)

API atual descreve `encode_rows(level=2, include_stats=True)` — v0.5
columnar/RLE. Nao se aplica a v0.6 (`from tcf import encode, decode`).

Acao: `git mv docs/manual docs/archive/manual_v05`

### T-DOC-2: `docs/article/` → archive (paper drafts v0.5)

Paper drafts orientados a LLM benchmark v0.5. v0.6 paper sera
escrito depois.

Acao: `git mv docs/article docs/archive/article_v05` (conflito com
`docs/archive/article_v01/` — usar nome diferente).

### T-DOC-3: `docs/theory/components/` → archive

Componentes descritos sao v0.4:
- `1-tcf-core.md` (v0.4 TCF Core, nao OBAT)
- `2-tcf-llm-interface.md`, `3-tcf-db-extractor.md`,
  `4-compression-deep-dive.md`, `5-compression-map-v04.md`,
  `6-test-harness.md`, `7-combination-study.md`

Acao: `git mv docs/theory/components docs/archive/theory_components_v05`

### T-DOC-4: `docs/theory/architecture/` → archive

Architecture descrita e' v0.4 (boundaries, source-map, telemetry,
storage 3-layer). Conceitos podem reconectar mas estrutura geral
e' v0.5.

Acao: `git mv docs/theory/architecture docs/archive/theory_architecture_v05`

### T-DOC-5: `docs/theory/research-lines/` → archive

Linha A (LLM direct reasoning) vs Linha B (schema carrier) sao
estruturas v0.5 LLM. Nao se aplicam a v0.6.

Acao: `git mv docs/theory/research-lines docs/archive/theory_research_lines_v05`

### T-DOC-6: `docs/theory/methodology/` → archive (todo, exceto rigor)

`F-findings.md`, `experimental-design.md`, `model-ranking.md`,
`tests.md` sao v0.5. `llm-research-rigor.md` tem padroes gerais
de rigor cientifico — mas em contexto LLM. Arquivar tudo;
re-derivar metodologia v0.6 se necessario.

Acao: `git mv docs/theory/methodology docs/archive/theory_methodology_v05`

### T-DOC-7: `docs/theory/` → cleanup pos-move

Apos T-DOC-3 a T-DOC-6, `docs/theory/` ficara vazio. Decidir:
- (a) Deletar `docs/theory/` (vazia)
- (b) Criar `docs/theory/README.md` minimo apontando pra docs/algorithms/

Sugiro (b) — placeholder pra v0.6 theory crescer (multi-coluna,
pre-tx, etc.).

### T-DOC-8: `docs/findings/` + `docs/FINDINGS_SUMMARY.md` → notice

Phase 1 LLM findings (Q01-Q38) sao **historicos validos**. Manter
no lugar, adicionar notice no topo de cada arquivo dizendo:
"Phase 1 LLM benchmark — ciclo v0.5; acessorio a TCF v0.6".

Acao: Edit cabecalho de cada arquivo + FINDINGS_SUMMARY.md

### T-DOC-9: `docs/README.md` hub → atualizar

Refletir nova realidade: docs/algorithms/ + docs/findings/ + archive/
v0.5. Remover ponteiros pra theory/manual/article/ (movidos pra
archive).

Acao: Edit docs/README.md

### T-DOC-10: README raiz — pointers

Verificar links que apontam para manual/, article/, theory/. Atualizar
ou remover.

Acao: Edit README.md raiz se necessario

## Acceptance

1. v0.5 EXCLUSIVO em `docs/archive/*_v05/`
2. `docs/findings/` mantido com notice v0.5
3. Hub `docs/README.md` reflete v0.6 atual
4. Nenhum link quebrado no README raiz
5. Todos commits pushados antes de proximo passo

## Conexoes

- META-NAMING (closed) — pre-requisito para nomes oficiais nos novos docs
- `docs/algorithms/` — destino conceitual da reorientacao
