# TCF — Documentation Hub

Este e o compendio central de toda a documentacao do projeto TCF
(Textual Columnar Format). Se voce quer entender algo sobre o projeto,
comece aqui.

## Indice

### Arquitetura
Como o projeto e organizado, onde dados vivem, como medimos coisas.

- [architecture/overview.md](architecture/overview.md) — visao geral da arquitetura
- [architecture/boundaries.md](architecture/boundaries.md) — **fronteiras: TCF core vs support vs experiments**
- [architecture/storage.md](architecture/storage.md) — estrategia de storage (git / disco / archive)
- [architecture/telemetry.md](architecture/telemetry.md) — medicao honesta de tempo (IO / parse / TCF)
- [architecture/source-map.md](architecture/source-map.md) — rastreabilidade entre documentos

### Datasets
Datasets canonicos usados nos experimentos.

- [datasets/tpch-sf001.md](datasets/tpch-sf001.md) — TPC-H Scale Factor 0.01
- [datasets/adult-census.md](datasets/adult-census.md) — UCI Adult Income
- [datasets/poor-reference.md](datasets/poor-reference.md) — retail_sales sintetico (legacy)

### Metodologia
Como experimentos sao planejados e executados.

- [methodology/experimental-design.md](methodology/experimental-design.md) — design experimental em fases
- [methodology/tests.md](methodology/tests.md) — registro de testes

### Artigo cientifico
O paper em construcao, em capitulos separados.

- [article/README.md](article/README.md) — indice do artigo
- [article/00-innovations.md](article/00-innovations.md) — inovacoes comprovadas (I1-I7)
- [article/01-introduction.md](article/01-introduction.md) — introducao
- [article/02-related-work.md](article/02-related-work.md) — trabalhos relacionados
- [article/03-tcf-format.md](article/03-tcf-format.md) — especificacao TCF
- [article/04-methodology.md](article/04-methodology.md) — metodologia
- [article/05-results-e1-e2.md](article/05-results-e1-e2.md) — resultados encode/decode
- [article/07-results.md](article/07-results.md) — resultados LLM
- [article/08-discussion.md](article/08-discussion.md) — discussao (placeholder)
- [article/09-conclusion.md](article/09-conclusion.md) — conclusao (placeholder)

### Research Notes
Pesquisas datadas com referencias. Cada arquivo e auto-suficiente,
registrando o que foi pesquisado, quando, e onde encontrar as fontes.

- [research-notes/2026-04-10-canonical-datasets.md](research-notes/2026-04-10-canonical-datasets.md) — ~20 datasets avaliados
- [research-notes/2026-04-10-compression-tokens-streaming.md](research-notes/2026-04-10-compression-tokens-streaming.md) — columnstore SQL Server, BPE, streaming
- [research-notes/2026-04-10-critical-review.md](research-notes/2026-04-10-critical-review.md) — revisao critica TOON, gaps metodologicos
- [research-notes/2026-04-10-storage-architecture.md](research-notes/2026-04-10-storage-architecture.md) — Cookiecutter DS, DVC, telemetria

### Reference
Glossarios e referencias rapidas.

- [reference/glossary.md](reference/glossary.md) — termos do projeto
- [reference/format-cheatsheet.md](reference/format-cheatsheet.md) — referencia rapida de formatos

---

## Navegacao por objetivo

**Quero entender o que e TCF:**
→ [../README.md](../README.md) (root) → [article/01-introduction.md](article/01-introduction.md)

**Quero reproduzir os experimentos:**
→ [architecture/storage.md](architecture/storage.md) → [methodology/experimental-design.md](methodology/experimental-design.md) → [datasets/](datasets/)

**Quero ver os findings cientificos:**
→ [article/00-innovations.md](article/00-innovations.md) → [article/07-results.md](article/07-results.md)

**Quero contribuir ou extender:**
→ [architecture/overview.md](architecture/overview.md) → [../tickets/README.md](../tickets/README.md)

**Quero saber por que uma decisao foi tomada:**
→ [research-notes/](research-notes/) (pesquisas datadas) → git log

---

## Convencoes

1. **Apenas `README.md` e documentos essenciais vivem na raiz do projeto.**
   Tudo que e documentacao substantiva vive aqui em `docs/`.

2. **Arquivos datados** em `research-notes/` preservam o contexto temporal.
   Nao atualizamos retroativamente — criamos um novo arquivo datado se
   a situacao mudar.

3. **Findings** (F##) sao cross-referenciados entre documentos. Um finding
   e definido em UM lugar (ticket ou research note), outros apontam para ele.

4. **Decisoes arquiteturais** vao em `architecture/`. Se uma decisao precisa
   de justificativa longa, vai em `research-notes/` e `architecture/` linka.

5. **Dados** NAO moram em `docs/`. Datasets tem seus manuais em `docs/datasets/`,
   mas os dados em si ficam fora do git (ver [architecture/storage.md](architecture/storage.md)).

---

## Mapa de arquivos legados (migrados)

Arquivos que estavam na raiz de `docs/` e foram movidos em 2026-04-10:

| De | Para | Motivo |
|----|------|--------|
| `docs/ARCHITECTURE.md` | `docs/architecture/overview.md` | Estrutura por tema |
| `docs/SOURCE_MAP.md` | `docs/architecture/source-map.md` | Estrutura por tema |
| `docs/TESTS.md` | `docs/methodology/tests.md` | Estrutura por tema |
| `docs/EXPERIMENT_DESIGN.md` | `docs/methodology/experimental-design.md` | Estrutura por tema |
| `docs/ARTICLE.md` | `docs/article/README.md` | Redundante, consolidado |
