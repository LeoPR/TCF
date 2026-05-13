---
title: M-architecture-v03 — split TCF nucleo + extras opcionais
type: meta
status: OPEN
priority: HIGH
created: 2026-04-27
origin: Conversa pos-reorg de docs sobre foco do TCF como nucleo
user_quote: "o foco e o TCF, em que ele atua como compressoes e descompressor; ai pensei em pacotes auxiliares"
see_also:
  - docs/workbench/research-notes/2026-04-27-architecture-v03.md (proposta)
  - docs/theory/components/4-compression-deep-dive.md
  - docs/workbench/tickets/open/R-tcf-core-revisit.md
  - docs/workbench/tickets/open/R-project-rename.md
---

# Meta-ticket: split do TCF em nucleo + extras

## Visao

Separar o repositorio em **nucleo TCF puro** (encoder/decoder) +
**ferramentas auxiliares** com lifecycle proprio. Modelo de
referencia: SQLAlchemy core + drivers + extensions.

Detalhamento da proposta em
[../../research-notes/2026-04-27-architecture-v03.md](../../research-notes/2026-04-27-architecture-v03.md).

## Motivacao

Estado atual mistura 3 escopos no mesmo repo:
1. **Produto TCF**: encoder/decoder/compression (foco do paper)
2. **Pesquisa academica**: Shaper, runners M-series, manifests
3. **Auxiliares uteis**: clients LLM, dataset reader

Para usuario que quer instalar `pip install tcf` e usar, isso confunde.
Para pesquisador que quer reproduzir experimentos, ate ajuda — mas
mistura responsabilidades.

## Sub-tickets propostos

### Fase 1 — split core (sem mover funcionalidade)

| Sub-ticket | Descricao |
|-----------|-----------|
| T-package-split-core | Mover `src/tcf/` -> `packages/tcf/src/tcf/` |
| T-package-pyproject | Criar `packages/tcf/pyproject.toml` |
| T-package-workspace | Setup `uv` ou `poetry` workspace na raiz |
| T-package-imports | Atualizar imports em experiments/ |
| T-package-smoke | Smoke tests pos-split |

### Fase 2 — extractor inicial (so SQLite + Postgres)

| Sub-ticket | Descricao |
|-----------|-----------|
| T-extractor-skeleton | `packages/tcf-extractor/` skeleton + pyproject |
| T-extractor-api | API: `StructureExtractor(engine)` |
| T-extractor-sqlite | Adapter SQLite (in-memory tests) |
| T-extractor-postgres | Adapter Postgres |
| T-extractor-docs | README + exemplos |

### Fase 3 — adapters incrementais

| Sub-ticket | Descricao |
|-----------|-----------|
| T-extractor-mssql | Adapter MSSQL |
| T-extractor-mysql | Adapter MySQL |
| T-extractor-snowflake | Adapter Snowflake (opcional) |

### Fase 4 — TCF v0.3 internals

Depende de [R-tcf-core-revisit](R-tcf-core-revisit.md). Cada proposta
A-G do compression-deep-dive vira sub-ticket.

### Fase 5 — paper update

| Sub-ticket | Descricao |
|-----------|-----------|
| T-paper-arch-figure | Diagrama de arquitetura como Figura 0 |
| T-paper-cap4-update | Cap 4 (metodologia) com nova arch |
| T-paper-appendix-A | Apendice A com TCF v0.3 spec |

## Decisoes pendentes

1. **Quando**: agora ou pos-paper?
2. **Workspace tooling**: `uv` (rapido, recente) vs `poetry` (maduro)?
3. **Extractor: pacote irmao ou submodule do tcf?**
   - `tcf-extractor` (separado) — mais limpo, lifecycle proprio
   - `tcf[extractor]` extras — mais simples para usuario, acopla deps
4. **LLM layer**: separa em `tcf-llm` ou mantem em `experiments/eval/`?
5. **Publicar PyPI**: pos-paper, junto, ou nunca?

## Riscos

- **Quebrar imports** em experiments/ durante migracao
- **Drift de versao** entre tcf core e tcf-extractor
- **Apendice A** do paper precisa refletir v0.2 OU v0.3, nao ambos

## Criterio de aceite (do meta-ticket)

- [ ] Decisao tomada para cada item de "Decisoes pendentes"
- [ ] Sub-tickets criados com base na decisao
- [ ] Cap 4 do paper atualizado se split for pre-paper
- [ ] Smoke tests todos passando pos-migracao
- [ ] CHANGELOG.md com entry v0.3-arch-split

## Impacto estimado

- Fase 1 (split core): 1-2 dias
- Fase 2 (extractor SQLite+Postgres): 3-5 dias
- Fase 3 (adapters): 2-3 dias por adapter
- Fase 4 (v0.3 internals): 2-4 semanas (depende escopo)
- Fase 5 (paper): 2-3 dias

Total se fizer tudo: ~6-8 semanas. Pode ser fatiado.

## Notas para revisar este meta-ticket

Quando reabrir:
- Snapshot deste arquivo no commit `<ts>`
- Estado atual: `src/tcf/`, `scripts/shaper/`, `experiments/`
- Se reorg ja aconteceu: `packages/` deve existir
- Tickets relacionados:
  - [R-tcf-core-revisit](R-tcf-core-revisit.md) — decisoes v0.3
  - [R-project-rename](R-project-rename.md) — possivel rename junto
  - [H-advanced-compression-v03](H-advanced-compression-v03.md) —
    propostas tecnicas que ficam em packages/tcf/
