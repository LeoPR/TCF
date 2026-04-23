# TCF — Documentation Hub

Este e o compendio central de toda a documentacao do projeto TCF
(Textual Columnar Format). Se voce quer entender algo sobre o projeto,
comece aqui.

## Indice

### Arquitetura
Como o projeto e organizado, onde dados vivem, como medimos coisas.

- [architecture/overview.md](architecture/overview.md) — visao geral da arquitetura
- [architecture/boundaries.md](architecture/boundaries.md) — **fronteiras: TCF core vs support vs experiments**
- [architecture/opacity-spectrum.md](architecture/opacity-spectrum.md) — **espectro: LLM-readable → transport → archive**
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

- [methodology/F-findings.md](methodology/F-findings.md) — **FONTE PRIMARIA: achados cientificos F-Q1..F-Q21+**
- [methodology/model-ranking.md](methodology/model-ranking.md) — **ranking modelos locais: accuracy, latencia, failure modes**
- [methodology/experimental-design.md](methodology/experimental-design.md) — design M-series (M1..M8+)
- [methodology/llm-research-rigor.md](methodology/llm-research-rigor.md) — protocolo de rigor cientifico
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
Evidencias e diarios de processo. Cada arquivo e auto-suficiente;
os achados consolidados vivem em `methodology/F-findings.md`.

- [research-notes/INDEX.md](research-notes/INDEX.md) — **indice completo: nota → F-finding → manifest**
- Principais:
  - [research-notes/2026-04-20-tcf-retrospective.md](research-notes/2026-04-20-tcf-retrospective.md) — retrospectiva M1-M5
  - [research-notes/2026-04-22-coverage-and-intermediate-forms.md](research-notes/2026-04-22-coverage-and-intermediate-forms.md) — Pandas/Polars/CoT
  - [research-notes/2026-04-22-timing-measurement-methodology.md](research-notes/2026-04-22-timing-measurement-methodology.md) — ALERTA: timing M1-M5

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
→ [methodology/F-findings.md](methodology/F-findings.md) (fonte primaria) → [article/07-results.md](article/07-results.md) (sintese paper)

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

3. **Findings** (F-Q##) vivem em `methodology/F-findings.md` (fonte unica).
   Research notes sao evidencias; article chapters sao sinteses. Nenhum dos
   dois define — ambos referenciam F-findings.

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
