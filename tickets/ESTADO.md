# Estado dos tickets

> **Arquivo gerado.** Não editar à mão: a fonte é o `status:` do frontmatter de cada
> ticket. Regenerar com `python scripts/ticket_index.py`. O `README.md` desta pasta é
> outra coisa: lá a curadoria é por TEMA e carrega o histórico do projeto; aqui é só
> a situação de cada um, para quem abre a pasta e precisa saber o que está de pé.

## Bloqueados (2)

| ticket | estado | mexido | assunto |
|---|---|---|---|
| [T-CODE-OUTPUT-SINKS](T-CODE-OUTPUT-SINKS.md) | `P2` deferred | 2026-06-15 | Interface Sink pluggable · **bloqueado por** T-CODE-ENCODER-MANAGER |
| [T-DATA-3-EDGE-QUALITY-FIXTURES](T-DATA-3-EDGE-QUALITY-FIXTURES.md) | `P3` deferred | 2026-06-01 | Plano de dados de borda/defeituosos para os gadgets de qualidade/schema (planejamento, NAO imple · **bloqueado por** T-RECOVER-SCHEMA-MULTI-TABLE |

## Em curso (2)

| ticket | estado | mexido | assunto |
|---|---|---|---|
| [T-STUDY-DATASETH-COMPLETE-SEMANTICS](T-STUDY-DATASETH-COMPLETE-SEMANTICS.md) | `P1` in-progress | 2026-09-01 | fechar semântica hierárquica antes do wire |
| [T-STUDY-HIERARCHY-LINK-ALGEBRA](T-STUDY-HIERARCHY-LINK-ALGEBRA.md) | `P1` in-progress | 2026-09-01 | equivalência dos portadores de vínculo |

## Abertos (27)

| ticket | estado | mexido | assunto |
|---|---|---|---|
| [T-CODE-CORE-CONSOLIDATE](T-CODE-CORE-CONSOLIDATE.md) | `P1` open | 2026-09-01 | fonte única de lógica, menos funções, naming HCC (adeus M8A) |
| [T-PERF-BORDAS-E-MODOS-09](T-PERF-BORDAS-E-MODOS-09.md) | `P1` open | 2026-09-01 | as bordas do TCF e os modos de compressão (rápido × maior); o alvo do .9 |
| [T-QA-8-material-comprobatorio](T-QA-8-material-comprobatorio.md) | `P1` open | 2026-09-01 | T-QA-8, material comprobatório do #TCF.8/0.8.0 (controle → sintéticos → públicos) com telemetria |
| [T-API-SCHEMA-PRESCRITIVO](T-API-SCHEMA-PRESCRITIVO.md) | `P2` open | 2026-09-01 | o objeto Schema (forma longa do `schema=`) como portador do contrato |
| [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md) | `P2` open | 2026-09-01 | flag de controle de paralelismo e uso de CPU (budget do host) |
| [T-CODE-VIEW-SUBTCF-RECORTE](T-CODE-VIEW-SUBTCF-RECORTE.md) | `P2` open | 2026-09-01 | promover H-QUERY-06 a saída TCF da view |
| [T-DOC-MANUAL-FORMAL](T-DOC-MANUAL-FORMAL.md) | `P2` open | 2026-09-01 | manual didático no padrão das ferramentas de dados (índice, quickstart, entradas por tipo) |
| [T-DOC-RELEASE-083-SUPERFICIE](T-DOC-RELEASE-083-SUPERFICIE.md) | `P2` open | 2026-09-01 | reconciliar changelog, status e roadmap com a publicação |
| [T-FLOW-ENCODE-STRATEGIES-TELEMETRY](T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md) | `P2` open | 2026-09-01 | Estratégias de encode (speed/mem) + telemetria sugestiva de ordem |
| [T-FMT-CONTRACT-SIGNATURE](T-FMT-CONTRACT-SIGNATURE.md) | `P2` open | 2026-09-01 | assinatura de contrato para os knobs que não reconstroem a entrada (drop_names, sort_by) |
| [T-FMT-OMIT-OR-DECLARE](T-FMT-OMIT-OR-DECLARE.md) | `P2` open | 2026-07-08 | Contrato de omissão (deduzível / convenção-default / declaração-obrigatória), AVALIAR pré-1.0 |
| [T-HTTP-QUERY-E-VIEW](T-HTTP-QUERY-E-VIEW.md) | `P2` open | 2026-09-01 | o método HTTP QUERY (RFC 10008) como transporte natural do view()/lazy |
| [T-LAB-DIDATICO-PONTA-A-PONTA](T-LAB-DIDATICO-PONTA-A-PONTA.md) | `P2` open | 2026-09-01 | micro-lab do fluxo real (coleta → dataset → schema → encode → cliente/servidor → disponibilizar) |
| [T-OPT-INFERENCE](T-OPT-INFERENCE.md) | `P2` open | 2026-09-01 | base HEX dos sizes |
| [T-STUDY-HIERARCHICAL-TCF](T-STUDY-HIERARCHICAL-TCF.md) | `P2` open | 2026-09-01 | TCF para estrutura hierárquica completa |
| [T-TYPED-SINGLECOL-MODE-HEURISTIC](T-TYPED-SINGLECOL-MODE-HEURISTIC.md) | `P2` open | 2026-09-01 | single-col tipado + modos de corpo (heurística p/ .9) |
| [DECISAO-VIEW-BOOL-TRUTHINESS](DECISAO-VIEW-BOOL-TRUTHINESS.md) | `P3` open | 2026-08-24 | int numa coluna bool passa por truthiness, e a doc promete o contrario |
| [META-STRATA-GOVERNANCE](META-STRATA-GOVERNANCE.md) | `P3` open | 2026-09-01 | atividades recorrentes de governança do método Strata |
| [T-DOC-3-shebang-terminology](T-DOC-3-shebang-terminology.md) | `P3` open-errata-reminder | 2026-09-01 | "shebang" → assinatura de formato / magic number |
| [T-DOC-L10N-REFERENCE](T-DOC-L10N-REFERENCE.md) | `P3` open | 2026-09-01 | os 5 documentos restantes de docs/reference/ em dois idiomas |
| [T-DOC-TIPOS-MISTOS](T-DOC-TIPOS-MISTOS.md) | `P3` open | 2026-09-01 | elaborar a documentação do comportamento de tipos mistos (hoje em post-it) |
| [T-FMT-ESCAPE-COMBINATORIAL-STUDY](T-FMT-ESCAPE-COMBINATORIAL-STUDY.md) | `P3` open | 2026-07-15 | reestudar o escape (combinatório + estratégias de outros mecanismos) |
| [T-FMT-META-STRICT](T-FMT-META-STRICT.md) | `P3` open | 2026-09-02 | o que já fecha por dedução vs o que exige redundância (checksum) |
| [T-FMT-QUOTING-STUDY](T-FMT-QUOTING-STUDY.md) | `P3` open | 2026-07-10 | estudo de quoting/escaping de nomes além do backslash interim (filho de T-FMT-NAME-ESCAPING) |
| [T-SHAPER-NESTED-OUTPUT](T-SHAPER-NESTED-OUTPUT.md) | `P3` open | 2026-09-02 | saída HIERÁRQUICA nativa no Shaper (aninhar via FK, inverso do flat) |
| [T-STUDY-USE-PROFILES](T-STUDY-USE-PROFILES.md) | `P3` open | 2026-09-01 | perfis de uso (transmissão × armazenamento) e a calibração dos vértices |
| [T-TOOL-TCF-FIX-CORRUPTION](T-TOOL-TCF-FIX-CORRUPTION.md) | `P3` open | 2026-09-01 | reparador de .tcf com algum grau de corrupção (ideia, pensar depois) |

## Fechados (68)

| ticket | estado | mexido | assunto |
|---|---|---|---|
| [BUG-BRACKET-CELL-LOSS](BUG-BRACKET-CELL-LOSS.md) | `P1` closed | 2026-07-16 | célula string que é exatamente '[' ou ']' é PERDIDA silenciosamente |
| [BUG-ENCODE-PRIMEIRO-VALOR-NULO](BUG-ENCODE-PRIMEIRO-VALOR-NULO.md) | `P1` closed | 2026-08-25 | `None` na primeira linha estoura o encode multi-col |
| [BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA](BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA.md) | `P1` closed-fixed | 2026-08-28 | coluna mista perde valor, e em dois casos emite wire que não decodifica |
| [BUG-SEQRLE-RANGE-EMPTY-B](BUG-SEQRLE-RANGE-EMPTY-B.md) | `P1` closed | 2026-07-15 | decode(encode(x)) crasha quando um afixo tem sufixo `..`/`...` |
| [BUG-VIEW-NULO-NO-HIERARQUICO](BUG-VIEW-NULO-NO-HIERARQUICO.md) | `P1` closed-fixed | 2026-08-28 | um None numa coluna densa tira a tabela inteira do view() |
| [BUG-VIEW-RECUSA-COLUNA-TIPADA](BUG-VIEW-RECUSA-COLUNA-TIPADA.md) | `P1` closed | 2026-08-23 | uma coluna int ou bool tira a tabela inteira do view() |
| [BUG-VIEW-UMA-STRING-VAZIA](BUG-VIEW-UMA-STRING-VAZIA.md) | `P1` closed-fixed | 2026-08-27 | count e select truncam uma linha vazia |
| [T-API-BOUNDARY-CONTRACTS](T-API-BOUNDARY-CONTRACTS.md) | `P1` closed | 2026-07-17 | contrato flat e fronteira DatasetH |
| [T-CODE-EMPTY-FRAG-INDEX-RT](T-CODE-EMPTY-FRAG-INDEX-RT.md) | `P1` closed | 2026-06-13 | Bug de RT no core M10 (string vazia desloca index de fragmento HCC) |
| [T-CODE-LAZY-VIEW-PROMOTE](T-CODE-LAZY-VIEW-PROMOTE.md) | `P1` closed | 2026-06-21 | Promover lazy view do gadget pro core (tcf.view) |
| [T-CODE-PACOTE1-WELD-CANONICAL](T-CODE-PACOTE1-WELD-CANONICAL.md) | `P1` closed | 2026-05-22 | Welding canonical Pacote 1 (delta-aware) em src/tcf |
| [T-CODE-RT-EDGES](T-CODE-RT-EDGES.md) | `P1` closed-fixed | 2026-07-05 | 2 violações de RT em bordas (seq-RLE trailing-space + \n embutido) |
| [T-CODE-TCF8H-JSON-PARITY](T-CODE-TCF8H-JSON-PARITY.md) | `P1` closed | 2026-09-02 | o que falta pra fechar "hierarquia" (paridade JSON) + 1 capacidade exclusiva |
| [T-CODE-TCF8H-WELD](T-CODE-TCF8H-WELD.md) | `P1` closed-welded | 2026-09-02 | weld do codec hierárquico #TCF.8H no src/tcf (feature do .8) |
| [T-DOC-LAZY-REFERENCE](T-DOC-LAZY-REFERENCE.md) | `P1` closed | 2026-06-21 | Reference Diátaxis da API tcf.view (A5 do plano 0.8) · **bloqueado por** T-CODE-LAZY-VIEW-PROMOTE |
| [T-EXP-DATASETH-S0-S3](T-EXP-DATASETH-S0-S3.md) | `P1` closed | 2026-07-16 | corpus, oráculo, IR e álgebra de vínculos |
| [T-EXP-MULTI-COL-SCALING](T-EXP-MULTI-COL-SCALING.md) | `P1` closed-welded-canonical | 2026-05-23 | Port multi-column pra canonical M10 + real-world |
| [T-FMT-NAME-ESCAPING](T-FMT-NAME-ESCAPING.md) | `P1` closed-parcial (interim backslash = entrega do .8; estudo quoting -> filho T-FMT-QUOTING-STUDY, .9) | 2026-07-10 | Escape/quoting de nomes de coluna (e chaves de hierarquia) no meta do header |
| [T-H-PERF-06-V2-T01-WELD-15](T-H-PERF-06-V2-T01-WELD-15.md) | `P1` closed-done | 2026-05-31 | T-H-PERF-06-V2-T01, Weld do candidato #15 (topK prune) em src/tcf |
| [T-H-PERF-06-V2-T02-CYTHON](T-H-PERF-06-V2-T02-CYTHON.md) | `P1` closed-done | 2026-05-31 | T-H-PERF-06-V2-T02, Acelerador Cython opcional de _detect_compositions (Fase B) |
| [T-QA-083-REVALIDACAO](T-QA-083-REVALIDACAO.md) | `P1` closed | 2026-08-29 | reavaliar a superfície 0.8.3 com evidência em disco |
| [T-REGRESSION-REAL-WORLD](T-REGRESSION-REAL-WORLD.md) | `P1` closed-done | 2026-05-30 | Estender regression suite para amostras real-world (gate prune algoritmico) |
| [T-REL-08-CLOSEOUT](T-REL-08-CLOSEOUT.md) | `P1` closed | 2026-08-23 | ordem por ROI para fechar o núcleo 0.8 |
| [T-REVAL-H-DA-01-06-10](T-REVAL-H-DA-01-06-10.md) | `P1` closed | 2026-05-21 | Revalidacao categoria B (Pacote 1 hipoteses confirmada-empirica nao testadas em real-world) |
| [T-SHAPER-SCIENTIFIC-GATING](T-SHAPER-SCIENTIFIC-GATING.md) | `P1` closed-done | 2026-05-30 | Gate cientifico de uso do shaper (tests estatisticos assertados) |
| [T-SPEC-DEEPDIVE-08](T-SPEC-DEEPDIVE-08.md) | `P1` closed-decided | 2026-09-02 | investigação de fundo dos specs (o que comprime, CNPJ além do básico, compilador/un-weld); plano |
| [T-SPEC-STATUS-08](T-SPEC-STATUS-08.md) | `P1` closed-decided | 2026-09-02 | status dos specs (2 abordagens) antes do teste em massa; decisão do que fecha no .8 |
| [BUG-BB-CR-CRU](BUG-BB-CR-CRU.md) | `P2` closed-fixed | 2026-08-30 | a união bool+str emite CR cru em wire LF-only |
| [BUG-CHAVE-VAZIA-POSICIONAL](BUG-CHAVE-VAZIA-POSICIONAL.md) | `P2` closed | 2026-08-21 | [...]} volta {"0": [...]}, único caso onde o TCF ALTERA |
| [BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA](BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA.md) | `P2` closed-fixed | 2026-08-28 | distinct e n_unique inventam um elemento em coluna de 0 linhas |
| [BUG-VIEW-OBJETO-NAO-RETANGULAR](BUG-VIEW-OBJETO-NAO-RETANGULAR.md) | `P2` closed-fixed | 2026-08-28 | a view responde número sobre uma tabela que não existe, e depois acusa corrupção de um blob ínte |
| [META-ESCAPE-DEDUCTION](META-ESCAPE-DEDUCTION.md) | `P2` closed | 2026-05-21 | Pacote 2 (H-ED-01..04, suppressao implicita de escapes) |
| [T-CI-3-pyx-compiled-byte-gate](T-CI-3-pyx-compiled-byte-gate.md) | `P2` closed-done | 2026-07-05 | T-CI-3, Gate byte-canonical do caminho Cython COMPILADO (detect.pyx) |
| [T-CLEAN-2-strata-defrag](T-CLEAN-2-strata-defrag.md) | `P2` closed-backlog-done-db2-owner-pending | 2026-07-01 | Defragmentação da biblioteca (higiene de superfície §3/§5 + índices §2) |
| [T-CLEAN-3-org-defrag-pre-0.8](T-CLEAN-3-org-defrag-pre-0.8.md) | `P2` closed-done (follow-up deferido: consolidacao STATUS pos-publicacao-0.8) | 2026-07-09 | T-CLEAN-3, defrag de organização (docs/tickets/diário) pós-#TCF.8-default, pré-review 0.8 |
| [T-CODE-DESCAPAR-V2B](T-CODE-DESCAPAR-V2B.md) | `P2` closed-parcial (forma A welded no .8; formas B/C -> .9, ver ROADMAP Tier 1) | 2026-07-10 | Descapar o V2-B (dict como candidato do min() p/ high-card) |
| [T-CODE-ENCODER-MANAGER](T-CODE-ENCODER-MANAGER.md) | `P2` closed | 2026-06-15 | Reviver D13 (paralelismo + sinks) |
| [T-CODE-H-DA-11c-features-unificadas](T-CODE-H-DA-11c-features-unificadas.md) | `P2` closed | 2026-05-22 | T-CODE-H-DA-11c, Consolidar pre-pass features (ColumnFeatures unificado) |
| [T-CODE-HCC-ATOM-DETECTION-REFINE](T-CODE-HCC-ATOM-DETECTION-REFINE.md) | `P2` closed-superseded-by-adr-0016 | 2026-05-24 | Bug #1 sub-exp 14 (atom secundario nao criado) |
| [T-CODE-HCC-MULTI-DELTA-FIX](T-CODE-HCC-MULTI-DELTA-FIX.md) | `P2` closed-welded-canonical | 2026-05-24 | Bug #2 sub-exp 14 (seq-RLE rejeita multi-run delta) |
| [T-CODE-LEGACY-PRUNE-PRE-07](T-CODE-LEGACY-PRUNE-PRE-07.md) | `P2` closed | 2026-06-24 | Podar fallbacks/legado pré-0.7 do core (rumo a 1.0) |
| [T-DATA-2-RECEITA-CNPJ](T-DATA-2-RECEITA-CNPJ.md) | `P2` closed-done | 2026-06-02 | Dataset real de CNPJ (Receita Federal open data) para gating ecologico das natures |
| [T-DATA-TRANSMISSION-GROUPING](T-DATA-TRANSMISSION-GROUPING.md) | `P2` closed-done | 2026-07-10 | Agrupar datasets por cenário de transmissão (matriz 3-eixos) |
| [T-DIST-PYPI-NAME](T-DIST-PYPI-NAME.md) | `P2` closed-done | 2026-06-16 | Capturar nome de distribuicao no PyPI |
| [T-DIST-RELEASE-0.8.0](T-DIST-RELEASE-0.8.0.md) | `P2` closed | 2026-08-23 | Release do pacote 0.8.0 (#TCF.8 default, ADR-0032) · **bloqueado por** T-REL-08-CLOSEOUT |
| [T-EXP-H-DA-11](T-EXP-H-DA-11.md) | `P2` closed | 2026-05-22 | Auto-detect min_len otimo por coluna |
| [T-EXP-H-GDICT-01](T-EXP-H-GDICT-01.md) | `P2` closed-insufficient-generalization | 2026-07-01 | Caracterizar cross-dict / dicionário global (B1; B2/B3 → 0.9) |
| [T-EXP-H-PERF-05d](T-EXP-H-PERF-05d.md) | `P2` closed | 2026-05-23 | Counter incremental em HCC _detect_compositions |
| [T-EXP-PACOTE5-T03-ENUMERATED](T-EXP-PACOTE5-T03-ENUMERATED.md) | `P2` closed | 2026-05-23 | enumerated nature canonical |
| [T-FMT-HEADER-BASE-HEX](T-FMT-HEADER-BASE-HEX.md) | `P2` closed-welded | 2026-07-10 | Base HEX implícita dos byte-sizes do header (decimal só como comando de inspeção/IO) |
| [T-FMT-TCF8H-HEADER](T-FMT-TCF8H-HEADER.md) | `P2` closed-decided (slot H reservado no .8, ADR-0031; codec -> trilho .9 via T-STUDY-HIERARCHICAL-TCF) | 2026-07-10 | Decisões de formato do cabeçalho TCF.8H (hierárquico) |
| [T-RECOVER-SCHEMA-MULTI-TABLE](T-RECOVER-SCHEMA-MULTI-TABLE.md) | `P2` closed-done | 2026-06-08 (Fases 1-4 FEITAS: fk_detect + date_check + sideouts_quality + CLI; ~40 testes; gadget funcional end-to-end) | Gadget auxiliar de schema multi-tabela (alertas, NAO conserta) |
| [T-REVAL-H-DA-07](T-REVAL-H-DA-07.md) | `P2` closed | 2026-05-22 | Revalidacao H-DA-07 (OBAT shape-preserve) em real-world |
| [BUG-MENSAGEM-COLUNA-VAZIA-MISTA](BUG-MENSAGEM-COLUNA-VAZIA-MISTA.md) | `P3` closed-fixed | 2026-08-30 | fail-loud omite o nome válido vazio |
| [BUG-VIEW-ORFAO-SEM-MAGIC](BUG-VIEW-ORFAO-SEM-MAGIC.md) | `P3` closed-fixed | 2026-08-28 | a view recusa o wire sem magic que o decode lê, e culpa um legado irrelevante |
| [DECISAO-GROUPING-SEMANTICA](DECISAO-GROUPING-SEMANTICA.md) | `P3` closed-decided | 2026-08-26 | onde o agrupamento do TCF diverge de SQL, pandas e polars |
| [T-CI-1-github-actions](T-CI-1-github-actions.md) | `P3` closed | 2026-05-23 | T-CI-1, GitHub Actions CI (pre-commit lint; tests refactor follow-up) |
| [T-CI-2-tests-refactor](T-CI-2-tests-refactor.md) | `P3` closed | 2026-05-23 | T-CI-2, Refactor tests CI-friendly (archive v0.5 + marker requires_data + new core_rt) |
| [T-CLEAN-1-pre-commit-hooks](T-CLEAN-1-pre-commit-hooks.md) | `P3` closed | 2026-05-23 | T-CLEAN-1, Adicionar pre-commit (detect-secrets, ruff, basicos) |
| [T-CODE-LAYERED-PIPELINE](T-CODE-LAYERED-PIPELINE.md) | `P3` closed | 2026-06-15 | Toggle infrastructure + online adaptive + fallback |
| [T-CODE-SCHEMA-BUILDER](T-CODE-SCHEMA-BUILDER.md) | `P3` closed | 2026-06-15 | Orquestrador que consume SideOutputs |
| [T-DATA-1-datasets-financeiros-cientificos](T-DATA-1-datasets-financeiros-cientificos.md) | `P3` closed | 2026-06-13 | T-DATA-1, Datasets financeiros/cientificos canonicos (Online Retail, Beijing PM2.5, Wine Quality |
| [T-DATA-4-TPCH-PART-SAMPLES](T-DATA-4-TPCH-PART-SAMPLES.md) | `P3` closed-done | 2026-06-01 | Emitir samples committed de part/partsupp do TPC-H (categoria hierarquica observavel) |
| [T-DOC-1-citation-cff](T-DOC-1-citation-cff.md) | `P3` closed | 2026-05-23 | T-DOC-1, Adicionar CITATION.cff e preparar DOI (Zenodo) |
| [T-DOC-2-diataxis-naming](T-DOC-2-diataxis-naming.md) | `P3` closed | 2026-05-23 | T-DOC-2, Explicitar mapeamento docs/algorithms,theory → Diataxis (reference,explanation) |
| [T-EXP-H-DA-09c-d-e](T-EXP-H-DA-09c-d-e.md) | `P3` closed | 2026-05-23 | Refinos detect_cadence (threshold/multivariada/adaptativo) |
| [T-EXP-NATUREZAS-RARAS-EXPLORACAO](T-EXP-NATUREZAS-RARAS-EXPLORACAO.md) | `P3` closed | 2026-05-23 | Naturezas #5 (range) e #8 (arredondamento) |
| [T-FIX-SHAPER-STRATIFY-TEST](T-FIX-SHAPER-STRATIFY-TEST.md) | `P4` closed-done | 2026-05-27 | Corrigir expectativa do test_stratify_proportional |

## Parados (3)

| ticket | estado | mexido | assunto |
|---|---|---|---|
| [T-SHAPER-CODE-HARDENING](T-SHAPER-CODE-HARDENING.md) | `P2` deferred | 2026-06-15 | Hardening de codigo do shaper (escala, dedup, bugs latentes) |
| [T-CODE-PLAN-CONTRACT](T-CODE-PLAN-CONTRACT.md) | `P3` deferred | 2026-06-15 | Plan dataclass (group_by/order/batch_size) |
| [T-RECOVER-LLM-SCHEMA-MODE](T-RECOVER-LLM-SCHEMA-MODE.md) | `P3` deferred | 2026-06-15 (PARK pos-0.7 / spin-off; escopo refinado 2026-05-27: gadget paralelo, formato LLM-binary, alertas only) | Gadget LLM (schema + SQL gen, formato LLM-binary) |

## Outros (6)

> `status:` fora do vocabulário conhecido. Aparecem aqui em vez de sumir.

| ticket | estado | mexido | assunto |
|---|---|---|---|
| [META-DOCS-V05-OBSOLETE](META-DOCS-V05-OBSOLETE.md) | ? |  | META-DOCS-V05-OBSOLETE |
| [META-EXP-FORMAT](META-EXP-FORMAT.md) | ? |  | META-EXP-FORMAT |
| [META-NAMING](META-NAMING.md) | ? |  | META-NAMING |
| [META-PERF-PHASE2](META-PERF-PHASE2.md) | ? |  | META-PERF-PHASE2 |
| [META-THEORY-MOVE](META-THEORY-MOVE.md) | ? |  | META-THEORY-MOVE |
| [META-TYPE-ENCODERS](META-TYPE-ENCODERS.md) | ? |  | META-TYPE-ENCODERS |

---

108 tickets no total.
