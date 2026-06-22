# Tickets — TCF v0.6

Tickets de planejamento + acompanhamento do projeto. Cada ticket tem
status (`open` / `in-progress` / `closed`), criterios de aceite, e
referencias a commits que o resolveram.

## Convencao de IDs

- `META-X` — meta-tickets que agrupam decisoes/sub-tarefas
- `T-NAME-N` — naming (terminologia + identidade)
- `T-DOC-N` — documentacao
- `T-EXP-N` — experimentos (clean lab)
- `T-CODE-N` — codigo (src/)
- `T-CLEAN-N` — limpeza/reorganizacao

## Tickets

| ID | Tema | Status |
|---|---|---|
| [META-NAMING](META-NAMING.md) | Naming oficial (TCF/OBAT/HCC) | **CLOSED 2026-05-17** |
| [META-DOCS-V05-OBSOLETE](META-DOCS-V05-OBSOLETE.md) | Fase 2: archivar v0.5-exclusivo em docs/ | **CLOSED 2026-05-17** |
| [META-THEORY-MOVE](META-THEORY-MOVE.md) | Mover hipoteses/teoria dirty → docs/theory/ + sintese das 3 estrategias | **CLOSED 2026-05-17** |
| [META-EXP-FORMAT](META-EXP-FORMAT.md) | Template validacao vs comparativo + reorganizar EXP-008 | **CLOSED 2026-05-15** |
| [META-TYPE-ENCODERS](META-TYPE-ENCODERS.md) | Grande plano: pre-tx por natureza + estudos camada algoritmo (T01 absorvido em Pacote 1; T02-T07 + L01-L05 adiados) | **OPEN 2026-05-15** (atualizado 2026-05-19) |
| [META-PERF-PHASE2](META-PERF-PHASE2.md) | Pacote 4 fase 2: lineitem full 60175 (executado, 21min real); H-PERF-04/05/06 todos adiados com justificativa documentada | **CLOSED-PARCIAL 2026-05-20** |
| [META-ESCAPE-DEDUCTION](META-ESCAPE-DEDUCTION.md) | Pacote 2: H-ED-01..04 caracterizacao mediu 0.13%-1.13% real-world (lower bound), critério aceite 5%. Primeiro ticket YAML frontmatter validou metodologia. | **CLOSED-INSUFFICIENT-GAIN 2026-05-21** |
| [T-REVAL-H-DA-01-06-10](T-REVAL-H-DA-01-06-10.md) | Revalidacao Categoria B (revisao 2026-05-21): H-DA-06 SUBSUMIDA, H-DA-01 marginal (1.36%), H-DA-10 CONFIRMADA inesperadamente (9.92% real-world). Nova H-DA-11 decorrente. | **CLOSED-COMPLETED-WITH-SURPRISES 2026-05-21** |
| [T-EXP-H-DA-11](T-EXP-H-DA-11.md) | Auto-detect min_len por coluna: heuristica v3 captura 9.87% real-world em src/tcf canonical welded (ADR-0010). M9 baseline 1615B preservado EXATO, RT 100% (9/9 + 57/57). | **CLOSED-CANONICAL-WELDED 2026-05-22** |
| [T-CODE-H-DA-11c](T-CODE-H-DA-11c-features-unificadas.md) | ColumnFeatures unificado: novo `src/tcf/column_features.py` + refactor `auto_min_len.py` + `encoder.py`. Output IDENTICO ao pre-refactor (zero-risk). Prepara terreno pra T02-T07 e weld futuro de detect_cadence canonical. | **CLOSED-REFACTOR-COMPLETED 2026-05-22** |
| [T-CODE-PACOTE1-WELD-CANONICAL](T-CODE-PACOTE1-WELD-CANONICAL.md) | Pacote 1 delta-aware welded canonical em src/tcf (ADR-0011). Novos modulos auto_cadence + obat_shape + hcc_seqrle. **M9 (1615B) → M10 (1523B) baseline**. Real-world ganho 11.73% weighted, RT 100% (9/9 + 20/20 + 57/57). | **CLOSED-WELDED-CANONICAL-M10 2026-05-22** |
| [T-REVAL-H-DA-07](T-REVAL-H-DA-07.md) | Revalidacao real-world H-DA-07 (OBAT shape-preserve): zero regressao significativa em 66 cols (62/66 sem mudanca via gating). 2 wins enormes (c_name -98.19%, D9 -48%), 2 losses pequenas (l_extendedprice +0.65%, c_acctbal +0.20%). | **CLOSED-CONFIRMED-REAL-WORLD 2026-05-22** |
| [T-EXP-H-PERF-05d](T-EXP-H-PERF-05d.md) | Counter incremental HCC `_detect_compositions`: Fase 1 profile GO (rebuild=46% _dc, 0.3% lines/iter). Fase 2 prototype: 37/41 byte-canonical OK, 4 divergencias em datetime TPC-H (0.08% net) por ordem de iteracao do Counter. Welding adiado (precisaria fix byte-canonical OR aceitar M11). | **CLOSED-VALIDATED-WITH-BYTE-DIVERGENCE 2026-05-23** |
| [T-EXP-PACOTE5-T03-ENUMERATED](T-EXP-PACOTE5-T03-ENUMERATED.md) | Pacote 5 enumerated nature: caracterizacao 37 low-card cols mostrou M10 ja' captura via dedup + seq-RLE (-6.52% em low-card RW, -2.28% weighted total). Encoder explicit seria PIOR em runs adjacentes (l_linestatus -141%), so' ganharia em valores longos sem runs (c_mktsegment +30%). | **CLOSED-NO-GO-M10-SUFICIENTE 2026-05-23** |
| [T-EXP-H-DA-09c-d-e](T-EXP-H-DA-09c-d-e.md) | Refinos detect_cadence: varreu threshold {0.5, 0.6, 0.7, 0.8} em 66 cols. Thr 0.7 atual e' otimo (0.5/0.6 dao -3.06% regressao RW; 0.8 idêntico). H-DA-09d/e adiados (heuristica ja' calibrada). | **CLOSED-NO-GO-THRESHOLD-07-OTIMO 2026-05-23** |
| [T-DOC-1-citation-cff](T-DOC-1-citation-cff.md) | CITATION.cff criado com Leonardo Marques Souza, v0.6, MIT, github.com/LeoPR/TCF. README "How to cite" adicionado. DOI Zenodo defer ate' v1.0/paper. | **CLOSED-CITATION-CFF-CREATED-DOI-DEFERRED 2026-05-23** |
| [T-DOC-2-diataxis-naming](T-DOC-2-diataxis-naming.md) | ADR-0012 criado documentando mapeamento docs/algorithms→reference, docs/theory→explanation. Tutorials defer ate' 1o tutorial real. MAP.md atualizado. | **CLOSED-ADR-0012-CREATED 2026-05-23** |
| [T-CLEAN-1-pre-commit-hooks](T-CLEAN-1-pre-commit-hooks.md) | .pre-commit-config.yaml criado (ruff + detect-secrets + basicos + custom no-cache-dirs). pyproject.toml + README dev setup atualizados. `pre-commit install` pending owner. | **CLOSED-CONFIG-CREATED-INSTALL-PENDING 2026-05-23** |
| [T-EXP-NATUREZAS-RARAS-EXPLORACAO](T-EXP-NATUREZAS-RARAS-EXPLORACAO.md) | Exploracao naturezas #5 (range) e #8 (suffix arredondamento) em Adult+TPC-H. #8 -4.45% weighted (M10 ja' captura via dedup). #5 +1.08% marginal. 3 cols com potencial isolado (l_quantity, l_linenumber, age) mas peso baixo. Padroes financeiros reais precisariam dataset dedicado. | **CLOSED-NO-GO-PADROES-RAROS-EM-DATASETS-GERAIS 2026-05-23** |
| [T-CI-1-github-actions](T-CI-1-github-actions.md) | Workflow .github/workflows/ci.yml (lint via pre-commit). Tests job ativado em T-CI-2 (mesma data). Badge CI no README. | **CLOSED 2026-05-23 (Fase 1+2)** |
| [T-CI-2-tests-refactor](T-CI-2-tests-refactor.md) | Refactor tests CI-friendly: archive 5 v0.5 broken pra _archive_v05/, marker requires_data, 31 tests novos test_core_rt.py (M10 baseline 1523B + edge cases + Pacote 3 fix). CI ativado matrix py 3.10/3.11/3.12. | **CLOSED-REFACTOR-COMPLETED 2026-05-23** |
| [T-DATA-1-datasets-financeiros-cientificos](T-DATA-1-datasets-financeiros-cientificos.md) | Scripts setup pra 3 datasets UCI/OpenML canonicos: Online Retail (~45MB, padroes .99 #8), Beijing PM2.5 (~2MB, range narrow PRES #5), Wine Quality (~100KB, decimais cientificos). READMEs + metadata. Download pendente owner. | **OPEN 2026-05-23 (scripts criados, download pendente)** |
| [T-EXP-MULTI-COL-SCALING](T-EXP-MULTI-COL-SCALING.md) | Multi-col welded canonical em src/tcf (ADR-0013, Opcao A). src/tcf/multi.py novo + encode_table/decode_table API publica. D17a 322B INVARIANT preservado. 17/17 tests novos (test_multi_col_rt.py). 9 tabelas real-world: -33.02% weighted vs raw, RT 9/9. | **CLOSED-WELDED-CANONICAL 2026-05-23** |
| (ADR-0014 welded direto) | API unificada `encode(list\|dict)` + `decode(text)` por dispatch + `SideOutputs` recipiente. ADR-0013 superseded (mas valido historicamente). encode_table/decode_table viram deprecated aliases. D17a 322B preservado. 117 passed + 1 xfailed. | **CLOSED-WELDED-CANONICAL 2026-05-24** |
| [T-CODE-ENCODER-MANAGER](T-CODE-ENCODER-MANAGER.md) | **Fase 1+1b WELDED**: `encode(data, parallel=False\|True\|N)` via ProcessPoolExecutor + work-stealing (sorted desc por workload, submit+as_completed). 14 tests, D17a 322B INVARIANT byte-canonical em parallel. Benchmark: customer 0.83x, orders 1.23x (4w)/1.30x (8w). Conclusao: gargalo eh IPC overhead Windows spawn (nao load imbalance). Speedup teto ~1.3x sem dependencia externa. Fases 1c/2-4 pendentes. | **OPEN-FASES-1+1B-WELDED 2026-05-24** |
| [T-CODE-OUTPUT-SINKS](T-CODE-OUTPUT-SINKS.md) | Contract `Sink` pluggable (Protocol), built-in sinks (File/MultiFile/Memory), streaming sinks (HTTP/TCP). Refactor scripts/writers/. Bloqueado por T-CODE-ENCODER-MANAGER. | **OPEN P2 2026-05-24** |
| [T-CODE-PLAN-CONTRACT](T-CODE-PLAN-CONTRACT.md) | `Plan` dataclass (group_by/order/batch_size/batch_unit) — contrato D11/D13. Habilita ordenacao reversivel O-FMT-01..04 e SQL->Plan (D8). | **OPEN P3 2026-05-24** |
| [T-CODE-SCHEMA-BUILDER](T-CODE-SCHEMA-BUILDER.md) | **Fase 1+2 WELDED**: `src/tcf/schema.py` novo com `build_schema(data)` orquestrador + `ColumnSchema`/`TableSchema` dataclasses + `to_dict`/`to_json`. 24/24 tests passing (D17a 322B INVARIANT preservado, ColumnFeatures/cadence/min_len/seq_rle_runs reaproveitados via SideOutputs). `natures` placeholder vazio pra Fase 3 (META-TYPE-ENCODERS T02-T07). | **OPEN-FASES-1+2-WELDED 2026-05-24** |
| [T-CODE-EMPTY-FRAG-INDEX-RT](T-CODE-EMPTY-FRAG-INDEX-RT.md) | **[probatório] Bug de RT no core M10** (achado na caracterizacao V2-A): string vazia desloca o index de fragmento HCC → back-ref posterior corrompe/crasha. 2 modos (frag-index off-by-one em syntax._parse_decl + rstrip comendo vazio final em hcc_seqrle). Fix decode-only/byte-safe, 12 reproducers pinados, 332 passed, D1-D9=1523B preservado. | **CLOSED 2026-06-13** |
| [T-DIST-PYPI-NAME](T-DIST-PYPI-NAME.md) | Capturar nome de distribuicao no PyPI. `tcf` TOMADO (Tencent SCF); `tcf-format` e `tabular-compact-format` LIVRES (checado 2026-06-14). Recomendado `tcf-format` mantendo `import tcf`. Owner reserva (placeholder 0.0.1 ou release 0.7.0). | **OPEN P2 2026-06-14** |
| [T-CLEAN-2-strata-defrag](T-CLEAN-2-strata-defrag.md) | **[probatório]** Defragmentacao da biblioteca (auditoria Strata 2026-06-18): higiene de superficie (§3/§5 — rotulos/numeros stale: CLAUDE v0.6, README "425 passed", MEMORY #TCF.6, links quebrados) + backlog (docs/theory dup §5, Pacote 1 maturacao §7, tombstones §3, MAP/tickets-location §2). Quick wins + backlog deferido; `src/tcf` intocado. | **IN-PROGRESS P2 2026-06-18** (QW-1..5 feitos; backlog DB-* aberto) |
| [META-STRATA-GOVERNANCE](META-STRATA-GOVERNANCE.md) | **[dispositivo]** Atividades recorrentes/cadencia do metodo Strata (nao-defrag): G-1 maturacao §7 (-> T-CLEAN-2), G-2 pass de rotulo §3-bis, G-3 re-verify L2 (2026-09-01), G-4 revisao periodica completa (~60-90d). + gatilho L0-check antes de mudanca grande. Lembrete vivo, proporcional (§9). | **OPEN P3 2026-06-18** |
| [T-CODE-LAZY-VIEW-PROMOTE](T-CODE-LAZY-VIEW-PROMOTE.md) | **A4 do plano 0.8**: promove a view lazy do gadget `scripts/tcf_lazy/` -> `src/tcf/view.py` (camada read-only; `from tcf import view`), shim de compat mantido. Aditivo, zero regressao byte-canonical (D1-D9=1523B/D17a=303B/RW=89616B), 380 passed. Versao segue 0.7.1 (bump em C). | **CLOSED 2026-06-21** |
| [T-DOC-LAZY-REFERENCE](T-DOC-LAZY-REFERENCE.md) | **A5 do plano 0.8**: reference Diataxis de `tcf.view` (`docs/reference/lazy-view.md`), marcar estavel (L1-L4) vs experimental (`agg_by`/L5 -> H-QUERY-04/0.9). | **OPEN P1 2026-06-21** (blocked-by A4, feito) |
| [T-EXP-H-GDICT-01](T-EXP-H-GDICT-01.md) | **B1 do plano 0.8**: caracterizar cross-dict / dicionario global (lab read-only, >=5 reais, 3 bracos: textual/brotli/latencia-lazy). Gate >=15%/2-reais OU estrutural. Segurado ate' A4 (feito). | **OPEN P2 2026-06-21** |
| [T-DIST-RELEASE-0.8.0](T-DIST-RELEASE-0.8.0.md) | **C do plano 0.8**: bump pacote 0.8.0 (!= formato #TCF.8, ADR-0024) + CHANGELOG/STATUS/ROADMAP/MAP + tag v0.8.0 via Trusted Publishing. | **BLOCKED P2 2026-06-21** (by A4✓/A5/B1) |

## Politica

- Cada ticket "closed" referencia commit(s) que o resolveram.
- Antes de deletar/mover arquivos: garantir push ao GitHub.
- Recuperabilidade via `git log` / `git show`.

## Convencao pra tickets novos (recomendacao 2026-05-21)

Tickets futuros devem usar YAML frontmatter pra serem indexaveis
por `scripts/index.py` e parseaveis por IA. Existentes (fechados)
ficam como estao — imutabilidade.

```yaml
---
title: T-EXP-N — Tema curto
status: open | in-progress | blocked | deferred | absorbed | closed | superseded
priority: P0 | P1 | P2 | P3        # opcional
created: YYYY-MM-DD
updated: YYYY-MM-DD
blocked-by: [TICKET-XYZ]            # opcional, grafo de dependencia
related:
  - docs/adr/0000-...md
  - experiments/lab/clean/EXP-NNN-...
---
```

Conteudo do ticket cubra estes movimentos (nomes livres):
contexto / motivacao → hipotese ou pergunta → plano → criterio de
aceite (KR-style mensuravel: "X% reducao", "RT 100%") → riscos →
conexoes → **updates datados inline** (lab notebook tradition;
preferivel a comments thread porque versiona em git).

Referencia da metodologia subjacente: [`../../README.methodology.md`](../../README.methodology.md) §3.8.
