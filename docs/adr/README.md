# Architecture Decision Records (ADR)

Registros numerados das decisoes arquiteturais do TCF. Inspirado em
[Michael Nygard's ADR](https://adr.github.io/) + [MADR](https://adr.github.io/madr/).

## Convencao

- **Numeracao**: `NNNN-imperative-phrase.md` (4 digitos, ASCII, kebab-case)
- **Imutabilidade**: ADRs aceitos NUNCA sao editados. Pra mudar, criar
  novo ADR com `Status: Supersedes NNNN` e back-link.
- **Status**: `proposed`, `accepted`, `superseded by NNNN`, `deprecated`
- **Template MADR**:
  ```
  # NNNN — Titulo imperative

  **Status**: accepted | superseded by NNNN | deprecated
  **Date**: YYYY-MM-DD
  **Deciders**: who

  ## Context and Problem Statement
  ## Considered Options
  ## Decision Outcome
  ## Pros and Cons of the Options
  ## More Information / Links
  ```

## Index

| # | Titulo | Status |
|---|---|---|
| [0001](0001-tcf-format-shebang.md) | TCF format shebang (`#TCF.<minor>`) | accepted |
| [0002](0002-vertice-triplice-restricao.md) | Vertice triplice (compressao + memoria + latencia) como restricao dura | accepted |
| [0003](0003-tripartite-pre-obat-hcc.md) | Tripartite Pre/OBAT/HCC com pesos relativo vs absoluto | accepted |
| [0004](0004-multi-column-header-compacto.md) | Multi-column header compacto (`#TCF.6 M` + `# size=name,...`) | accepted |
| [0005](0005-discoverability-claude-md-root.md) | CLAUDE.md no root + MAP.md + hooks pra discoverability | accepted |
| [0006](0006-empty-string-decode-fix.md) | Empty string body line deve ser decodada como string vazia (bug fix src/tcf) | accepted |
| [0007](0007-comma-in-literals-bug.md) | `,` em literais corrompe decode (separator `*` em ref→lit ambiguo) | **accepted** (welded 2026-05-19) |
| [0008](0008-detect-cadence-numeric-rule.md) | detect_cadence: regra numeric+high-cardinality (H-DA-09b refino) | **accepted** (welded EXP-010 2026-05-19) |
| [0009](0009-obat-trigram-index-optimization.md) | OBAT: hash trigrama index reduz O(N²) a O(N) amortizado (alpha 1.75→1.42, 2.70x em 20k) | **accepted** (welded src/tcf 2026-05-19) |
| [0010](0010-auto-detect-min-len.md) | Auto-detect min_len por coluna (H-DA-11) | **accepted** (canonical welded) |
| [0011](0011-pacote1-weld-canonical.md) | Pacote 1 (Delta-aware) welded canonical em src/tcf (M9 → M10) | **accepted** (welded) |
| [0012](0012-diataxis-naming-local.md) | Diataxis naming local (docs/algorithms, docs/theory) | accepted |
| [0013](0013-multi-column-canonical-api.md) | Multi-column canonical API welded em src/tcf | **accepted** (welded; superseded by 0014) |
| [0014](0014-unified-api-side-outputs.md) | API unificada `encode(list\|dict)` + SideOutputs recipiente | **accepted** (welded) |
| [0015](0015-natures-templated-checked-weld.md) | TemplatedCheckedSpec welded canonical em src/tcf/natures | **accepted** (welded) |
| [0016](0016-hcc-multi-delta-seq-rle.md) | HCC seq-RLE multi-delta (Bug #2 sub-exp 14 fix) | **accepted** (welded) |
| [0017](0017-format-spec-v1-frozen.md) | Format spec v1.0 frozen + versioning policy | accepted (parte "freeze" superseded por 0024 — projeto e' pré-1.0) |
| [0018](0018-v2-format-roadmap.md) | Roadmap de formato v2.0 (fallback identity, dicionario, lossy) | **proposed** (V2-A welded por 0022) |
| [0019](0019-hcc-detect-compositions-topk-prune.md) | Weld do prune top-K em HCC _detect_compositions (H-PERF-06-v2 #15) | accepted |
| [0020](0020-cython-optional-accelerator.md) | Acelerador Cython opcional de _detect_compositions (H-PERF-06-v2 Fase B) | accepted |
| [0021](0021-onedrive-git-corruption-recovery.md) | Incidente OneDrive × `.git`: recuperacao (causa = hipotese) | accepted |
| [0022](0022-v2a-fallback-identity-weld.md) | V2-A fallback identity welded (abre v2.0, `#TCF.7`, opt-in `fallback=True`) | **accepted** |
| [0023](0023-v2-minimal-header-weld.md) | Header v2 minimo welded (`#TCF.7`, opt-in `min_header`: sem espaco + ultima coluna sem size) | **accepted** |
| [0024](0024-pre-1.0-versioning-git-as-compat.md) | Versionamento pré-1.0: minors de dev, git como compatibilidade (supersede freeze de 0017) | **accepted** (refinado por 0028: eixo RELEASE separado do MINOR) |
| [0025](0025-v2b-dictionary-categorical-weld.md) | V2-B dicionario categorico welded (`#TCF.7`, marcador `@`, 13.9% weighted) | **accepted** |
| [0026](0026-structural-split-weld.md) | Split estrutural welded (`#TCF.7`, marcador `%`, 19.39% weighted) | **accepted** |
| [0027](0027-nature-mark-header-self-describing.md) | H-NAT-MARK-01: nature-id viaja no header (self-describing, `#TCF.8`; multi + single-col) | **accepted** (MVP welded 2026-06-24) |
| [0028](0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md) | Versionamento pré-1.0: acoplamento minor↔formato + eixo RELEASE (0.N.x); evita inflacao 0.8.0 com formato #TCF.7 (refina 0024) | **proposed** |
| [0029](0029-version-format-identification-semi-implicit.md) | Identificacao versao/formato: semi-implicito (orfao default + header no desvio + chamada explicita) + major-externo + congelamento 1.0 single-col; discriminador `#TCF.8` 1-char | **proposed** |

## Quando criar ADR

Crie ADR quando:
- Decisao **arquitetural** (afeta multiplos componentes ou versoes futuras)
- Vai mudar comportamento publico (API, formato, convencao)
- Reverter custaria significativo
- Multiplas opcoes foram consideradas e descartadas

NAO crie ADR pra:
- Bug fixes (use commit message + diario)
- Refatoracoes locais
- Tarefas de implementacao (use sub-experimento)

## Como referenciar ADR

- Em outros docs: `[ADR-0003](docs/adr/0003-tripartite-pre-obat-hcc.md)`
- Em codigo (comentario): `# Ver ADR-0003 — tripartite Pre/OBAT/HCC`
- Em ADRs (cross-link): `Supersedes ADR-0001`, `See also ADR-0002`

## Migracao de decisoes antigas

Decisoes anteriores ao ADR system estao em:
- `experiments/lab/dirty/notas/diario/YYYY-MM-DD.md` (cronologico)
- Memorias user (`~/.claude/.../memory/feedback_*.md`, `project_*.md`)

Migrar pra ADR quando: a decisao reaparecer em conversa, OU quando
um novo ADR superseder algo antigo (entao escreve-se ambos pra rastrear).
