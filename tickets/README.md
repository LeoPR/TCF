# Tickets: TCF (formato #TCF.8 default, ADR-0032)

> ## Antes de abrir ticket de DIREÇÃO, consulte os dois registries
>
> Eles guardam o que já foi pensado e **não** são tickets, por isso somem da leitura e a
> ideia acaba re-registrada como se fosse nova (aconteceu em 2026-08-23 com armazenamento:
> `O-FMT-20` e `H-QUERY-04` já cobriam, com o princípio decidido).
>
> | registry | o que guarda |
> |---|---|
> | [`roadmap-hipoteses.md`](../experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md) | **hipóteses `H-*`** por pacote: o que foi testado, confirmado, refutado ou adiado |
> | [`futuras-otimizacoes-formato.md`](../experiments/lab/dirty/notas/2026-05/futuras-otimizacoes-formato.md) | **otimizações `O-FMT-*`** de formato: registradas com o enquadramento do owner |
>
> Regra: ideia de direção → procure nos dois **primeiro**. Se já existe, **estenda** o
> registro; não abra ticket paralelo (Strata §5, autoridade única).


> **Procurando o ESTADO de um ticket?** [`ESTADO.md`](ESTADO.md) lista todos por situação
> (bloqueado, em curso, aberto, fechado, parado), gerado do frontmatter. Esta página é outra
> coisa: a curadoria por TEMA, com o histórico de cada linha de trabalho.

Tickets de planejamento + acompanhamento do projeto. Cada ticket tem
status (`open` / `in-progress` / `closed`), criterios de aceite, e
referencias a commits que o resolveram.

## Convencao de IDs

- `META-X`: meta-tickets que agrupam decisoes/sub-tarefas
- `T-NAME-N`: naming (terminologia + identidade)
- `T-DOC-N`: documentacao
- `T-EXP-N`: experimentos (clean lab)
- `T-CODE-N`: codigo (src/)
- `T-CLEAN-N`: limpeza/reorganizacao

## Tickets

| ID | Tema | Status |
|---|---|---|
| [META-NAMING](META-NAMING.md) | Naming oficial (TCF/OBAT/HCC) | **CLOSED 2026-05-17** |
| [META-DOCS-V05-OBSOLETE](META-DOCS-V05-OBSOLETE.md) | Fase 2: archivar v0.5-exclusivo em docs/ | **CLOSED 2026-05-17** |
| [META-THEORY-MOVE](META-THEORY-MOVE.md) | Mover hipoteses/teoria dirty → docs/theory/ + sintese das 3 estrategias | **CLOSED 2026-05-17** |
| [META-EXP-FORMAT](META-EXP-FORMAT.md) | Template validacao vs comparativo + reorganizar EXP-008 | **CLOSED 2026-05-15** |
| [META-TYPE-ENCODERS](META-TYPE-ENCODERS.md) | Grande plano: pre-tx por natureza + estudos camada algoritmo (T01 absorvido em Pacote 1; T02-T07 + L01-L05 adiados) | **PARKED** pos-0.7/v2.0 |
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
| [T-CI-3-pyx-compiled-byte-gate](T-CI-3-pyx-compiled-byte-gate.md) | Gate Cython compilado: build obrigatório no job `accel`, `accelerated=True`, byte-equivalência `.pyx`↔pure-Python + regressão/real-world. Estratégia multi-plataforma permanece critério do release. | **CLOSED-DONE 2026-07-05** |
| [T-DATA-1-datasets-financeiros-cientificos](T-DATA-1-datasets-financeiros-cientificos.md) | Scripts setup pra 3 datasets UCI/OpenML canonicos: Online Retail (~45MB, padroes .99 #8), Beijing PM2.5 (~2MB, range narrow PRES #5), Wine Quality (~100KB, decimais cientificos). READMEs + metadata. Download pendente owner. | closed (os 3 datasets estão em `<data_root>/`, com metadata) |
| [T-EXP-MULTI-COL-SCALING](T-EXP-MULTI-COL-SCALING.md) | Multi-col welded canonical em src/tcf (ADR-0013, Opcao A). src/tcf/multi.py novo + encode_table/decode_table API publica. D17a 322B INVARIANT preservado. 17/17 tests novos (test_multi_col_rt.py). 9 tabelas real-world: -33.02% weighted vs raw, RT 9/9. | **CLOSED-WELDED-CANONICAL 2026-05-23** |
| (ADR-0014 welded direto) | API unificada `encode(list\|dict)` + `decode(text)` por dispatch + `SideOutputs` recipiente. ADR-0013 superseded (mas valido historicamente). encode_table/decode_table viram deprecated aliases. D17a 322B preservado. 117 passed + 1 xfailed. | **CLOSED-WELDED-CANONICAL 2026-05-24** |
| [T-CODE-ENCODER-MANAGER](T-CODE-ENCODER-MANAGER.md) | **Fase 1+1b WELDED**: `encode(data, parallel=False\|True\|N)` via ProcessPoolExecutor + work-stealing (sorted desc por workload, submit+as_completed). 14 tests, D17a 322B INVARIANT byte-canonical em parallel. Benchmark: customer 0.83x, orders 1.23x (4w)/1.30x (8w). Conclusao: gargalo eh IPC overhead Windows spawn (nao load imbalance). Speedup teto ~1.3x sem dependencia externa. Fases 1c/2-4 pendentes. | **CLOSED** (fases 1+1b welded; 1c/2-4 nao serao feitas) |
| [T-CODE-OUTPUT-SINKS](T-CODE-OUTPUT-SINKS.md) | Contract `Sink` pluggable (Protocol), built-in sinks (File/MultiFile/Memory), streaming sinks (HTTP/TCP). Refactor scripts/writers/. Bloqueado por T-CODE-ENCODER-MANAGER. | **DEFERRED** (park v2.0) |
| [T-CODE-PLAN-CONTRACT](T-CODE-PLAN-CONTRACT.md) | `Plan` dataclass (group_by/order/batch_size/batch_unit), contrato D11/D13. Habilita ordenacao reversivel O-FMT-01..04 e SQL->Plan (D8). | **DEFERRED** (park v2.0) |
| [T-CODE-SCHEMA-BUILDER](T-CODE-SCHEMA-BUILDER.md) | **Fase 1+2 WELDED**: `src/tcf/schema.py` novo com `build_schema(data)` orquestrador + `ColumnSchema`/`TableSchema` dataclasses + `to_dict`/`to_json`. 24/24 tests passing (D17a 322B INVARIANT preservado, ColumnFeatures/cadence/min_len/seq_rle_runs reaproveitados via SideOutputs). `natures` placeholder vazio pra Fase 3 (META-TYPE-ENCODERS T02-T07). | **CLOSED** (fases 1+2 welded) |
| [T-CODE-EMPTY-FRAG-INDEX-RT](T-CODE-EMPTY-FRAG-INDEX-RT.md) | **[probatório] Bug de RT no core M10** (achado na caracterizacao V2-A): string vazia desloca o index de fragmento HCC → back-ref posterior corrompe/crasha. 2 modos (frag-index off-by-one em syntax._parse_decl + rstrip comendo vazio final em hcc_seqrle). Fix decode-only/byte-safe, 12 reproducers pinados, 332 passed, D1-D9=1523B preservado. | **CLOSED 2026-06-13** |
| [T-DIST-PYPI-NAME](T-DIST-PYPI-NAME.md) | Capturar nome de distribuicao no PyPI. `tcf` TOMADO (Tencent SCF); `tcf-format` e `tabular-compact-format` LIVRES (checado 2026-06-14). Recomendado `tcf-format` mantendo `import tcf`. Owner reserva (placeholder 0.0.1 ou release 0.7.0). | **CLOSED-DONE** (`tcf-format` publicado) |
| [T-CLEAN-2-strata-defrag](T-CLEAN-2-strata-defrag.md) | **[probatório]** Defragmentacao da biblioteca (auditoria Strata 2026-06-18): higiene de superficie (§3/§5, rotulos/numeros stale: CLAUDE v0.6, README "425 passed", MEMORY #TCF.6, links quebrados) + backlog (docs/theory dup §5, Pacote 1 maturacao §7, tombstones §3, MAP/tickets-location §2). Quick wins + backlog deferido; `src/tcf` intocado. | **IN-PROGRESS P2 2026-06-18** (QW-1..5 feitos; backlog DB-* aberto) |
| [META-STRATA-GOVERNANCE](META-STRATA-GOVERNANCE.md) | **[dispositivo]** Atividades recorrentes/cadencia do metodo Strata (nao-defrag): G-1 maturacao §7 (-> T-CLEAN-2), G-2 pass de rotulo §3-bis, G-3 re-verify L2 (2026-09-01), G-4 revisao periodica completa (~60-90d). + gatilho L0-check antes de mudanca grande. Lembrete vivo, proporcional (§9). | **OPEN P3 2026-06-18** |
| [T-CLEAN-3-org-defrag-pre-0.8](T-CLEAN-3-org-defrag-pre-0.8.md) | **[dispositivo→exec]** Defrag de organizacao pos-#TCF.8-default (sucessor do T-CLEAN-2): indice de tickets furado (19 fora, 2 open), diario furado (~25 dias sem entrada), STATUS bridges fora de ordem de autoridade, docs/article morto, notas superadas a classificar. Caminho-feliz em tiers + regras anti-colisao temporal (git=juiz, arquivar-nao-deletar). T1+T2+T3 EXECUTADOS (indice 62/62, INDEX regen, ESTADO-VIGENTE no STATUS, v08 encerrado, diario 43 entradas c/ 29 retroativas, 30 notas classificadas 17a/8b/5c + 7 anotacoes). Follow-up deferido: consolidacao STATUS pos-0.8. | **CLOSED-DONE 2026-07-09** |
| [T-CODE-LAZY-VIEW-PROMOTE](T-CODE-LAZY-VIEW-PROMOTE.md) | **A4 do plano 0.8**: promove a view lazy do gadget `scripts/tcf_lazy/` -> `src/tcf/view.py` (camada read-only; `from tcf import view`), shim de compat mantido. Aditivo, zero regressao byte-canonical (D1-D9=1523B/D17a=303B/RW=89616B), 380 passed. Versao segue 0.7.1 (bump em C). | **CLOSED 2026-06-21** |
| [T-DOC-LAZY-REFERENCE](T-DOC-LAZY-REFERENCE.md) | **A5 do plano 0.8**: reference Diataxis de `tcf.view` (`docs/reference/lazy-view.md`), estavel (L1-L4) vs experimental (`agg_by`/L5 -> H-QUERY-04/0.9). Exemplos ancorados. | **CLOSED 2026-06-21** |
| [BUG-VIEW-UMA-STRING-VAZIA](BUG-VIEW-UMA-STRING-VAZIA.md) | Uma única string vazia no corpo core fazia `count()` devolver 0 e `select()` truncar a linha em silêncio. Corrigido na ordem de três linhas de `_n_somado`: corpo ausente é perguntado antes de tirar o terminador. | **closed 2026-08-27** |
| [BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA](BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA.md) | numa coluna de 0 linhas, `distinct` devolvia `['']` e `n_unique` 1. A rota `.8M` fechou na onda 3 (`ntable == 0`); a rota `.8H` (corpo `b""` em mode `tcf`) fechou na onda 5: corpo ausente é zero linha. | **closed 2026-08-28** |
| [BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA](BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA.md) | coluna mista perdia valor no `encode`/`decode`, e em dois casos colapsava dois valores num só. O `.8M` passou a usar o mesmo juiz de homogeneidade do `.8H`: as três famílias recusam, como `api.md` já publicava. A política coerciva foi retirada, não implementada. | **closed 2026-08-28** |
| [BUG-VIEW-NULO-NO-HIERARQUICO](BUG-VIEW-NULO-NO-HIERARQUICO.md) | um `None` numa coluna densa fazia a `view` recusar a tabela `.8H` inteira como ragged. Coluna escalar densa-com-nulos passou a declarar `?0:` (emask 2-estados) no header; a `view` a distingue do ragged sem ler corpo. Muda wire: +1 byte de header por coluna assim; 2 pinos de navegação re-pinados, zero nos gates. | **closed 2026-08-28** |
| [BUG-VIEW-OBJETO-NAO-RETANGULAR](BUG-VIEW-OBJETO-NAO-RETANGULAR.md) | `#TCF.8H#O` de colunas desiguais era aceito pela `view`, que respondia `nrows` sobre tabela inexistente e depois acusava corrupção de blob íntegro. Recusa na abertura, pelos counts, com a frase das outras formas não tabulares. | **closed 2026-08-28** |
| [BUG-VIEW-ORFAO-SEM-MAGIC](BUG-VIEW-ORFAO-SEM-MAGIC.md) | `stamp=False` emitia wire sem magic que o `decode` lê e a `view` recusava, culpando o legado `#TCF.6/.7`. A `view` implementa o ramo órfão espelhando o `decode`; o legado de verdade continua recusado. | **closed 2026-08-28** |
| [BUG-BB-CR-CRU](BUG-BB-CR-CRU.md) | a união bool+str `#TCF.8bB` aceitava CR em um extra e gravava byte `0d` cru, embora o wire seja LF-only; controles single string/multi recusam e `.8H` escapa. Fechado pelo guard de quebra de linha do `_encode_lazy_bool`, que passou a testar CR além do LF: o extra com CR volta a cair no `.8H` e recebe o fail-loud da união. | **closed-fixed 2026-08-30** |
| [BUG-MENSAGEM-COLUNA-VAZIA-MISTA](BUG-MENSAGEM-COLUNA-VAZIA-MISTA.md) | o fail-loud de tipo misto nomeava colunas comuns, mas omitia o nome válido `''` por truthiness; o controle homogêneo com a mesma chave faz RT. Fechado sem trocar `if name` por `if name is not None`, que confundiria a lista solta do envelope `#V` com um `{"": [...]}` legítimo: o `_encode_root` passa `anon=True` e o rótulo da mensagem ficou separado do nome do campo. | **closed-fixed 2026-08-30** |
| [T-QA-083-REVALIDACAO](T-QA-083-REVALIDACAO.md) | reavaliação pós-fix materializada: 7 casos, tag 0.8.2 isolada, RT em arquivo e contratos com hash; dois bugs confirmados e três alegações anteriores reclassificadas. | **CLOSED 2026-08-29** |
| [T-DOC-RELEASE-083-SUPERFICIE](T-DOC-RELEASE-083-SUPERFICIE.md) | reconciliar publicação 0.8.3, duas mudanças de emissão e escopo de compatibilidade/título entre CHANGELOG, STATUS e ROADMAP. | **OPEN P2 2026-08-29** |
| [T-DOC-TIPOS-MISTOS](T-DOC-TIPOS-MISTOS.md) | o comportamento de coluna de tipos mistos esta soldado e medido; a documentacao esta em post-it em tres lugares, e a coluna comparativa com pandas/polars/SQL depende de um ambiente com essas bibliotecas. | **OPEN P3 2026-08-29** |
| [T-CODE-VIEW-SUBTCF-RECORTE](T-CODE-VIEW-SUBTCF-RECORTE.md) | Executar H-QUERY-06/07: `Filtered.to_tcf()` por recorte de raw/dict/split, com fallback; contrato válido em `.8M`, bordas de índice/projeção/single-col ainda bloqueiam o weld. | **OPEN P2 alvo-.9 2026-08-26** |
| [T-EXP-H-GDICT-01](T-EXP-H-GDICT-01.md) | **B1 do plano 0.8**: caracterizar cross-dict. B1 passou → B2 design+revisão+prototype (RT-lossless, reproduz B1) → **gate N≥5 FALHOU (1/5)** → teste-teto (per-col-min adaptativo vence) → **FECHADO**. Pivô: descapar V2-B. | **CLOSED-INSUFFICIENT-GENERALIZATION 2026-07-01** |
| [T-DIST-RELEASE-0.8.0](T-DIST-RELEASE-0.8.0.md) | Ato final do 0.8.0: C1/C2 e smoke local pré-verificados; C3 só após fila R0-R2 (BUG-14→F3→F4→F6), gates de artefato e go explícito do owner. | **OPEN-BLOCKED P2 2026-07-12** (by T-REL-08-CLOSEOUT) |
| [T-CODE-DESCAPAR-V2B](T-CODE-DESCAPAR-V2B.md) | Descapar V2-B (dict = candidato do `min()` p/ high-card). Prototype read-only: **byte-safe** (pins intactos, RT ok), −5% real em high-card espalhado, custo ~2× compute. Opções (A) cap-raise 8k [rec] / (B) +skip cadence / (C) puro. **Toca src/tcf, sob aprovação.** | **CLOSED-PARCIAL 2026-07-10** (T-REL-08 P1b; forma A welded `a201c1e`; B/C → ROADMAP .9) |
| [T-DOC-3](T-DOC-3-shebang-terminology.md) | Terminologia: "shebang" (=`#!`) é impreciso → **assinatura de formato / magic number** (`#TCF.N`, análogo `%PDF-`). Termo canônico setado em vocabulary.md + ADR-0001 + TCF-format.md. Backlog: sweep incremental da prosa viva. | **CLOSED-CANONICAL-SET 2026-07-01** |
| [T-FMT-TCF8H-HEADER](T-FMT-TCF8H-HEADER.md) | Header do protótipo hierárquico `#TCF.8H` (EXP-015): consagráveis (M-implícito, omit-closes, última-sem-size) vs condicionais (reorder S2/S3). `H` REGISTRADO no discriminador (ADR-0031, 2026-07-09; especialização de `M`, sem-espaço); codec segue gated. | **CLOSED-DECIDED 2026-07-10** (T-REL-08 P1e; slot H no .8 `a001fd3`; codec → .9 via T-STUDY-HIERARCHICAL-TCF) |
| [T-OPT-INFERENCE](T-OPT-INFERENCE.md) | Otimizações por inferência (valor deduzido, não escrito): hex-default dos sizes (subsume em O-FMT-18; base-94 vence), bN (→ H-TYPE-02/07, gate D3 N=8). Framework: specs induzidas por round-trip. | **OPEN P2 2026-07-08** |
| [T-FMT-OMIT-OR-DECLARE](T-FMT-OMIT-OR-DECLARE.md) | Contrato de omissão: campo omitido e não-deduzível → declaração OBRIGATÓRIA (4 categorias; fail-loud; proveniência). Generaliza ADR-0029. Avaliar pré-1.0. | **OPEN pre-1.0 2026-07-08** |
| [T-FMT-HEADER-BASE-HEX](T-FMT-HEADER-BASE-HEX.md) | Base HEX implícita dos byte-sizes do header (decimal só comando de inspeção/IO/debug). Super-específico, desmembrado de T-OPT-INFERENCE Item 1. **WELDED**: core.py+view.py hex nos #TCF.7/.8; #TCF.6 decimal; D17a 303→302; 528 passed. (Owner 07-09: hex vira exclusivo do .8, ajuste no flip.) | **CLOSED-WELDED 2026-07-10** (T-REL-08 P1a; shipado no .8, weld `a381cdb`) |
| [T-FMT-NAME-ESCAPING](T-FMT-NAME-ESCAPING.md) | Escape/quoting de nomes de coluna (`:`/`,`/`=`/`#`-inicial + `{}[]` da hierarquia) no meta, resolve o blocker do `:` sob .8-default via escaping (CSV-style), não rejeição. Interim backslash **WELDED** (M2, `58f7dee`); resta o estudo CSV-quoting/smart (deferido). | **CLOSED-PARCIAL 2026-07-10** (T-REL-08 P1d; interim = .8 `58f7dee`; estudo → T-FMT-QUOTING-STUDY .9) |
| [T-QA-8](T-QA-8-material-comprobatorio.md) | **[dispositivo→exec]** Material comprobatório do #TCF.8/0.8.0. F0 (12/13 achados originais), F1 runner e F2 controle concluídos; 600 passed. BUG-14 (RT Unicode no domínio aceito) é gate R0; depois F3→F4→F5 condicional→F6. | **OPEN P1 · F2 DONE 2026-07-12** |
| [T-TOOL-TCF-FIX-CORRUPTION](T-TOOL-TCF-FIX-CORRUPTION.md) | Ideia do owner (2026-07-10): reparador de `.tcf` com algum grau de corrupção (gadget FORA de src/tcf; reparo = sugestão auditável). Decode pós-F0 já MARCA os pontos (fail-loud "meta corrompido": nome declarado vazio, dangling, hex inválido); BUG-04/05/11 = mais ganchos futuros. Pensar depois do T-QA-8 + publicação 0.8. | **OPEN P3 2026-07-10** |
| [T-API-BOUNDARY-CONTRACTS](T-API-BOUNDARY-CONTRACTS.md) | **CONGELAR fronteiras da API no `.8`** (regate pré-1.0 → `.8`, owner 2026-07-13, reescopo feature-complete): decidir agora null-vs-vazio, tipos-como-string, ragged fail-loud, `\n`-em-valor (pendente owner) + tabela do lote 3 (ISOLAMENTO já welded). | **CLOSED**, pre-req de feature-complete do `.8` |
| [T-CODE-TCF8H-WELD](T-CODE-TCF8H-WELD.md) | **[dispositivo→exec]** Weld do codec hierárquico `#TCF.8H` no `src/tcf` (feature do `.8`, owner 2026-07-13). Protótipo EXP-015 validado (RT-exato); header decidido (ADR-0031). Gate de **CAPACIDADE** (RT em JSON aninhado real + non-regressão flat + aprovação `src/tcf`), não ≥15%. Fases W0-W5. | **closed-welded 2026-09-02** (welded de fato 2026-07-14, ADR-0033) |
| [T-FMT-META-STRICT](T-FMT-META-STRICT.md) | Integridade defensiva pós-.8: fusões geométricas→checksum/tcfx; BUG-12 corrigido (`25ad29eb`, prova 2026-09-02); teto `max_length` welded (`95ab69dc`), expansão acumulada vira ticket próprio pré-1.0. | **OPEN P3 · pré-1.0/`.9`** (re-triagem 2026-09-02: nada barato resta pro `.8`) |
| [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md) | Flag de controle de paralelismo/uso de CPU (pedido owner 2026-07-10): env `TCF_MAX_WORKERS` como teto do HOST > kwarg; `parallel=True` mais educado que cpu_count cheio; budget único (workers + futuro V2-J intra-coluna); telemetria pedido-vs-concedido. Design decidido PÓS-F3 (medição de speedup/porção-serial do T-QA-8). | **OPEN P2 2026-07-10 (design pós-F3)** |
| [T-REL-08-CLOSEOUT](T-REL-08-CLOSEOUT.md) | **[dispositivo→exec]** Fila única por ROI: R0/R1 concluídos em modo amostral; R1.5 specs cadastrais + FLOOR + query-like classificados; próximo F6 doc/build/smoke → R3 C3. Massa fica em janela pós-closeout; corrupção/hardening e pesquisa continuam separados. | **OPEN P1 · PRÓXIMO F6 2026-07-12** |
| [T-FMT-QUOTING-STUDY](T-FMT-QUOTING-STUDY.md) | Filho de T-FMT-NAME-ESCAPING (preferência owner: ticket, não linha solta): estudo CSV-quote/smart além do backslash interim, "apenas o barra resolve tudo?" (fuzz do .8 diz sim pro FLAT; pressão real = hierarquia `{}[]`). Medir nomes "sujos" em headers reais antes de avançar. | **OPEN P3 alvo-.9 2026-07-10** |
| [T-CODE-CORE-CONSOLIDATE](T-CODE-CORE-CONSOLIDATE.md) | **[dispositivo→registro]** Simplificar o core (diretriz owner 2026-07-12: código espalhado, lógica duplicada = risco de dessincronização, ex. fix BUG-14 aplicado 2× em hcc_seqrle+syntax; muitas funções; M8A é nome de PROTÓTIPO → renomear pra HCC). Inventário medido: 4 duplicações D1-D4, ~131 defs, M8A em 8 arquivos+pyx. Fases C0 (dedup cirúrgico, tail do .8) → C1 (rename, pós-release) → C2 (achatar decode 2-passadas) → C3 (re-medição). | **OPEN P1 2026-07-12** |
| [T-SPEC-STATUS-08](T-SPEC-STATUS-08.md) | **[dispositivo→registro]** Survey + laboratório cadastral: data/datetime, CEP, RG, telefone e códigos fixos medidos fora do core; base64/base80/base96 comparados. CPF/CNPJ/IP permanecem `.8`; `DateSpec` ISO é candidato condicional; demais famílias ficam `.9` sem dados reais. | **closed-decided 2026-09-02** (Opção A owner 2026-07-12; caveat F6 no README; hand-off `.9` registrado) |
| [T-SPEC-DEEPDIVE-08](T-SPEC-DEEPDIVE-08.md) | **[dispositivo→registro]** Investigação de fundo dos specs: Ceiling delta-aware continua `.9`; FLOOR total-byte está welded; a revisão cadastral v1 adicionou data/CEP/RG/telefone/códigos fixos e confirmou que o gargalo é dado real, não base de encoding. | **closed-decided 2026-09-02** (direções `.9` no ROADMAP: NATURE-DELTA/FIELD-SPLIT; gabarito CPF 10-eixos cross-ref) |

### Indexados retroativamente (backfill 2026-07-09, T-CLEAN-3 T1-a)

> 19 tickets que existiam sem row no índice (gap de discoverability achado no levantamento T-CLEAN-3).
> Rows geradas MECANICAMENTE do frontmatter (title+status de cada ticket, sem reinterpretação) + data do
> último commit. Tabela acima NÃO foi reordenada, este bloco é só aditivo.

| ID | Tema | Status |
|---|---|---|
| [T-DOC-MANUAL-FORMAL](T-DOC-MANUAL-FORMAL.md) | Manual didatico no padrao polars/pandas: indice, quickstart, entrada por TIPO de dado, sequencia coletar->consultar. A doc de hoje e' boa mas organizada por ORIGEM, nao pela pergunta do leitor | **OPEN P2** |
| [T-LAB-DIDATICO-PONTA-A-PONTA](T-LAB-DIDATICO-PONTA-A-PONTA.md) | Micro-lab do fluxo real: coletar -> dataset -> schema -> encode -> envio -> cliente/servidor -> disponibilizar. Fecha buraco: NAO existe exemplo cliente/servidor no repo, e o TCF e' sobre transmissao | **OPEN P2** |
| [T-HTTP-QUERY-E-VIEW](T-HTTP-QUERY-E-VIEW.md) | O metodo HTTP **QUERY** (RFC 10008, jun/2026, nao e' mais draft) como envelope do `view()`: corpo na requisicao + safe/idempotente + **resposta cacheavel com o corpo na chave**. Hipotese central: view() no SERVIDOR vs no cliente | **OPEN P2 (pesquisa)** |
| [T-PERF-BORDAS-E-MODOS-09](T-PERF-BORDAS-E-MODOS-09.md) | **Ticket-mestre do `.9`**: bordas do TCF por eixo (cardinalidade e' o quente) + modos de compressao rapido/normal/maximo (nunca testados) + bench na topologia REAL 1 encode : N decodes. Base medida 2026-08-23: penhasco de encode 143x, break-even 1,2-36 Mbps, borda em 500k | **OPEN P1 (.9)** |
| [T-API-SCHEMA-PRESCRITIVO](T-API-SCHEMA-PRESCRITIVO.md) | Objeto `Schema` (forma longa do `schema=` do ADR-0047) como portador do CONTRATO: specs+tipos+assinatura de knobs+nomes/ordem+contrato-fora-do-fio; aditivo enquanto for so' ENTRADA (campo que viajar no wire = ADR de formato) | **OPEN P2 (pre-1.0; registro de destino)** |
| [BUG-CHAVE-VAZIA-POSICIONAL](BUG-CHAVE-VAZIA-POSICIONAL.md) | `{"": [...]}` voltava `{"0": [...]}`, o unico caso em que o TCF ALTERAVA o dado. Causa: colisao de grafia com `drop_names`; conserto = portar o `\z` do `.8H` (ADR-0033) ao `.8M`. Veredito: DEFINICAO SUPERADA (2026-07-10 -> 2026-07-17), nao bug | **CLOSED 2026-08-21 (ADR-0046)** |
| [T-CODE-HCC-ATOM-DETECTION-REFINE](T-CODE-HCC-ATOM-DETECTION-REFINE.md) | Bug #1 sub-exp 14 (atom secundario nao criado) | **CLOSED-SUPERSEDED-BY-ADR-0016** (ult. commit 2026-06-21) |
| [T-CODE-HCC-MULTI-DELTA-FIX](T-CODE-HCC-MULTI-DELTA-FIX.md) | Bug #2 sub-exp 14 (seq-RLE rejeita multi-run delta) | **CLOSED-WELDED-CANONICAL** (ult. commit 2026-06-21) |
| [T-CODE-LAYERED-PIPELINE](T-CODE-LAYERED-PIPELINE.md) | Toggle infrastructure + online adaptive + fallback | **CLOSED** (ult. commit 2026-06-15) |
| [T-CODE-LEGACY-PRUNE-PRE-07](T-CODE-LEGACY-PRUNE-PRE-07.md) | Podar fallbacks/legado pré-0.7 do core (rumo a 1.0) | **CLOSED** (ult. commit 2026-06-24) |
| [T-CODE-RT-EDGES](T-CODE-RT-EDGES.md) | 2 violações de RT em bordas (seq-RLE trailing-space + \n embutido) | **CLOSED-FIXED** (ult. commit 2026-07-05) |
| [T-DATA-2-RECEITA-CNPJ](T-DATA-2-RECEITA-CNPJ.md) | Dataset real de CNPJ (Receita Federal open data) p/ gating ecologico das natures | **CLOSED-DONE** (ult. commit 2026-06-02) |
| [T-DATA-3-EDGE-QUALITY-FIXTURES](T-DATA-3-EDGE-QUALITY-FIXTURES.md) | Plano de dados de borda/defeituosos p/ gadgets de qualidade/schema (planejamento) | **DEFERRED** (ult. commit 2026-06-21) |
| [T-DATA-4-TPCH-PART-SAMPLES](T-DATA-4-TPCH-PART-SAMPLES.md) | Samples committed de part/partsupp do TPC-H (categoria hierarquica observavel) | **CLOSED-DONE** (ult. commit 2026-06-01) |
| [T-DATA-TRANSMISSION-GROUPING](T-DATA-TRANSMISSION-GROUPING.md) | Agrupar datasets por cenário de transmissão (matriz 3-eixos) | **CLOSED-DONE 2026-07-10** (T-REL-08 P1c; entrega = coverage-matrix.md `033bba3`) |
| [T-FIX-SHAPER-STRATIFY-TEST](T-FIX-SHAPER-STRATIFY-TEST.md) | Corrigir expectativa do test_stratify_proportional | **CLOSED-DONE** (ult. commit 2026-05-31) |
| [T-FLOW-ENCODE-STRATEGIES-TELEMETRY](T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md) | Estratégias de encode (speed/mem) + telemetria sugestiva de ordem (S1/S2/S3) | **OPEN** (ult. commit 2026-07-06) |
| [T-H-PERF-06-V2-T01-WELD-15](T-H-PERF-06-V2-T01-WELD-15.md) | Weld do candidato #15 (topK prune) em src/tcf | **CLOSED-DONE** (ult. commit 2026-06-21) |
| [T-H-PERF-06-V2-T02-CYTHON](T-H-PERF-06-V2-T02-CYTHON.md) | Acelerador Cython opcional de _detect_compositions (Fase B) | **CLOSED-DONE** (ult. commit 2026-06-21) |
| [T-RECOVER-LLM-SCHEMA-MODE](T-RECOVER-LLM-SCHEMA-MODE.md) | Gadget LLM (schema + SQL gen, formato LLM-binary) | **DEFERRED** (ult. commit 2026-06-15) |
| [T-RECOVER-SCHEMA-MULTI-TABLE](T-RECOVER-SCHEMA-MULTI-TABLE.md) | Gadget auxiliar de schema multi-tabela (alertas, NAO conserta) | **CLOSED-DONE** (ult. commit 2026-06-08) |
| [T-REGRESSION-REAL-WORLD](T-REGRESSION-REAL-WORLD.md) | Estender regression suite p/ amostras real-world (gate prune algoritmico) | **CLOSED-DONE** (ult. commit 2026-06-21) |
| [T-SHAPER-CODE-HARDENING](T-SHAPER-CODE-HARDENING.md) | Hardening de codigo do shaper (escala, dedup, bugs latentes) | **DEFERRED** (ult. commit 2026-07-05) |
| [T-SHAPER-SCIENTIFIC-GATING](T-SHAPER-SCIENTIFIC-GATING.md) | Gate cientifico de uso do shaper (tests estatisticos assertados) | **CLOSED-DONE** (ult. commit 2026-05-31) |
| [T-STUDY-HIERARCHICAL-TCF](T-STUDY-HIERARCHICAL-TCF.md) | TCF para JSON aninhado (guarda-chuva: grupo de labs / peças; liga EXP-015 `#TCF.8H`) | **OPEN** (ult. commit 2026-07-05) |
| [T-STUDY-DATASETH-COMPLETE-SEMANTICS](T-STUDY-DATASETH-COMPLETE-SEMANTICS.md) | S0–S1: contrato DatasetH e codec-oráculo antes do wire canônico | **IN-PROGRESS 2026-07-16** |
| [T-STUDY-HIERARCHY-LINK-ALGEBRA](T-STUDY-HIERARCHY-LINK-ALGEBRA.md) | S2–S7: IR, equivalência dos vínculos e comparação física | **IN-PROGRESS 2026-07-16** |
| [T-EXP-DATASETH-S0-S3](T-EXP-DATASETH-S0-S3.md) | Executar corpus, oráculo, IR e álgebra S0–S3 | **CLOSED 2026-07-16** |

## Politica

- Cada ticket "closed" referencia commit(s) que o resolveram.
- Antes de deletar/mover arquivos: garantir push ao GitHub.
- Recuperabilidade via `git log` / `git show`.

## Convencao pra tickets novos (recomendacao 2026-05-21)

Tickets futuros devem usar YAML frontmatter pra serem indexaveis
por `scripts/index.py` e parseaveis por IA. Existentes (fechados)
ficam como estao, imutabilidade.

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

Referência da metodologia subjacente: oficina
[`Methodologies`](../../Methodologies/README.md) + receita
[`Strata`](../../Methodologies/recipe/knowledge-architecture.md).

### Nao indexados ate' 2026-08-22 (reconciliacao)

| ID | Tema | Status |
|---|---|---|
| [BUG-BRACKET-CELL-LOSS](BUG-BRACKET-CELL-LOSS.md) | célula string que é exatamente '[' ou ']' é PERDIDA silenciosamente | closed |
| [BUG-SEQRLE-RANGE-EMPTY-B](BUG-SEQRLE-RANGE-EMPTY-B.md) | decode(encode(x)) crasha quando um afixo tem sufixo `..`/`...` | closed |
| [T-CI-1-github-actions](T-CI-1-github-actions.md) | GitHub Actions CI (pre-commit lint; tests refactor follow-up) | closed |
| [T-CI-2-tests-refactor](T-CI-2-tests-refactor.md) | Refactor tests CI-friendly (archive v0.5 + marker requires_data + new core_rt) | closed |
| [T-CI-3-pyx-compiled-byte-gate](T-CI-3-pyx-compiled-byte-gate.md) | Gate byte-canonical do caminho Cython COMPILADO (detect.pyx) | closed-done |
| [T-CLEAN-1-pre-commit-hooks](T-CLEAN-1-pre-commit-hooks.md) | Adicionar pre-commit (detect-secrets, ruff, basicos) | closed |
| [T-CLEAN-2-strata-defrag](T-CLEAN-2-strata-defrag.md) | Defragmentação da biblioteca (higiene de superfície §3/§5 + índices §2) | closed-backlog-done-db2-owner-pending |
| [T-CLEAN-3-org-defrag-pre-0.8](T-CLEAN-3-org-defrag-pre-0.8.md) | defrag de organização (docs/tickets/diário) pós-#TCF.8-default, pré-review 0.8 | closed-done (follow-up deferido: consolidacao STATUS pos-publicacao-0.8) |
| [T-CODE-H-DA-11c-features-unificadas](T-CODE-H-DA-11c-features-unificadas.md) | Consolidar pre-pass features (ColumnFeatures unificado) | closed |
| [T-CODE-TCF8H-JSON-PARITY](T-CODE-TCF8H-JSON-PARITY.md) | o que falta pra fechar "hierarquia" (paridade JSON) + 1 capacidade exclusiva | **closed 2026-09-02** (P1/P2/P3/P4 welded; P5 ratificado fora do `.8`; shared-ref → research-track/1.0) |
| [T-DATA-1-datasets-financeiros-cientificos](T-DATA-1-datasets-financeiros-cientificos.md) | Datasets financeiros/cientificos canonicos (Online Retail, Beijing PM2.5, Wine Quality) | closed |
| [T-DIST-RELEASE-0.8.0](T-DIST-RELEASE-0.8.0.md) | Release do pacote 0.8.0 (#TCF.8 default, ADR-0032) | open |
| [T-DOC-1-citation-cff](T-DOC-1-citation-cff.md) | Adicionar CITATION.cff e preparar DOI (Zenodo) | closed |
| [T-DOC-2-diataxis-naming](T-DOC-2-diataxis-naming.md) | Explicitar mapeamento docs/algorithms,theory → Diataxis (reference,explanation) | closed |
| [T-DOC-3-shebang-terminology](T-DOC-3-shebang-terminology.md) | Terminologia: "shebang" → assinatura de formato / magic number | open-errata-reminder |
| [T-EXP-H-DA-09c-d-e](T-EXP-H-DA-09c-d-e.md) | Refinos detect_cadence (threshold/multivariada/adaptativo) | closed |
| [T-EXP-H-PERF-05d](T-EXP-H-PERF-05d.md) | Counter incremental em HCC _detect_compositions | closed |
| [BUG-VIEW-RECUSA-COLUNA-TIPADA](BUG-VIEW-RECUSA-COLUNA-TIPADA.md) | uma coluna `int`/`bool` tirava a tabela inteira do `view()` | **closed 2026-08-23** |
| [BUG-ENCODE-PRIMEIRO-VALOR-NULO](BUG-ENCODE-PRIMEIRO-VALOR-NULO.md) | `None` numa coluna estourava o encode com `TypeError` cru (o gatilho não era a posição, era o template) | **closed 2026-08-25** |
| [DECISAO-VIEW-BOOL-TRUTHINESS](DECISAO-VIEW-BOOL-TRUTHINESS.md) | `int` numa coluna bool passa por truthiness, e a doc promete o contrário | open |
| [DECISAO-GROUPING-SEMANTICA](DECISAO-GROUPING-SEMANTICA.md) | Contrato matemático mínimo da `view`: nulo forma grupo, string vazia é elemento, soma vazia é zero, extremos/média sem resposta; convenções externas ficam em adaptadores explícitos. | **CLOSED-DECIDED 2026-08-26** |
| [T-DOC-L10N-REFERENCE](T-DOC-L10N-REFERENCE.md) | os 5 documentos restantes de `docs/reference/` em dois idiomas (742 linhas) | open |
| [T-FMT-CONTRACT-SIGNATURE](T-FMT-CONTRACT-SIGNATURE.md) | assinatura de contrato para os knobs que não reconstroem a entrada (drop_names, sort_by) | open |
| [T-FMT-ESCAPE-COMBINATORIAL-STUDY](T-FMT-ESCAPE-COMBINATORIAL-STUDY.md) | reestudar o escape (combinatório + estratégias de outros mecanismos) | open |
| [T-QA-8-material-comprobatorio](T-QA-8-material-comprobatorio.md) | material comprobatório do #TCF.8/0.8.0 (controle → sintéticos → públicos) com telemetria, dicts | open |
| [T-SHAPER-NESTED-OUTPUT](T-SHAPER-NESTED-OUTPUT.md) | saída HIERÁRQUICA nativa no Shaper (aninhar via FK, inverso do flat) | open · **`.9`** (re-triagem 2026-09-02: não é barato e o massa do `.8H` já rodou à mão) |
| [T-STUDY-USE-PROFILES](T-STUDY-USE-PROFILES.md) | perfis de uso (transmissão × armazenamento) e a calibração dos vértices | open |
| [T-TYPED-SINGLECOL-MODE-HEURISTIC](T-TYPED-SINGLECOL-MODE-HEURISTIC.md) | single-col tipado + modos de corpo (heurística p/ .9) | open |
