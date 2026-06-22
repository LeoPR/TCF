# STATUS — TCF (compendio sempre-atualizado)

> **Versionamento (ADR-0024, 2026-06-14)**: projeto e' **pré-1.0**. Os minors do
> formato (`#TCF.4/.5/.6/.7`) sao iteracoes de dev rumo a um **1.0 solido**, sem
> compat rigida entre eles (git reproduz versoes antigas). O `#TCF.7` = "0.7"
> pré-1.0, **NAO v2.0** (v2.0 = depois). Pacote: `0.7.0` (era "1.0.0", rotulo
> prematuro). Labels "v1.0 frozen"/"v2.0" em ADRs/STATUS antigos: ler nessa chave.
>
> **0.7 e' o DEFAULT do encode** (multi-col): `encode(dict)` -> `#TCF.7` (fallback
> + dicionario V2-B + header minimo, automaticos). Single-col inalterado.
> Baseline D17a re-pinado **322 -> 307 -> 303 B** (V2-B na coluna `categoria`;
> #TCF.6 legado=322, lido pelo decoder + produzivel via `_encode_multi(fallback=
> False, min_header=False)`). D1-D9=1523B (single-col) inalterado. Suite 385 passed.
>
> **Proximo foco (2026-06-14)**: continuar no 0.7 (detalhes de compressao). Revisao
> implicito-vs-explicito + candidatos a knob explicito + detalhes "passaram batido"
> em `experiments/lab/dirty/notas/revisao-implicito-vs-explicito-2026-06-14.md`.
> FEITO: knobs explicitos #1-3 (fallback/min_header opt-out, min_len override);
> #5 ordering (O-FMT-02 `sort_by` order-free welded); **V2-B dicionario WELDED**
> ([ADR-0025](docs/adr/0025-v2b-dictionary-categorical-weld.md), `@`, 13.9% weighted);
> **SPLIT ESTRUTURAL WELDED** ([ADR-0026](docs/adr/0026-structural-split-weld.md),
> `%`, 4o candidato do fallback, **19.39% weighted** = maior lever do ciclo:
> decimal/data/datetime/id -> campos -> V2-B). **Pacote 8 (H-HCC dinamico) ADIADO**
> (1.30% teto, cauda longa, risco alto no detector core). **V2-D strip de afixo
> REFUTADO** (subsumido pelo OBAT, 0.11%; sinal real era split estrutural).
> **LOSS ampliado (Pacote 10, 2026-06-14)**: owner ampliou o escopo lossy ("loss e
> PRO TCF FAZER SIM"). Revisao exaustiva de TODAS as vertentes (9 facets + critico,
> workflow) em `experiments/lab/dirty/notas/loss-taxonomia.md`. Ideia-chave: loss
> por-linha + LOSSLESS NO AGREGADO (soma; parcelamento) — PoC do maior-resto OK.
> Mais promissora = loss CROSS-COLUNA (`valor=soma(parcelas)`). Decisao de weld
> PENDENTE (owner; cruza a linha lossless, GATE N>=5).
> **FECHAMENTO DO CICLO 0.7 (2026-06-15)**: bytes-core welded (V2-A/B/split +
> header minimo + sort_by). **Higiene de tickets feita**: 3 fases welded fechadas
> (encoder-manager 1+1b, schema-builder 1+2, layered Fase 1) + 3 ja'-prontos
> confirmados (stratify-test, H-PERF-06 T01/T02); **5 parks** v2.0/pos-0.7
> (output-sinks, plan-contract, shaper-hardening, llm-gadget, META-TYPE execucao);
> [ADR-0018](docs/adr/0018-v2-format-roadmap.md) -> `accepted` (referencia do
> roadmap de formato; V2-D refutado). **Decisoes do owner**: o **0.7 permanece
> lossless-puro** — V2-C round e Pacote 10 (loss) viram **roadmap v2.0** (se
> perseguido, cross-coluna primeiro, GATE N>=5); nome PyPI = **`tcf-format`
> RESERVADO** (2026-06-16) — release **`0.7.1`** (pyproject `1.0.0` -> `0.7.1`,
> alinha ADR-0024; o patch e' contador de release, desacoplado do formato `#TCF.7`
> e do comportamento). Build validado via `uv` (`tcf_format-0.7.1.{tar.gz,whl}`).
> Suite 398 passed; D1-D9=1523B / D17a=303B intactos; `src/tcf` so' string de
> versao. Tag `v0.7.1`. Follow-ups adiados: V2-B RLE no stream; release.yml
> (Trusted Publishing). Detalhe: `experiments/lab/dirty/notas/diario/2026-06-15.md`.
>
> **SESSAO 2026-06-16 (pos-0.7, divulgacao + lazy + caracterizacoes)**:
> - **Lazy view gadget** [`scripts/tcf_lazy/`](scripts/tcf_lazy/) — **L1-L5 funcional, 27 testes**:
>   conectar e consultar (`count/sum/min/max/avg` + `where` + group-by) **descomprimindo so' o
>   necessario** (qtd-por-usuario toca **7,9%** do blob). Le `#TCF.7`, **nao-versao**, `src/tcf`
>   intocado. Achados: `*N|` no modo-tcf NAO e' separavel (so' dict/raw); L5 layout = trade-off
>   de compressao. Lab `2026-06-16-lazy-query/` + Pacote 12 (H-QUERY-01).
> - **TCF + brotli vence em ESCALA**: TCF cheio + brotli < csv+brotli em multi-col real (adult
>   −28%); "menos TCF" refutado; ordering codec-dependente (`2026-06-16-staged-and-ordering-brotli/`).
>   EXP-008 refrescado (single-col).
> - **number-nature** caracterizada -> **PARK** (weighted <15% em 2+, some sob brotli).
>   **O-FMT-12** (encode_file/auto-detect CSV) levantado -> **PARK** (input fora-do-core).
> - Criados **[`ROADMAP.md`](ROADMAP.md)** (tiers pre-1.0/2.0/pesquisa) + **[`docs/divulgacao-tcf.md`](docs/divulgacao-tcf.md)**.
>   Filtros modulares (H-NAT-MARK-02) + classificacao "e' versao?" registrados. README propagado.
> - **Pacote `tcf-format 0.7.1` publicado no PyPI**. Suite **425 passed**, 1 xfailed. `src/tcf` intocado.
>
> **SESSAO 2026-06-17 (filtros modulares F1.5/F2 + CEP)**:
> - **F1 + F1.5 FEITOS** (gadget [`scripts/natures_compiler/`](scripts/natures_compiler/)): compilador
>   DSL textual -> spec + registry por nome (cpf/cnpj/ip semeados); **14 testes**; regenera CPF/CNPJ/IP
>   do DSL == a' mao. **Zero `src/tcf`.** Achado: CEP/MAC precisariam spec novo.
> - **CEP + outer-dict pesquisados** -> **nenhuma acao**: o TCF ja' trata CEP (split/OBAT+dict, lossless,
>   zeros preservados); outer-dict subsumido por V2-B+split no caso tabular (nicho = payload minusculo
>   indexando tabela-padrao grande). [pesquisa](experiments/lab/dirty/notas/cep-outer-dict-codebook-pesquisa.md).
> - **F2 (H-NAT-MARK-01) — DESIGN FEITO, PARADO em (A)** (decisao owner): nature-id viaja no header
>   (`#TCF.7->#TCF.8`, tag `:` no nome, resolucao core-only, id desconhecido->cru+flag). **Nao implementado**
>   — o magic permanente nao se justifica so' por DX (gate >=15%/2-reais nao bate; registry gadget ja'
>   cobre quase de graca). [ADR-0027 `proposed`](docs/adr/0027-nature-mark-header-self-describing.md) +
>   [design](experiments/lab/dirty/notas/f2-nature-mark-header-design.md). **`src/tcf` intocado.**
>
> **SESSAO 2026-06-19 (pre-1.0: cheap-wins fechados + V2-RLE-STREAM + defrag)**:
> - **Cheap-wins fechados**: Tier A (release.yml, [reference de knobs](docs/reference/encode-knobs.md),
>   higiene CI) + CW-4 (docstrings stale em `src/tcf` alinhados, so' docstring) + CW-5 (O-FMT-11
>   subsumido por min_header/name-guard). Ver [ROADMAP](ROADMAP.md) cheap-wins.
> - **V2-RLE-STREAM caracterizado** ([lab](experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md)):
>   fecha o follow-up "V2-B RLE no stream" pendente desde 06-15. **Geral CLOSED-INSUFFICIENT-GAIN**
>   (+1,19% weighted/7 reais, 0/7 >=15%, -1,39% sob brotli). **Nicho textual-puro ABERTO** p/ decisao
>   do owner (low-card skewed, ordem natural: situacao +55%, workclass +22%). Achado: **clusterizado
>   flipa pro tcf-`*N|`** (overlap com o run-RLE de linha). Registry: roadmap-hipoteses Pacote 11-bis;
>   familia RLE em [`rle-familia-estudo.md`](experiments/lab/dirty/notas/rle-familia-estudo.md).
>   RLE intra-valor (H-INTRA) ADIADO. **`src/tcf` intocado** (lab-first).
> - **Defrag/Strata**: tickets [T-CLEAN-2](tickets/T-CLEAN-2-strata-defrag.md) (QW feitos + backlog) +
>   [META-STRATA-GOVERNANCE](tickets/META-STRATA-GOVERNANCE.md). Diretiva: sempre cross-reference.
>
> **SESSAO 2026-06-21 (plano 0.8 + lazy endurecido + transmissao + dict/H-REF)**:
> - **Plano 0.8** ([`v08-plano-etapas.md`](experiments/lab/dirty/notas/v08-plano-etapas.md)): 0.8 =
>   lazy basico shipado+endurecido + cross dict (se pagar); Q-04 avancado -> 0.9. Pacote 0.8.0 != #TCF.8.
> - **Lazy endurecido (workstream A)**: A1 banco de testes (4 modos + bordas, verde) + A2 fecha bug de
>   dupla contagem em `touched` + A3 otimiza o CAMINHO do algoritmo (count 1->0 decode; redundancia
>   3->1; Python deferido). 381 passed. [lab](experiments/lab/dirty/2026-06-19-lazy-testbank/result.md).
>   `src/tcf` intocado (tudo no gadget). Falta A4 (promover -> `tcf.view`, sob aprovacao) + A5.
> - **Cross dict / referencia**: achado — `^N` ja' e' dict implicito; ideia do owner = dict GLOBAL no
>   header ([H-GDICT-01](experiments/lab/dirty/notas/roadmap-hipoteses.md)) + familia H-REF
>   ([`dict-referencia-hipoteses.md`](experiments/lab/dirty/notas/dict-referencia-hipoteses.md)). Nao caracterizado.
> - **Header linhas-vs-bytes**: row-count REFUTADO (solid-block; ganho ininfimo, perde O(1)/paralelo);
>   base-94 size = O-FMT-18 candidato (so' nicho transmissao-minuscula). [lab](experiments/lab/dirty/old/refuted/2026-06-19-header-rows-vs-bytes/result.md).
> - **Guia de transmissao por API** ([`transmissao-api-onde-tcf-importa.md`](experiments/lab/dirty/notas/transmissao-api-onde-tcf-importa.md)):
>   honesto — nicho do TCF ~5-15% (batch/export tabular grande); **teste decisivo pendente**:
>   TCF+brotli vs **NDJSON+brotli** (so' comparamos com CSV+brotli).
> - Checkpoint Strata: [`checkpoints/2026-06-21-avaliacao-documental-strata.md`](experiments/lab/dirty/notas/checkpoints/2026-06-21-avaliacao-documental-strata.md).
>
> **SESSAO 2026-06-21-b (faxina + avaliacao 0.8 + A4)**:
> - **Faxina dirty/docs** (commit 4401046): 17 labs -> `old/welded|refuted`, drift
>   `#TCF.6->#TCF.7` corrigido nos docs de exemplo, snapshots marcados, MAP/diario/historia
>   atualizados, `_wf_*.js` + `out_files/` destrackeados. `src/tcf` intocado.
> - **Avaliacao grounded de prontidao 0.8** (workflow 6 agentes, testes rodados): base solida
>   confirmada (D1-D9=1523B/D17a=303B/RW=89616B verdes); A1-A3 do lazy feitos; gaps = A4/A5/B1/C.
> - **A4 FEITO** ([T-CODE-LAZY-VIEW-PROMOTE](tickets/T-CODE-LAZY-VIEW-PROMOTE.md), owner aprovou
>   o toque): lazy promovido `scripts/tcf_lazy/lazy.py` -> **`src/tcf/view.py`** (camada read-only;
>   `from tcf import view`), shim de compat mantido. Aditivo, **zero regressao byte-canonical**,
>   380 passed. Versao segue 0.7.1 (bump 0.8.0 e' no release, workstream C).
> - **4 tickets 0.8 criados** (rastreabilidade): A4 (closed), A5 [T-DOC-LAZY-REFERENCE],
>   B1 [T-EXP-H-GDICT-01] (segurado ate' A4, feito), C [T-DIST-RELEASE-0.8.0] (blocked).
> - **B1 SEGURADO** por decisao do owner (foco no workstream A primeiro).

**Snapshot 2026-06-08** (**Schema/quality gadget COMPLETO + incidente
OneDrive recuperado + push remoto**) — resumo desde 06-03. Atualizacoes
posteriores nos blocos **SESSAO** acima (ate' 2026-06-17):

- **Schema/Quality Gadget (T-RECOVER-SCHEMA-MULTI-TABLE) — COMPLETO**, em
  `scripts/schema_gadget/` (auxiliar, ALERT-ONLY, NUNCA arruma, `src/tcf`
  intocado). 4 fases:
  - Fase 1 `fk_detect.py` — FK candidate por overlap de valores + confiança
    graduada (nome+cardinalidade). TPC-H: 9/9 recall, 0 FP em `alta` (d6b5d2e).
  - Fase 3 `sideouts_quality.py` — alertas ZERO-CUSTO (constant, duplicate_key
    single-PK, type_drift fração-numérica). Validação adversarial (workflow 7
    datasets) removeu useless_id (94% ruído em tpch) (9ed66de).
  - Fase 4 `report.py`+`__main__.py` — CLI `python -m schema_gadget
    {list|analyze}` markdown/JSON (484ce9b).
  - Fase 2 `date_check.py` — impossible_date/format_mix/suspicious_date,
    auto-detecta colunas-data. NÃO zero-custo (scan calendário). Validado por
    corrupção controlada (0 FP no real limpo, recall total no corrompido) (88618f8).
  - ~40 testes CI-friendly. Ticket closed-done. T-DATA-3 deixou de bloquear.
- **Incidente OneDrive (2026-06-03→08, ADR-0021)**: OneDrive criou cópias de
  conflito `-DESKTOP-SG30VJF` e reverteu `main` 158 commits (latência local,
  1 máquina, RARO — não sistêmico). RECUPERADO: backup Z: + reset p/ HEAD real
  + limpeza. Nada perdido. Repo VIVE no OneDrive → checar HEAD/`import tcf` no
  início de sessão (memória `reference-onedrive-git-corruption-risk`).
- **Git remoto SADIO**: `origin/main` sincronizado (push fast-forward dos ~45
  commits). Branch-lixo `main-DESKTOP-SG30VJF` removido local e **confirmado
  ausente no remoto** (2026-06-16: `git ls-remote` mostra so' `main` + tag `v0.7.1`).

**Anterior 2026-06-03** (**Datasets BR/CNPJ + H-PERF-06 Cython +
shaper gating + reorg separacao de concerns**). 33 commits desde o bloco
anterior. Resumo:

- **Datasets novos** (referencia leve no git; dados reais regeneraveis em Z:):
  - `ibge-municipios` (5571 municipios BR, geografia real) — commit 29024f7
  - `tpch-sf01` (TPC-H SF=0.1, ~866k linhas, FK OK) — commit 4733f52
  - `br-identidades` (SINTETICO: 500k pessoas CPF + 100k empresas CNPJ,
    geografia IBGE reusada, FK socio_cpf) — commit f5e2fa8
  - `receita-cnpj` (REAL non-PII: 200k estabelecimentos Receita Federal) —
    commit f7ded09. **Nature CNPJ medida em dado real: 64.1% vs M10 108.4%
    = ganho 40.9%** (>> gate 5%). 1a fonte ECOLOGICA de check-digit ->
    **nature CNPJ confirmada-empirica** (confianca Media, falta N>=5 fontes).
  - tpch part/partsupp samples emitidos (T-DATA-4, commit c9b4984)
  - Setup via WebDAV: Receita migrou pra Nextcloud (`/public.php/webdav`);
    `setup_receita_cnpj.py` faz streaming-stop (nao baixa os ~2GB).
- **H-PERF-06-v2** (acelerar HCC `_detect_compositions`, byte-canonical):
  - Fase A: prune top-K + early-term (ADR-0019, commit 8118d7a)
  - Fase B: acelerador **Cython opcional** com fallback pure-Python
    byte-identico (ADR-0020, commit f44f7d3). `src/tcf/_core/detect.pyx`.
    Cumulativo ~2.67x speedup encode (online-retail 20k x 8col).
- **Shaper** (tool auxiliar, NAO TCF-core) cientificamente validado:
  `tests/test_shaper_scientific.py` (10 testes P1-P5: fk_preserving,
  stratify chi2+TVD, join, volume marginal, schema levels). Aprovado p/
  uso <=100k linhas (T-SHAPER-SCIENTIFIC-GATING, commit 004e8b0).
- **Gate real-world** byte-canonical: `tests/test_real_world_snapshots.py`
  (retail Description/StockCode + lineitem l_comment, regime n_tam_est>=3) —
  T-REGRESSION-REAL-WORLD, commit bb321c5. Mudancas em HCC/prune DEVEM passar.
- **Reorg separacao de concerns** (Fases 0-7, commits 5a15538..bb02cff):
  benchmark LLM v0.5 consolidado em `llm-benchmark/` (harness); catalogo
  findings FICA em `docs/findings/` (research compendium); motor v0.5 em
  `old/tcf/` revisto (`LEVELS-REVIEW.md` — niveis L0-L3 desambiguados do
  codigo). README enxuto 332->184 linhas. **src/tcf INTOCADO** (verificado).
- **Bugs ADR-0006/0007** fixados (commit 2b6edc0): separador ref->lit p/
  `,`/`~`; decode preserva string vazia.

**Anterior 2026-05-27** (**Auditoria profunda + fechamento do limbo**:
workflow 6 dimensoes mapeou 197 itens (76 pra repensar). Limbo de hipoteses
nunca concluidas foi fechado empiricamente (lab `2026-05-27-naturezas-reais-uci/`):
naturezas raras/Pacote 7 re-caracterizadas nos UCI — estrutura EXISTE (refutacao
anterior foi dataset errado); novo achado de ponto cego baixa-cardinalidade
(TCF infla colunas curtas ate' 2.3x); fallback identity prototipado (0.8-10.2%,
RT OK). Todos exigem format change → roadmap **v2.0** ([ADR-0018](docs/adr/0018-v2-format-roadmap.md)).
**B-tier resolvido**: H-DA-01 seq-RLE CONFIRMADO forte (beijing -29.5% se removido,
nao marginal). v1.0 segue pronta pra tag (limbo agora caracterizado+decidido, nao esquecido).

**Anterior 2026-05-27** (**Sprint 3 v1.0**: Validation Plan ADR-0017 8/9 +
packaging fix critico (pyproject empacotava old/tcf v0.5) + docs Diataxis. Commit 92fed11.

**Anterior 2026-05-27** (**Sprint 2 v1.0 fechado**: ADR-0017
proposed (freeze format+API em v1.0, 339 linhas com 5+1 enforcement
features); benchmark UCI extension (wine 90.9%, beijing 71.7%, retail
23.7% — **TCF vence 7/9 datasets** acumulados); TCF-format.md ganha
seccao "Versionamento" + Estado v1.0 atualizado. Pendente pra tag
v1.0.0: Validation Plan 10 items em [ADR-0017](docs/adr/0017-format-spec-v1-frozen.md).

**Anterior 2026-05-27** (**Sprint 1 v1.0**: T-DATA-1 3 datasets UCI
baixados + canonical rodado; bug encoder seq-RLE multi-delta `+-1,0`
encontrado e corrigido (decoder rejeitava); suite regressao formal
`tests/test_regression_v1_baseline.py` (21 tests: D1-D9 snapshot + D17a
322B INVARIANT). 259 tests passing. Commit 304f38a.

**Anterior 2026-05-27** (**Consolidacao dirty lab**: 17 labs
pos-canonical movidos pra `experiments/lab/dirty/old/welded/` (10) ou
`old/refuted/` (7). Topo do dirty agora tem **3 labs ativos +
1 baseline-consolidado**. Novo
[`2026-05-27-baseline-consolidado/`](experiments/lab/dirty/2026-05-27-baseline-consolidado/)
com METRICS.md (D1-D9 1523B, D17a 322B INVARIANT), ADRs-INDEX.md
(16 ADRs 0001-0016), lessons-learned.md, run-baseline.py reproduzivel.
MAP.md atualizado. **Source of truth pra comparacoes futuras**.

**Anterior 2026-05-24** (**CHECKPOINT sessao maxima**: 3 ADRs
welded canonical (0014 unified API, 0015 natures, 0016 multi-delta).
14 sub-exps dirty + benchmark consolidado. **TCF vence em 5/6 datasets**
vs csv+brotli. 96 -> 211 tests. Pausa pra retomada — checkpoint em
[`2026-05-24-sessao-maxima-natures-multi-delta.md`](experiments/lab/dirty/notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md).

**Anterior nesta sessao**: ADR-0016 WELDED — Bug #2 sub-exp 14 fix:
HCC seq-RLE multi-delta `*N+d1,d2,...|template`. M10 markers preserved
pra uniform; CSV format pra mixed. D-IP-subnet 1000 sem nature:
117.51% -> **4.18%** (-96.4%). D1-D9 byte-canonical preservado.
Bug #1 (atom detection) superseded. 19 tests novos.
Suite completa: 211 passed (+19) + 1 pre-existing fail.

**Anterior**: **ADR-0015 WELDED + extensao SPEC_IP**:
`src/tcf/natures/` package canonical com:
- `TemplatedCheckedSpec` + SPEC_CPF + SPEC_CNPJ (CPF -64%)
- `TemplatedPaddedSpec` + SPEC_IP (IP subnet 1000 = **229B / 1.71%** confirmado)
- Protocol uniforme: spec.encode_value/decode_value/classify_value methods
- Polimorfico zero `isinstance` (Strategy pattern, separacao responsabilidades)
- API publica: `encode(values, nature=SPEC_CPF/SPEC_CNPJ/SPEC_IP)` opt-in
- Default sem nature preserva M10 INVARIANT byte-canonical D17a 322B
- 37 tests novos (21 test_natures.py + 16 test_natures_ip.py)
- Suite completa: 192 passed (+37) + 1 pre-existing fail.

**Dirty lab CPF/CNPJ/IP completo + 3 tickets P2/P3
novos registrados**: 14 sub-exps executados. Achados sumarizados:
- Sub-exps 01-09: CPF/CNPJ caracterizacao + variantes B/C + fallback + stats ISO 25012
- Sub-exp 10 debug OBAT/HCC: 6 cases revelaram comportamentos
- Sub-exp 11: hipotese gating ADR-0010 **REFUTADA** (min_len bypass nao muda)
- Sub-exp 12 IP hex variante D: **abandonada** (entre B e C, nunca vence)
- Sub-exp 13 base-aware seq-RLE: **arquitetura validada** (regression OK), mas
  ganho marginal em hex (-94B subnet). H1 partially refutada.
- Sub-exp 14 cross-subnet investigation: **2 bugs reais identificados**:
  (1) M8A nao cria atom secundario; (2) compare_for_seq rejeita multi-run delta
- 3 tickets P2/P3 registrados: T-CODE-HCC-MULTI-DELTA-FIX, 
  T-CODE-HCC-ATOM-DETECTION-REFINE, T-CODE-LAYERED-PIPELINE
- Nota arquitetural funil de camadas + toggles + online adaptive + literatura
  (Frame of Reference, PFOR-DELTA, Gorilla, Dictionary encoding))

**Anterior 2026-05-24**: T-CODE-SCHEMA-BUILDER Fase 1+2 WELDED:
novo `src/tcf/schema.py` com `build_schema(data) -> TableSchema`,
`ColumnSchema` + `TableSchema` dataclasses, `to_dict()` + `to_json()`.
Reaproveita 100% SideOutputs (ColumnFeatures, cadence_info, min_len,
seq_rle_runs, multi_info). Output deterministico. 24/24 tests novos
(`test_schema.py`). Suite: 155 passed (+24) + 1 xfailed + 1 pre-existing
fail. `natures` placeholder vazio pra Fase 3 (META-TYPE-ENCODERS).

**Anterior 2026-05-24**: T-CODE-ENCODER-MANAGER Fase 1b WELDED
work-stealing: refactor `_encode_columns_parallel` pra submit +
as_completed sorted desc por workload. Benchmark: customer 0.83x,
orders 1.23x (4w) / 1.30x (8w). Conclusao: gargalo NAO eh load
imbalance, eh IPC overhead (Windows spawn ~4s + pickling).
Speedup teto realista ~1.3x sem dependencia externa (joblib/Cython).
Byte-canonical preservado. 82 tests OK. Otimizacoes alem adiadas
pra Fase 1c (joblib opcional) ou Fase 4 (streaming chunks).

**Fase 1 anterior 2026-05-24**:
`encode(data, parallel=False|True|N)` via ProcessPoolExecutor.
`_worker_encode_column` picklavel. D17a 322B INVARIANT preservado em
modo parallel. 14/14 tests novos (`test_parallel.py`). SideOutputs
serializado entre workers funciona.

**Sessao 2 anterior 2026-05-24**: O-FMT-14
header desacoplavel/opcional registrado em `futuras-otimizacoes-formato.md`.
Nova nota `naturezas-templated-2026-05-24.md` cataloga sub-naturezas
de T02 Templated (CPF/IP/MAC/telefone/CEP/EAN/IBAN) + T04 Checksummed
(CPF/CNPJ/Luhn) + LR Lossy (FLOAT-PREC/GEO/MONETARY) + CP Composite
(datetime/endereco/money). Hipoteses H-TM-*/H-LR-*/H-CP-* registradas
em roadmap-hipoteses.md secao Pacote 7. META-TYPE-ENCODERS atualizado.
Lab nao iniciado — criterio reabertura: T-DATA-1 download + caracterizacao
em datasets dedicados.

**Sessao 1 anterior 2026-05-24**: API UNIFICADA ADR-0014: `encode(list|dict)`
+ `decode(text)` por dispatch (tipo + shebang). Single = caso particular de
multi com 1 coluna. `SideOutputs` recipiente opcional captura
column_features, cadence_info, OBAT log, HCC trace/rede, seq_rle_runs,
multi_info, per_col. `encode_table`/`decode_table` viram deprecated aliases.
D17a 322B INVARIANT preservado. 117 passed (+21 novos) + 1 xfailed. 4 novos
tickets P2/P3: T-CODE-ENCODER-MANAGER (revive D13 v0.4), T-CODE-PLAN-CONTRACT,
T-CODE-SCHEMA-BUILDER (consume SideOutputs), T-CODE-OUTPUT-SINKS.
TCF-format.md expandido com pipeline ASCII unificado + camadas futuras.)

> **Como ler este documento**: este e' o ponto de entrada
> bibliografico do projeto. Se um sistema novo (humano ou Claude)
> precisar entender **onde estamos agora**, comeca por aqui.
> Sempre atualizar este arquivo ao fechar sub-experimento ou tomar
> decisao estrutural. **Status absoluto**, nao incremental.
>
> **Sistema de discoverability (novo 2026-05-18)**:
> - `CLAUDE.md` raiz — guia pra Claude Code com inventario completo
> - `MAP.md` raiz — wayfinding map
> - `INDEX.md` raiz — auto-gerado por `scripts/index.py`
> - `docs/adr/` — Architecture Decision Records numerados
> - `docs/vocabulary.md` — vocabulario controlado
> - `docs/how-to/audit-memorias-e-documentacao.md` — auditoria periodica
> - `experiments/lab/dirty/notas/checkpoints/` — pausas explicitas
>
> **Checkpoint ativo**:
> [`2026-05-24-sessao-maxima-natures-multi-delta.md`](experiments/lab/dirty/notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md)
> — 3 ADRs welded canonical (0014/0015/0016); 14 sub-exps; benchmark
> consolidado (TCF vence 5/6); pronto pra retomada
>
> Checkpoint anterior:
> [`2026-05-18-pausa-para-organizar-documentacao.md`](experiments/lab/dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md)

---

## TCF — visao 1 paragrafo

**TCF** (Tabular Compact Format) e' um formato de **compressao de
strings tabulares** v0.6 com pipeline canonical delta-aware (M10
baseline, ADR-0011):

- **Pre-pass** — `analyze_column` (ColumnFeatures) + `detect_cadence`
  (regras 1+2, ADR-0008) + `detect_min_len` (heur v3 + gating n>=100,
  ADR-0010)
- **OBAT** (Online Bidirectional Affix Tokenizer) — tokeniza via
  LCP+LCS. `processar_with_hint` (shape-preserve) ou `processar`
  canonical. Em `src/tcf/core/` + `src/tcf/obat_shape.py`.
- **HCC** (Hierarchical Compositional Coding, M8.A + seq-RLE) —
  detector unificado + emit composicional + seq-RLE near-identical
  (`*N+delta|template`). Em `src/tcf/composicional/`.

API publica unificada (ADR-0014): `from tcf import encode, decode, SideOutputs`.
- `encode(list)` -> body single-col (sem shebang)
- `encode(dict)` -> multi-col com header `#TCF.6 M`
- `decode(text)` -> dispatch automatico pelo shebang
- `SideOutputs()` opcional captura features/logs/traces internos

RT byte-canonical validado em D1-D9 (M10 baseline 1523B, vs M9 antigo
1615B), D17a multi-col (322B INVARIANT), Adult+TPC-H single-col 57 cols,
9 tabelas multi-col (Adult + TPC-H tier 1+2, 136k linhas, -33.02% weighted
vs raw, -31.46% vs single concat, RT 9/9).

---

## Foco atual (2026-06-03)

v1.0 estavel (formato `#TCF.6` + API congelados, ADR-0017). Apos as sessoes
recentes: datasets BR/CNPJ adicionados, nature CNPJ confirmada-empirica em
dado real, H-PERF-06 Cython welded, shaper validado, reorg de separacao de
concerns completa (Fases 0-7). **`src/tcf/` intocado** em toda a reorg/datasets.
**Decisao do proximo pacote pendente** — ver "Proximas direcoes" no fim.
Candidatos: T-SHAPER-CODE-HARDENING (escala >100k), roadmap v2.0 (ADR-0018),
fases parciais T-CODE, ou mais datasets (gaps de cobertura).

### Historico — Ciclo 2026-05-21/22 (Revalidacao + H-DA-11 fechado)

- **2026-05-21 Pacote 2** (escape deduction H-ED-01..04): CLOSED-INSUFFICIENT-GAIN
  (real-world max 1.13% << criterio 5%). Primeiro ticket YAML frontmatter
  validou metodologia. Aprendizado: sintetico "digit-dominant" nao
  generaliza pra real-world.

- **2026-05-21 Revisao conceitual** de hipoteses confirmada-empirica:
  classificadas A/B/C por evidencia real-world. Lab dirty `2026-05-21-revalidacao-categoria-B/`
  + ticket T-REVAL-H-DA-01-06-10.

- **2026-05-21 T-REVAL Categoria B**: CLOSED-COMPLETED-WITH-SURPRISES
  - H-DA-06 SUBSUMIDA em H-DA-09b-v2 (cobertura 87.5% real-world)
  - H-DA-01 MARGINAL real-world (1.36%, 16.3x reducao vs sint)
  - **H-DA-10 CONFIRMADA INESPERADAMENTE** (9.92% weighted)
  - Nova H-DA-11 decorrente

- **2026-05-22 T-EXP-H-DA-11**: CLOSED-CANONICAL-WELDED (ADR-0010)
  - Heuristica v3 (decision tree shallow em avg_len + card + is_numeric)
  - Gating n_threshold=100 preserva M9 baseline 1615B EXATO
  - **Adult+TPC-H ganho 9.87% weighted real-world**
  - `src/tcf/auto_min_len.py` (novo) + `src/tcf/encoder.py` modificado
  - RT 100%: D1-D9 9/9 + real-world 57/57

- **2026-05-22 T-CODE-H-DA-11c**: CLOSED-REFACTOR-COMPLETED (zero-risk)
  - Novo `src/tcf/column_features.py` (ColumnFeatures + analyze_column)
  - Refator `src/tcf/auto_min_len.py` com APIs from_features + wrapper
  - Output IDENTICO ao pre-refactor (1615B + 9.87% + RT 100%)
  - Prepara terreno pra T02-T07 + weld futuro de detect_cadence canonical

- **2026-05-22 T-CODE-PACOTE1-WELD-CANONICAL**: CLOSED (ADR-0011)
  - Pipeline canonical delta-aware completo welded em src/tcf
  - Novos modulos: `auto_cadence.py`, `obat_shape.py`, `composicional/hcc_seqrle.py`
  - `encoder.py` + `decoder.py` modificados (pipeline + HCCSeqRLE.decode)
  - **D1-D9 baseline mudou: M9=1615B → M10=1523B (-92B, -5.70%)**
  - **Real-world ganho 11.73% weighted** (vs M9 puro 1,008,003B → 889,714B)
  - RT 100%: 9/9 + 20/20 sint + 57/57 real-world

- **2026-05-22 T-REVAL-H-DA-07**: CLOSED-CONFIRMED-REAL-WORLD
  - Shape-preserve gating funciona: 62/66 cols sem mudanca
  - 2 wins enormes: c_name -98.19%, D9 -48.03%
  - 2 losses pequenas: l_extendedprice +0.65%, c_acctbal +0.20%
  - Real-world weighted: -0.46% (ganho marginal)
  - Categoria B residual fechada

- **2026-05-23 T-EXP-H-PERF-05d**: CLOSED-VALIDATED-WITH-BYTE-DIVERGENCE
  - Fase 1 profile GO (rebuild=46% _dc, 0.3% lines/iter)
  - Fase 2 prototype IncrementalSyntax: 37/41 byte-canonical OK
  - 4 divergencias em datetime TPC-H (+62B / 80kB = 0.08%)
  - Causa: ordem Counter difere (rebuild vs incremental)
  - Welding adiado (fix byte-canonical complexo OU aceitar M11)
  - Pacote 4 permanece fechado-parcial; ADR-0009 OBAT continua win principal

- **2026-05-23 Reflexao naturezas numericas**:
  - Nota `notas/naturezas-numericas-2026-05-23.md` cataloga ~12 naturezas
  - 4 ja' welded (incremento, cadencia, alta-card numerica, comprimento)
  - Pacote 5 (enumerated) testado e refutado em sub-exp

- **2026-05-23 T-EXP-PACOTE5-T03-ENUMERATED**: CLOSED-NO-GO-M10-SUFICIENTE
  - Caracterizacao 37 low-card cols (Adult + TPC-H)
  - M10 ja' captura via dedup + seq-RLE eficientemente
  - Encoder explicit seria PIOR em runs adjacentes (l_linestatus -141%)
  - So' ganharia em valores LONGOS sem runs (c_mktsegment +30%)
  - Weighted total real-world: -2.28% (regressao)
  - **Aprendizado meta**: M10 e' encoder enumerated implicito eficiente
  - **Anti-incidente**: hipotese promissora conceitualmente refutada
    em medicao empirica (mesmo padrao Pacote 2)

- **2026-05-23 Pacote 3 (parser robustness) — ADR-0007 ACCEPTED + WELDED**:
  - Fix Opcao B (separator `*` em ref->lit ambiguo) ja' estava welded
    em src/tcf/composicional/syntax.py desde 2026-05-19 (sem docs atualizadas)
  - Sub-exp 05 valida: 10/10 casos minimos OK (era 7/10), M10 1523B
    preservado, RT 100% real-world (57/57)
  - ADR-0007 atualizado proposed -> accepted + welded
  - Roadmap H-FIX-03 atualizado para WELDED; H-FIX-01 refutada
    (Opcao A perde pra B); H-FIX-02 N/A

- **2026-05-23 T-EXP-H-DA-09c-d-e**: CLOSED-NO-GO-THRESHOLD-07-OTIMO
  - Varreu threshold detect_cadence {0.5, 0.6, 0.7, 0.8} em 66 cols
  - Thr 0.7 atual e' otimo (0.5/0.6 dao -3.06% regressao real-world)
  - H-DA-09d (multivariada) + H-DA-09e (adaptativo) adiados
  - **Consolidacao**: 3 refutacoes na sessao (Pacote 2, Pacote 5,
    H-DA-09c) confirmam que TCF M10 esta bem calibrada

- **2026-05-23 T-DOC-1/2 + T-CLEAN-1**: CLOSED (aderencia metodologica P3)
  - **T-DOC-1**: CITATION.cff criado (v0.6, MIT); README "How to cite";
    DOI Zenodo defer ate' v1.0/paper
  - **T-DOC-2**: ADR-0012 criado documentando mapeamento Diataxis local
    (docs/algorithms→reference, docs/theory→explanation); MAP.md atualizado
  - **T-CLEAN-1**: .pre-commit-config.yaml criado (ruff + detect-secrets +
    basicos + custom no-cache-dirs); pyproject.toml + README dev setup;
    `pre-commit install` pending owner

- **2026-05-23 T-EXP-NATUREZAS-RARAS**: CLOSED-NO-GO
  - Exploracao naturezas #5 (range narrow) e #8 (suffix/arredondamento)
  - #8 Suffix: -4.45% weighted (regressao — M10 ja' captura categoricas
    via dedup)
  - #5 Range: +1.08% marginal (3 cols com potencial isolado: l_quantity,
    l_linenumber, age — peso baixo no agregado)
  - **4a refutacao da sessao** (5 contando T-EXP-H-DA-09c)
  - Padroes financeiros reais precisariam dataset dedicado (defer)

- **2026-05-23 T-DATA-1**: CLOSED 2026-06-02 (3 datasets baixados + canonical setup; raw em Z:/tcf-data/external/, metadata em datasets/canonical/)
  - 3 datasets UCI canonicos planejados:
    - Online Retail (~45MB, UnitPrice .99/.95/.50 = #8 arredondamento)
    - Beijing PM2.5 (~2MB, PRES 991-1046 = #5 range narrow)
    - Wine Quality (~100KB, density/pH decimais cientificos)
  - Scripts setup criados: setup_wine_quality.py, setup_beijing_pm25.py,
    setup_online_retail.py (padrao similar a setup_adult.py)
  - READMEs + metadata.json em datasets/canonical/{name}/
  - Owner roda localmente: `pip install -e ".[datasets]"` + `python scripts/setup_*.py`
  - Futuro T-EXP-NATUREZAS-RARAS-V2 re-testa #5/#8 com novos datasets

- **2026-05-23 T-EXP-MULTI-COL-SCALING**: **CLOSED-WELDED-CANONICAL** (ADR-0013)
  - Port `multi_col.py` (EXP-011 M9) pra canonical M10 (`from tcf import encode, decode`)
  - D17a (sint 13x4): 322B preservado vs EXP-011, RT OK
  - **9 tabelas real-world** (Adult Census + TPC-H tier 1+2, 136k linhas):
    - **-33.02% weighted vs raw** (15,848,939 → 10,614,897 bytes)
    - **-31.46% weighted vs single-col concat** (controle)
    - RT **9/9** OK
    - Adult Census destaque: -65.14% vs raw (15 cols mixed)
    - **Lineitem 60k x 16**: -17.11% raw, -30.73% single, RT OK (16.6 min)
    - Header overhead < 1% em datasets >= 1500 rows (5/5)
    - Outlier region (5 rows): +3.87% vs raw (header dominante, esperado)
  - **WELDED em src/tcf** (Opcao A aprovada):
    - `src/tcf/multi.py` novo (encode_table + decode_table + MAGIC_MULTI)
    - `src/tcf/__init__.py` atualizado: API publica agora 4 funcs
    - ADR-0013 criado (accepted + welded)
    - `tests/test_multi_col_rt.py` novo (17/17 passing, D17a 322B INVARIANT)
  - Sub-exp dirty: `experiments/lab/dirty/2026-05-23-multi-column-scaling/`

- **2026-05-23 T-CI-1 + T-CI-2**: CLOSED (CI completo em uma rodada)
  - **T-CI-1**: .github/workflows/ci.yml com job lint (pre-commit)
  - **T-CI-2**: refactor tests + job test ativado
    - 5 tests v0.5 broken movidos pra tests/_archive_v05/
    - tests/conftest.py + pytest markers (requires_data)
    - pyproject.toml: testpaths + norecursedirs + markers
    - tests/test_core_rt.py NOVO (31 tests CI-friendly: M10 baseline
      INVARIANT 1523B + RT edge cases + Pacote 3 comma fix)
    - workflow CI matrix py 3.10/3.11/3.12 ativo
  - Validacao local: 30 passed + 1 xfailed (edge case `encode([])`),
    50 deselected (requires_data)

**Pacote 4 — Perf OBAT/HCC** (fechado 2026-05-20):
- H-PERF-02 WELDED (ADR-0009) — hash trigrama, alpha 1.75→1.42
- H-PERF-04/05/06 ADIADOS (Patricia trie, counter incremental, Cython)

**Proximo pacote — decisao pendente**:
- ~~**H-DA-11c** consolidar pre-pass features~~ (FEITO 2026-05-22)
- ~~**Pacote 1 weld canonical**~~ (FEITO 2026-05-22, ADR-0011)
- **H-DA-07** revalidacao (categoria B residual)
- **H-PERF-05d** counter incremental HCC (zero-risk, alto potencial)
- **T02-T07** outras naturezas pre-tx (criterio ainda nao atingido)

### Pacotes fechados (referencia)

| Pacote | Foco | Status | Welding |
|---|---|---|---|
| **Pacote 1** (Delta-aware) | auto-pre detect_cadence → OBAT hint → HCC seq-RLE | fechado | EXP-010 (clean), 20/20 RT |
| **Pacote 1 refino** (H-DA-09b-v2) | regra numeric+high-cardinality em real-world | fechado | ADR-0008 em EXP-010/auto_pre |
| **Pacote 2** (escape deduction) | H-ED-01..04: ganho real-world insuficiente | CLOSED-INSUFFICIENT-GAIN 2026-05-21 | — |
| **Pacote 3** (parser robustness) | bug `,` em literais HCC | fechado | ADR-0007 em src/tcf/composicional/syntax.py |
| **Pacote 4** (perf OBAT) — parcial | hash trigrama OBAT | **welded** (sub-pacote 1) | ADR-0009 em src/tcf/core/online.py |
| **T-REVAL Categoria B** | revalidacao H-DA-01/06/10 em real-world | CLOSED 2026-05-21 (surpresa H-DA-10 9.92%) | — |
| **T-EXP-H-DA-11** | auto-detect min_len por coluna | **WELDED canonical** 2026-05-22 | **ADR-0010 em src/tcf/auto_min_len.py + src/tcf/encoder.py** (9.87% real-world) |
| **T-CODE-H-DA-11c** | ColumnFeatures unificado (refactor) | CLOSED 2026-05-22 | **src/tcf/column_features.py + refactor auto_min_len.py** (zero-risk) |
| **T-CODE-PACOTE1-WELD-CANONICAL** | Pipeline delta-aware completo canonical (M9 → M10) | **CLOSED 2026-05-22** | **ADR-0011: auto_cadence + obat_shape + hcc_seqrle + encoder/decoder modificados** (11.73% real-world) |
| **T-REVAL-H-DA-07** | Shape-preserve gating em real-world | CLOSED-CONFIRMED 2026-05-22 | gating preserva 62/66 cols neutras; 2 wins (c_name -98%, D9 -48%), 2 losses pequenas |
| **T-EXP-H-PERF-05d** | Counter incremental HCC | CLOSED-VALIDATED-WITH-BYTE-DIVERGENCE 2026-05-23 | 37/41 byte-canonical OK; 4 datetime TPC-H divergem 0.08%; welding adiado |
| **T-EXP-PACOTE5-T03-ENUMERATED** | Encoder enumerated explicito | CLOSED-NO-GO-M10-SUFICIENTE 2026-05-23 | M10 ja' captura via dedup+seq-RLE; encoder explicit PIOR em runs adjacentes |
| **Pacote 3** (parser robustness, ADR-0007) | Fix bug `,` em literais (Opcao B separator) | **WELDED canonical** (welded 2026-05-19, ADR accepted 2026-05-23) | src/tcf/composicional/syntax.py:435-442 |
| **T-EXP-H-DA-09c-d-e** | Tunar threshold detect_cadence | CLOSED-NO-GO 2026-05-23 | thr 0.7 ja' otimo; H-DA-09d/e adiados |
| **T-DOC-1** | CITATION.cff | CLOSED 2026-05-23 | criado v0.6 MIT; DOI Zenodo defer |
| **T-DOC-2** | Diataxis naming local | CLOSED 2026-05-23 | ADR-0012 criado |
| **T-CLEAN-1** | Pre-commit hooks | CLOSED 2026-05-23 | config criado; install pending owner |
| **T-EXP-NATUREZAS-RARAS** | Naturezas #5 (range) #8 (suffix) | CLOSED-NO-GO 2026-05-23 | M10 ja' captura suffix categorico; range marginal +1.08% weighted |
| **T-CI-1** | GitHub Actions CI Fase 1 | CLOSED 2026-05-23 | workflow ci.yml lint + test ativado (matrix py 3.10/3.11/3.12) |
| **T-CI-2** | Tests refactor CI-friendly | CLOSED 2026-05-23 | 5 v0.5 archived; 31 RT tests novos; marker requires_data |
| **T-DATA-1** | 3 datasets UCI/OpenML canonicos | **CLOSED 2026-06-02** | online-retail, beijing-pm25, wine-quality baixados; canonical setup + raw em Z:/tcf-data/external/ |
| **T-EXP-MULTI-COL-SCALING** | Multi-col welded canonical em src/tcf (ADR-0013, Opcao A) | **CLOSED-WELDED-CANONICAL 2026-05-23** | src/tcf/multi.py + encode_table/decode_table API publica; D17a 322B INVARIANT; 17/17 tests novos; 9 tabelas real-world: -33.02% raw weighted |
| **T-CODE-UNIFIED-API** | API unificada `encode(list\|dict)` + SideOutputs (ADR-0014, supersede ADR-0013) | **CLOSED-WELDED-CANONICAL 2026-05-24** | encoder/decoder dispatcher + side_outputs.py + multi.py interno; D17a 322B preservado; 117 passed (+21); deprecated aliases mantidos |

### Pacotes registrados, nao iniciados

| Pacote | Foco | Status |
|---|---|---|
| **Pacote 2** (escape deduction) | H-ED-01..04: omitir `\digits` quando deduzivel | registrado, adiado |
| **Pacote 4** (perf — restante) | H-PERF-04/05/06: HCC opt + trigrama meio + Cython | em curso |

### Arquivo historico (superseded)

- **T01 incremental** (`2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/`):
  13 sub-exps pre-tx multi-pass. **Superseded** pelo Pacote 1 Delta-aware
  (que cabe no vertice triplice single-pass). Mantido como referencia
  metodologica; nao guia evolucao.
- **META-TYPE-ENCODERS** (`tickets/META-TYPE-ENCODERS.md`): planejou
  7 naturezas (T01-T07) + 5 estudos (L01-L05). Pos-Pacote 1, foi
  realinhado: T01 absorvido como OBAT-level, T02-T07 e L01-L05
  permanecem adiados aguardando 2-3 naturezas validadas.

**Roadmap cross-lab**: [`experiments/lab/dirty/notas/roadmap-hipoteses.md`](experiments/lab/dirty/notas/roadmap-hipoteses.md)
**Diario mais recente**: [`experiments/lab/dirty/notas/diario/2026-05-19.md`](experiments/lab/dirty/notas/diario/2026-05-19.md)

---

## Datasets ativos

### Canonical (`datasets/canonical/` — metadata+sample no git, dados reais em Z:)
| Dataset | Tipo | Volume | Nota |
|---|---|---|---|
| adult-census | real (UCI) | 48842 | single-table mixed |
| tpch-sf001 | gerado (DuckDB) | 60k lineitem | SF=0.01, 8 tabelas FK |
| tpch-sf01 | gerado (DuckDB) | 600k lineitem | SF=0.1, ~866k total |
| online-retail | real (UCI) | 541909 | free-text Description, .99 prices |
| beijing-pm25 | real (UCI) | 43824 | sensor decimais, range narrow |
| wine-quality | real (UCI) | 6497 | features quimicas decimais |
| ibge-municipios | real (IBGE) | 5571 | BR, categoria hierarquica acentuada |
| br-identidades | **sintetico** | 600k | CPF+CNPJ validos, geografia IBGE; vies declarado |
| receita-cnpj | **real non-PII** | 200k | CNPJ Receita; nature CNPJ 40.9% real |

> Gaps de cobertura + roadmap em memoria `project-dataset-coverage-map`
> (free-text longo, IP/UUID, monetary-string, >1M linhas).

### Synthetic (`datasets/synthetic/`):

### Core TCF (D1-D9) — controle algoritmo
Padroes estruturais (afixos, wrappers). Cobertos pelo TCF-CORE
canonical. Total 2981 raw -> 1523 TCF (51.1%, baseline M10/ADR-0011 pinado
em test_regression_v1_baseline.py; 1615B era M9 antigo). Referenciados em
EXP-007/008.

### ERP/CRM tipos (D10-D15) — variety (stress de tipos, nao guia)
Formatos misturados artificialmente — uteis pra entender limites,
nao guia de evolucao (cf. diretriz dados-realistas).

### Incremental T01 (D11a-m) — realistic
- `D11a-datas-dia.csv` (12 linhas) — sequencial maio-junho 2026 [day]
- `D11b-datas-borda.csv` (14 linhas) — bordas mes/ano + Feb 29 [day]
- `D11c-datas-mensal.csv` (13 linhas) — fatura mensal dia 5 [day]
- `D11d-datetime-min.csv` (13 linhas) — heartbeat top-of-minute [second]
- `D11e-datetime-mensal.csv` (13 linhas) — fatura mensal datetime (datas+9h) [second]
- `D11f-datetime-ms.csv` (13 linhas) — cadencia 1s [ms]
- `D11g-datetime-us.csv` (13 linhas) — cadencia 1ms (multi-char) [us]
- `D11h-datetime-ns.csv` (13 linhas) — cadencia 1us (multi-char) [ns]
- `D11i-datas-mensal-com-correcao.csv` (7 linhas) — mensal com day corrections (multi-position)
- `D11j-datetime-tz-Z.csv` (13 linhas) — minute cadence, tz constante `Z` [second+tz]
- `D11k-datetime-tz-offset.csv` (13 linhas) — minute cadence, tz constante `-03:00`
- `D11m-datetime-tz-variavel.csv` (6 linhas) — multiplas zonas (-03/+00/+02), mesma UTC absoluta

---

## Tickets ativos

`tickets/`:

| ID | Status | Foco |
|---|---|---|
| [META-NAMING](tickets/META-NAMING.md) | CLOSED | TCF/OBAT/HCC oficial |
| [META-DOCS-V05-OBSOLETE](tickets/META-DOCS-V05-OBSOLETE.md) | CLOSED | archive v0.5 |
| [META-THEORY-MOVE](tickets/META-THEORY-MOVE.md) | CLOSED | mover teoria pra docs/theory/ |
| [META-EXP-FORMAT](tickets/META-EXP-FORMAT.md) | CLOSED | template validacao vs comparativo |
| [META-TYPE-ENCODERS](tickets/META-TYPE-ENCODERS.md) | **OPEN** | plano-mestre T01-T07 + L01-L05 (adiados) |
| [META-PERF-PHASE2](tickets/META-PERF-PHASE2.md) | CLOSED-PARCIAL | Pacote 4 perf phase 2 |
| [META-ESCAPE-DEDUCTION](tickets/META-ESCAPE-DEDUCTION.md) | CLOSED-INSUFFICIENT-GAIN | Pacote 2 |
| [T-REVAL-H-DA-01-06-10](tickets/T-REVAL-H-DA-01-06-10.md) | CLOSED-COMPLETED-WITH-SURPRISES | Revalidacao Categoria B (2026-05-21) |
| [T-EXP-H-DA-11](tickets/T-EXP-H-DA-11.md) | **CLOSED-CANONICAL-WELDED** | Auto-detect min_len (ADR-0010, 9.87%) |
| [T-CODE-H-DA-11c](tickets/T-CODE-H-DA-11c-features-unificadas.md) | **CLOSED-REFACTOR-COMPLETED** | ColumnFeatures unificado (zero-risk) |
| [T-CODE-PACOTE1-WELD-CANONICAL](tickets/T-CODE-PACOTE1-WELD-CANONICAL.md) | **CLOSED 2026-05-22** | Pacote 1 canonical (ADR-0011, M9 → M10, 11.73% real-world) |
| [T-REVAL-H-DA-07](tickets/T-REVAL-H-DA-07.md) | **CLOSED-CONFIRMED-REAL-WORLD** | Shape-preserve gating valida em real-world |
| [T-EXP-H-PERF-05d](tickets/T-EXP-H-PERF-05d.md) | **CLOSED-VALIDATED-WITH-BYTE-DIVERGENCE** | Counter incremental HCC (welding adiado) |
| [T-EXP-PACOTE5-T03-ENUMERATED](tickets/T-EXP-PACOTE5-T03-ENUMERATED.md) | **CLOSED-NO-GO-M10-SUFICIENTE** | Encoder enumerated explicit refutado (M10 ja' captura) |
| [T-DOC-1-citation-cff](tickets/T-DOC-1-citation-cff.md) | **CLOSED 2026-05-23** | CITATION.cff (v0.6, DOI defer) |
| [T-DOC-2-diataxis-naming](tickets/T-DOC-2-diataxis-naming.md) | **CLOSED 2026-05-23** | ADR-0012 Diataxis local |
| [T-CLEAN-1-pre-commit-hooks](tickets/T-CLEAN-1-pre-commit-hooks.md) | **CLOSED 2026-05-23** | .pre-commit-config.yaml |
| [T-EXP-NATUREZAS-RARAS-EXPLORACAO](tickets/T-EXP-NATUREZAS-RARAS-EXPLORACAO.md) | **CLOSED-NO-GO** | naturezas #5/#8 raras em datasets gerais |
| [T-CI-1-github-actions](tickets/T-CI-1-github-actions.md) | **CLOSED 2026-05-23 (Fase 1+2)** | workflow CI completo (lint + test matrix) |
| [T-CI-2-tests-refactor](tickets/T-CI-2-tests-refactor.md) | **CLOSED 2026-05-23** | 5 v0.5 archived; 31 tests novos CI-friendly |
| [T-DATA-1-datasets-financeiros-cientificos](tickets/T-DATA-1-datasets-financeiros-cientificos.md) | **CLOSED 2026-06-02** | 3 datasets UCI/OpenML baixados + canonical setup (Z:/tcf-data/external/) |
| [T-EXP-MULTI-COL-SCALING](tickets/T-EXP-MULTI-COL-SCALING.md) | **CLOSED-WELDED-CANONICAL 2026-05-23** | src/tcf/multi.py welded (ADR-0013); encode_table/decode_table publicos; 17/17 tests; -33.02% raw weighted real-world |
| [ADR-0014 (welded direto)](docs/adr/0014-unified-api-side-outputs.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | API unificada encode(list\|dict) + SideOutputs; ADR-0013 superseded; 117 passed |
| [T-CODE-ENCODER-MANAGER](tickets/T-CODE-ENCODER-MANAGER.md) | **OPEN-FASES-1+1B-WELDED 2026-05-24** | Fase 1+1b: paralelismo `encode(data, parallel=N)` via ProcessPool + work-stealing (sorted desc workload), 14 tests, byte-canonical OK. Speedup ~1.23-1.30x (teto IPC overhead Windows spawn). Fases 1c/2/3/4 pendentes. |
| [T-CODE-OUTPUT-SINKS](tickets/T-CODE-OUTPUT-SINKS.md) | **OPEN P2 2026-05-24** | Contract Sink pluggable, refactor scripts/writers/ (bloqueado por encoder-manager) |
| [T-CODE-PLAN-CONTRACT](tickets/T-CODE-PLAN-CONTRACT.md) | **OPEN P3 2026-05-24** | Plan dataclass (group_by/order/batch_size), habilita O-FMT-01..04 |
| [T-CODE-SCHEMA-BUILDER](tickets/T-CODE-SCHEMA-BUILDER.md) | **OPEN-FASES-1+2-WELDED 2026-05-24** | Fase 1+2: `build_schema(data) -> TableSchema`; ColumnSchema + to_dict/to_json; 24/24 tests; reaproveita SideOutputs 100%. Fase 3 (naturezas) depende META-TYPE-ENCODERS reabrir. |
| [T-CODE-HCC-MULTI-DELTA-FIX](tickets/T-CODE-HCC-MULTI-DELTA-FIX.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | Bug #2 sub-exp 14 fixed via ADR-0016. D-IP-subnet 1000 sem nature: 117.51% -> 4.18% (-96.4%). M10 invariant preservado, marker CSV format opcional. |
| [T-CODE-HCC-ATOM-DETECTION-REFINE](tickets/T-CODE-HCC-ATOM-DETECTION-REFINE.md) | **CLOSED-SUPERSEDED-BY-ADR-0016 2026-05-24** | Bug #1 nao precisa fix isolado — cross-subnet ja' compactado via Bug #2 fix. |
| [ADR-0016 (welded direto)](docs/adr/0016-hcc-multi-delta-seq-rle.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | HCC seq-RLE multi-delta. Marker novo `*N+d1,d2,...|template` opt-in (uniform mantem M10 format). Bug #2 sub-exp 14 fix. 19 tests, D-IP-subnet 1000: 117% -> 4.18%. |
| [T-CODE-LAYERED-PIPELINE](tickets/T-CODE-LAYERED-PIPELINE.md) | **OPEN-FASE-1-WELDED 2026-05-24** | PipelineConfig dataclass + 3 toggles (pre_pass, obat_shape_preserve, hcc_seq_rle). encode(data, layers=cfg) opt-in. D17a 322B INVARIANT + D1-D9 byte-canonical preservados. 25 tests novos. Fase 2 (online adaptive) pendente. |
| [ADR-0015 (welded direto)](docs/adr/0015-natures-templated-checked-weld.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | TemplatedCheckedSpec + SPEC_CPF + SPEC_CNPJ + TemplatedPaddedSpec + SPEC_IP em `src/tcf/natures/`. API publica `encode(values, nature=SPEC_*)` opt-in. CAMADA 0 do funil welded. 37/37 tests, default preserva M10 INVARIANT. IP subnet 1000=229B (1.71%). |
| [T-REGRESSION-REAL-WORLD](tickets/T-REGRESSION-REAL-WORLD.md) | **CLOSED-DONE 2026-05-31** | Gate byte-canonical real-world (retail Description/StockCode + lineitem l_comment, n_tam_est>=3). Fixtures 2k em datasets/samples/. Mudancas HCC/prune DEVEM passar. |
| [T-SHAPER-SCIENTIFIC-GATING](tickets/T-SHAPER-SCIENTIFIC-GATING.md) | **CLOSED-DONE 2026-05-31** | 10 testes estatisticos (P1-P5) validam claims do shaper. Aprovado <=100k linhas. |
| [T-SHAPER-CODE-HARDENING](tickets/T-SHAPER-CODE-HARDENING.md) | **OPEN P2** | Hardening shaper p/ escala >100k (A1 filter-before-load, A3 lstrip bug, A4 dedup, A6 lazy-load). Nao bloqueia uso <=100k. |
| [ADR-0019 (welded)](docs/adr/0019-hcc-detect-compositions-topk-prune.md) | **CLOSED-WELDED 2026-05-30** | H-PERF-06-v2 Fase A: prune top-K + early-term em HCC _detect_compositions. Byte-canonical preservado. |
| [ADR-0020 (welded)](docs/adr/0020-cython-optional-accelerator.md) | **CLOSED-WELDED 2026-05-31** | H-PERF-06-v2 Fase B: acelerador Cython opcional de _detect_compositions, fallback pure-Python byte-identico. ~2.67x cumulativo. |
| [T-DATA-2-RECEITA-CNPJ](tickets/T-DATA-2-RECEITA-CNPJ.md) | **CLOSED-DONE 2026-06-02** | Dataset CNPJ real (200k, non-PII). Nature CNPJ ganho 40.9% em dado real -> confirmada-empirica (confianca Media). |
| [T-DATA-4-TPCH-PART-SAMPLES](tickets/T-DATA-4-TPCH-PART-SAMPLES.md) | **CLOSED-DONE 2026-06-01** | Samples part/partsupp TPC-H committed (categoria hierarquica observavel). |
| [T-DATA-3-EDGE-QUALITY-FIXTURES](tickets/T-DATA-3-EDGE-QUALITY-FIXTURES.md) | **DEFERRED** | Plano de dados de borda p/ gadget de qualidade (bloqueado por T-RECOVER-SCHEMA-MULTI-TABLE; gadget nao existe). |
| Reorg separacao de concerns (Fases 0-7) | **DONE 2026-06-02** | benchmark LLM -> llm-benchmark/; findings ficam em docs/; old/tcf revisto (LEVELS-REVIEW). src/tcf intocado. Ver memoria project-reorg-separation-of-concerns. |
| [T-CODE-EMPTY-FRAG-INDEX-RT](tickets/T-CODE-EMPTY-FRAG-INDEX-RT.md) | **CLOSED 2026-06-13** | [probatório] Bug de RT no core M10 (achado na caracterizacao V2-A): string vazia desloca index de fragmento HCC. 2 modos (syntax._parse_decl frag-index + hcc_seqrle rstrip vazio-final). Fix decode-only/byte-safe; 12 reproducers pinados em test_core_rt; 332 passed; D1-D9=1523B + real-world preservados. |
| [ADR-0022 (welded direto)](docs/adr/0022-v2a-fallback-identity-weld.md) | **CLOSED-WELDED 2026-06-13** | **V2-A fallback identity (abre v2.0)**: opt-in `encode(table, fallback=True)`; por coluna min(TCF, raw); emite `#TCF.7 M` + marcador `!<size>=<name>` sse alguma coluna cai pra raw. Default OFF preserva byte-canonical (D1-D9=1523B, D17a=322B). Caracterizado 9 fontes (7.85% weighted). 340 passed. V2-B/C/D seguem roadmap (ADR-0018). |
| [ADR-0023 (welded direto)](docs/adr/0023-v2-minimal-header-weld.md) | **CLOSED-WELDED 2026-06-14** | **Header v2 minimo** (O-FMT-15+16): opt-in `encode(table, min_header=True)`. Revisao do header: TODO `#TCF.7` dispensa o prefixo `# ` do meta (o flag `M` ja' declara colunas); min_header tambem omite o size da ULTIMA coluna (corpo ate' EOF). #TCF.6 mantem `# ` (congelado). Compoe com fallback. Default OFF preserva byte-canonical. Cadastro README 182->177B (−5). 351 passed. Foco: payload minusculo (memoria project-byte-level-compression-focus). |
| O-FMT-02 `sort_by` (welded direto) | **CLOSED-WELDED 2026-06-14** | **Ordenacao order-free** opt-in `encode(table, sort_by="col")`: reordena linhas pela chave -> agrupa similares -> +compressao (5-15% low-card). Decode retorna a ordem ORDENADA. Pre-encode transform (nao toca pipeline). Default None inalterado. 6 testes TestSortBy. Caracterizado em `2026-06-14-ordering-characterizacao`. |
| [ADR-0025 (welded direto)](docs/adr/0025-v2b-dictionary-categorical-weld.md) | **CLOSED-WELDED 2026-06-14** | **V2-B dicionario/categorico**: 3o candidato do fallback `min(tcf, raw, v2b)`, marcador `@<size>=<name>`. Coluna low-card vira [tabela de unicos]+[stream de indices 1-char] em vez de 1 ref `^idx` por linha. Order-free; gated `2<=K<N, K<=1024`. Zero-regressao por construcao. Caracterizado 8 datasets reais (13.9% weighted, RT 42/42). D17a 307->303 (re-pin ADR-0024/0025). 385 passed. GATE real-world verde. |
| [ADR-0026 (welded direto)](docs/adr/0026-structural-split-weld.md) | **CLOSED-WELDED 2026-06-14** | **Split estrutural** (H-STRUCT-01): 4o candidato do fallback `min(tcf, raw, dict, split)`, marcador `%<size>=<name>`. Valor estruturado (decimal/data/datetime/id) com template uniforme vira campos (template 1x) -> cada campo low-card esmagado pelo V2-B (sinergia = motor). Gate 100% uniforme + >=2 campos + variacao; sem mecanismo de excecao. Auto-detect gated, zero-regressao. **Maior lever do ciclo: 19.39% weighted** em 8 datasets reais (50.4% nas afetadas). Complementa natures CPF/CNPJ (min). Name-guard `!@%`. D17a=303/D1-D9=1523 INTOCADOS (nao dispara em tabela pequena). 398 passed. GATE verde. |

---

## Experimentos clean publicados

`experiments/lab/clean/`:

| EXP | Foco | Status |
|---|---|---|
| EXP-007-prototipo-tcf-core | Validacao byte-canonical src/tcf vs M14 baseline (9/9 OK, 1615 bytes) | pushed |
| EXP-008-compressao-comparada | TCF vs gzip/brotli/zstd/lzma/bz2 em 4 formatos × 15 datasets | pushed |
| EXP-009-pre-tx-natureza | Meta-pasta (stub) — sub-experimentos nascem ao fechar macros dirty | stub |
| EXP-010-tcf-delta-aware-prototype | Prototype clean welded do Pacote 1 (single-column, 20/20 RT, -18% vs canonical) | ativo |
| EXP-011-multi-column-basic | Multi-column basic (per-coluna independente, RT OK em D17a, -34.6% vs raw CSV) | ativo |
| EXP-012-real-world-adult-census | Real-world Adult Census via shaper (RT 4/4 OK, ratio 38-42% em 100-5000 rows) | concluido |
| EXP-013-real-world-tpch | Real-world TPC-H 8 tabelas (RT 8/8 OK apos welding ADR-0007; ratio 90.6% total raw->tcf) | concluido |
| EXP-014-tpch-lineitem-scale | Performance scale lineitem (1k-20k + full 60175). Pre-ADR-0009: O(N^1.75) / 71min full. **Pos-ADR-0009: O(N^1.42) / 18.5min estimado, 21.3min REAL (+15%, RT OK).** RT 5/5 OK | concluido |

EXP-009.1+ ainda nao abertos (criterio: macro dirty fechar com hipotese
confirmada).

---

## Diretrizes ativas (memorias)

- **dados realistas** — TCF e' pra sistemas reais, nao caos artificial.
  D10/D13/D14 sao stress de variety extrema, nao guia.
- **staged pipeline** — "burros e trabalhadores agora, pequenos e
  rapidos depois". Pre-tx em 3 estagios explicitos (identify /
  normalize / optimize). Naive primeiro.
- **template comparativo** — experimentos multi-eixo precisam de
  subpastas + contra-prova + classes + reports multiplos + tabelas
  formatadas (vide META-EXP-FORMAT).
- **vocabulario disciplinado** — sem "incrivel/onde brilha/melhor"
  fora de cenario; usar "diferenca em cenario X".
- **dirty isolado** — codigo experimental nao vai pra src/ ate
  weld deliberado com testes byte-canonical.
- **commit local, push sob demanda** — desde 2026-05-16. Nao mandar
  pro GitHub sem confirmacao explicita.
- **self-containment do .tcf** — arquivo + algoritmo padrao =
  reconstrucao do original. Sem hint externo. Cabecalho (se preciso)
  vive dentro do .tcf. Validado em sub-exp 09.

---

## Estrutura de pastas (apos reorg separacao de concerns 2026-06-02)

```
TCF/
├── STATUS.md                        # este arquivo
├── README.md (enxuto v0.6), CHANGELOG.md, CLAUDE.md, MAP.md, AGENTS.md
├── src/tcf/                         # CANONICAL v0.6 (OBAT + HCC + natures + _core/detect.pyx)
├── datasets/
│   ├── synthetic/                   # D1-D17
│   ├── canonical/                   # 9 datasets (metadata+sample; dados em Z:)
│   └── samples/                     # fixtures committed (real-world gate)
├── llm-benchmark/                   # benchmark LLM v0.5 (ACESSORIO) — harness eval/ + scripts/
├── old/tcf/                         # motor v0.5 niveis L0-L3, congelado (LEVELS-REVIEW.md)
├── docs/
│   ├── algorithms/ adr/ theory/ how-to/ tutorials/   # v0.6 (Diataxis)
│   ├── findings/                    # catalogo cientifico v0.5 LLM (historico, FICA aqui)
│   └── archive/                     # v0.5/v0.1 congelado
├── tickets/                         # planejamento markdown (YAML frontmatter)
├── experiments/
│   ├── lab/{clean,dirty}/           # labs v0.6 (dirty/old/ = M0-M14 + welded + refuted)
│   ├── results/ scratch/            # output LLM (gitignored)
└── tests/                           # suite v0.6 + fixtures
```

---

## Proximas direcoes (ordenado por prioridade)

### Prioridade alta (caminho feliz)

1. ~~**H-DA-07 revalidacao real-world**~~ (FEITO 2026-05-22,
   T-REVAL-H-DA-07: CONFIRMADA)
2. ~~**H-PERF-05d counter incremental HCC**~~ (FEITO 2026-05-23,
   validated-with-byte-divergence; welding adiado)
3. ~~**Pacote 5 T03 enumerated**~~ (TESTADO 2026-05-23: NO-GO,
   M10 ja' captura via dedup+seq-RLE)
4. ~~**H-DA-09c/d/e** refinos detect_cadence~~ (TESTADO 2026-05-23:
   NO-GO, thr 0.7 ja' otimo; 09d/e adiados)
5. ~~**H-FIX-01/02/03** Pacote 3 parser robustness~~ (FEITO 2026-05-23:
   ADR-0007 ACCEPTED + WELDED, H-FIX-03 win via Opcao B separator)
6. ~~**T-DOC-1/2 + T-CLEAN-1**~~ (FEITO 2026-05-23: CITATION.cff,
   ADR-0012, .pre-commit-config.yaml)
7. **H-PERF-06 Cython/Rust port** — adiado, requer build system
8. ~~**Naturezas raras** (#5 range, #8 arredondamento)~~ (TESTADO
   2026-05-23: NO-GO em datasets gerais; #8 -4.45%, #5 +1.08%)
9. ~~**Multi-column scaling** — EXP-011 base, expansao futura~~ (FEITO
   2026-05-23 com Fase 4 lineitem + WELDED canonical: T-EXP-MULTI-COL-SCALING
   port M10 + 9 tabelas real-world + src/tcf/multi.py via ADR-0013;
   API publica encode_table/decode_table; 17/17 tests novos)
10. ~~**CI** — GitHub Actions com pre-commit + tests~~ (FEITO COMPLETO
    2026-05-23: T-CI-1 lint + T-CI-2 tests refactor + job test ativo)
11. ~~**T-CI-2** — refactor tests CI-friendly~~ (FEITO mesmo dia)

### Prioridade media (decisao pendente)

3. **H-PERF-05d counter incremental HCC** — unico zero-risk de alto
   potencial no Pacote 4 ainda aberto (~50-70% HCC perf). Implementacao
   complexa (state entre iters).
4. **H-DA-09c/d/e** — refino threshold/multivariada/adaptativo do
   auto-pre detect_cadence. Decorrentes do Pacote 1.
5. **H-PERF-06 Cython/Rust port** — adiar ate' Python opt esgotar
   (alto overhead, integrar build system).

### Prioridade baixa (adiados explicitamente)

6. **META-TYPE-ENCODERS T02-T07** — outras naturezas (templated,
   enumerated, checked, etc.). Criterio reabertura: real-world onde
   Pacote 1 + ADR-0008 + ADR-0010 nao bastem. Atual: ADR-0010 acabou de
   aumentar cobertura — criterio MENOS satisfeito.
7. **Track 2 L01-L05** — estudos de camada algoritmo (token-level,
   slot detection, markers tipados, tree-balance, pre-filter).

### Aberto/pendente apos sessoes 2026-05-30..06-02

- **T-SHAPER-CODE-HARDENING** (P2) — hardening shaper p/ >100k linhas
  (A1 filter-before-load destrava escala; A3/A4/A6). Nao bloqueia <=100k.
- **T-DATA-3-EDGE-QUALITY-FIXTURES** (deferred) — plano de dados de borda;
  bloqueado por T-RECOVER-SCHEMA-MULTI-TABLE (gadget de qualidade nao existe).
- **Roadmap v2.0** (ADR-0018) — format changes p/ naturezas raras reais
  (low-card padding, fallback identity); requer mudanca de formato.
- **Datasets gaps** (project-dataset-coverage-map) — free-text longo real,
  IP/UUID, monetary-string, >1M linhas, geo lat/lon.
- **CNPJ gate forte** — nature CNPJ e' confirmada-empirica com 1 fonte real;
  N>=5 fontes diferentes p/ confianca Alta (so' se quiser fortalecer claim).
- **Spin-off llm-benchmark/** — extrair p/ repo separado via git filter-repo
  quando a fronteira estabilizar (futuro, so' se owner quiser).
- **Fases parciais T-CODE** — ENCODER-MANAGER (1c/2-4), SCHEMA-BUILDER
  (Fase 3 naturezas), LAYERED-PIPELINE (Fase 2 online adaptive),
  OUTPUT-SINKS/PLAN-CONTRACT (bloqueados).

---

## Discipline de manutencao

Este arquivo deve ser **atualizado**:
- Ao fechar sub-experimento (status table)
- Ao tomar decisao estrutural (estrutura de pastas, ticket aberto/fechado)
- Ao mudar foco de natureza (T01 -> T02 etc.)

Se editar, lembrar: **status absoluto, nao incremental**. Substituir
o que mudou, manter o resto coerente.
