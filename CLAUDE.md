# TCF — Project Guide for Claude Code

> **Project-scope memory** (versionado em git). Carregado automaticamente
> a cada sessao. Complementa `~/.claude/.../memory/MEMORY.md` (user
> scope). User memoria tem preferencias pessoais; este aqui e' o que
> e' COMUM ao time.

## Projeto em 1 paragrafo

**TCF** (Tabular Compact Format) v0.6 — compressao de strings tabulares
com pipeline canonical delta-aware (M10 baseline, ADR-0011):
- **Pre-pass**: `analyze_column` (features) + `detect_cadence` (regras
  1+2, ADR-0008) + `detect_min_len` (heur v3 + gating n>=100, ADR-0010)
- **OBAT** (Online Bidirectional Affix Tokenizer) em `src/tcf/core/` +
  `src/tcf/obat_shape.py` (shape-preserve hint)
- **HCC** (Hierarchical Compositional Coding M8.A + seq-RLE) em
  `src/tcf/composicional/`

API: `from tcf import encode, decode`. Estado: pipeline canonical M10
validado em D1-D9 (baseline 1523B, vs M9 antigo 1615B — **pinado em
`tests/test_core_rt.py` + `test_regression_v1_baseline.py`**), 20 sint
(RT 20/20), Adult+TPC-H 57 cols (RT 57/57). Multi-column basico em EXP-011.

> **Ganhos real-world** (citar a fonte, nao o numero solto — §5 fonte unica):
> dois numeros distintos, ambos vs M9 puro (1,008,003B), nao conflitam:
> - **9.87% weighted** = H-DA-11 isolado (auto-min-len). Fonte: ADR-0010.
> - **11.73% weighted** = Pacote 1 completo (pipeline delta-aware). Fonte: ADR-0011.
> Bytes absolutos do gate real-world (89616B total) pinados em
> `tests/test_real_world_snapshots.py` — a prosa aponta, o teste mede.

## ONDE ESTAO AS COISAS — consulte ANTES de propor criar/baixar

### Codigo
- `src/tcf/` — **canonical (M10)**. NAO MODIFICAR sem aprovacao explicita.
  - `core/online.py` — OBAT canonical
  - `obat_shape.py` — OBAT shape-preserve hint (ADR-0011)
  - `composicional/syntax.py` — HCC M8.A
  - `composicional/hcc_seqrle.py` — HCC + seq-RLE near-identical (ADR-0011)
  - `auto_cadence.py` — detect_cadence (ADR-0008/0011)
  - `auto_min_len.py` — detect_min_len (ADR-0010, H-DA-11)
  - `column_features.py` — ColumnFeatures + analyze_column (H-DA-11c)
  - `encoder.py`, `decoder.py` — API publica (pipeline delta-aware)
  - `_core/detect.pyx` — acelerador Cython OPCIONAL de `_detect_compositions`
    (ADR-0020). Fallback pure-Python silencioso em `composicional/syntax.py`
    (byte-identico). Build best-effort via `hatch_build.py`; `.pyd/.c/build`
    sao gerados (gitignored). `_core/` faz parte de src/tcf (NAO MODIFICAR
    sem aprovacao). Manter `.pyx` e fallback byte-equivalentes.
- `scripts/` — ferramentas de suporte (NAO faz parte do TCF-CORE)
  - `dataset_reader.py` — **le datasets canonicos do hub SQLite**
  - `shaper/` — **sampler multidimensional** (volume, schema, join,
    order, stratify, fk_preserving)
  - `_paths.py` — resolve storage via `config/storage.json`
  - `setup_*.py` — setup canonical datasets (adult, tpch, ibge-municipios,
    br-identidades, receita-cnpj, online-retail, beijing-pm25, wine-quality)
  - `csv_to_sqlite.py`, `derive_formats.py`, `quality_report.py`
  - `benchmark_*.py` — benchmarks de FORMATO/compressao. **EXCECAO**: os 3
    `benchmark_{llm_accuracy,progressive_diagnostic,stats_ablation}.py` sao
    benchmark LLM v0.5 (acessorio) — marcados pra mover a `llm-benchmark/`
    (ver REORG abaixo). `benchmark_llm_accuracy.py` esta' QUEBRADO contra v0.6
    (importa nomes de old/tcf) — deixado sem conserto, arquivado-morto (Fase 2).
- `experiments/lab/dirty/` — labs exploratorios v0.6 (sub-exps numerados)
- `experiments/lab/clean/EXP-NNN-*/` — prototypes consolidados v0.6
- `experiments/eval/`, `experiments/results/`, `experiments/scratch/` —
  **benchmark LLM v0.5 (ACESSORIO, NAO TCF-core)**. M-series runners +
  manifests + CommercialClient. Marcado pra consolidar em `llm-benchmark/`
  (reorg em andamento; ver REORG abaixo). Entry point `__main__.py` foi
  removido na Fase 2 (estava quebrado); usar os run_*.py individuais.

### Dados
- `datasets/synthetic/` — CSVs pequenos no repo (D1-D17)
- `datasets/canonical/` — APENAS metadata.json + README. Dados reais em Z:.
- **`Z:/tcf-data/`** — grandes arquivos (via `config/storage.json`)
  - `external/` — raw downloads (adult-census, tpch-sf001)
  - `interim/` — **SQLite hubs prontos**:
    - `Z:/tcf-data/interim/adult-census.db`
    - `Z:/tcf-data/interim/tpch-sf001.db`
  - `processed/` — derivacoes (csv, jsonl, etc.)
  - `archives/`, `benchmarks/`

### Docs
- `STATUS.md` — **ponto de entrada bibliografico**, sempre-atualizado
- `MAP.md` — wayfinding map de 1 pagina
- `docs/algorithms/` — specs canonicos (OBAT, HCC, TCF-format)
- `docs/adr/` — Architecture Decision Records numerados
- `docs/theory/` — fundamentos teoricos
- `docs/vocabulary.md` — vocabulario controlado
- `docs/findings/` — catalogo cientifico v0.5 LLM (F-Q01..Q38, **historico**).
  NAO e' slot generico de findings v0.6. **FICA em docs/** (decisao Fase 6,
  2026-06-02): research compendium acoplado as research-notes vizinhas; mover
  quebraria 13 cross-links. O harness foi pra llm-benchmark/, o catalogo fica.
  Findings v0.6 vao em `docs/theory/` ou ADR (nao aqui).
- `old/tcf/` — **motor v0.5 (niveis L0–L3), congelado-historico**. `src/tcf/`
  tem acoplamento ZERO com ele. Semantica revista em `old/tcf/LEVELS-REVIEW.md`.
  NAO modificar, NAO importar de `old.tcf` em `src/tcf`.
- `experiments/lab/dirty/notas/` — narrativa + diario + roadmap
  - `roadmap-hipoteses.md` — registry cross-lab de hipoteses
  - `diario/YYYY-MM-DD.md` — decisoes diarias
  - `checkpoints/` — **pontos de pausa explicitos**
  - `futuras-otimizacoes-formato.md` — ideias de formato futuras
  - `historia-dirty-lab.md` — narrativa M0-M14
  - `welding-plan.md`, `naming-compactacao-composicional.md`

## REORG em andamento (separacao de concerns, 2026-06-02)

O repo nasceu como DOIS projetos colados: TCF-core v0.6 (`src/tcf/`) + um
benchmark LLM v0.5 (acessorio). Owner pediu separacao. Plano brownfield de
8 fases (README.methodology.md §13.2; assessment aprovado por etapa).

**Fronteira-alvo**: o HARNESS LLM v0.5 vivo consolidou em **`llm-benchmark/`**
(top-level, in-repo; spin-off pra repo separado depois via `git filter-repo`).
Contem: `llm-benchmark/eval/` (runners + llm_eval/ + probes/) +
`llm-benchmark/scripts/` (3 benchmark_*). O CATALOGO de findings
(`docs/findings/` + `FINDINGS_SUMMARY.md`) **FICA em docs/** (research
compendium, ver Fase 6). `results/`/`scratch/` sao gitignored, ficam em
`experiments/`. `tests/fixtures/synthetic_domains.py` ficou em tests/.

**Estado (2026-06-13)**: Fases 0-7 FEITAS — **reorg concluida**. 0+3 (5a15538:
doc-fixes + LEVELS-REVIEW); 1 (c09889a: fronteira CLAUDE.md); 2 (6c08abe: deleta
__main__ quebrado, marca benchmark LLM morto); 4+5 fundidas (45f03ad: git mv
harness -> llm-benchmark/); 6 (0b66c5e: findings FICAM em docs/, so' rotulo
reforcado); 7 (bb02cff: enxuga README 332->184 linhas, separa core v0.6 de LLM
v0.5). Detalhe na memoria [`project-reorg-separation-of-concerns`](C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/project_reorg_separation_of_concerns.md).

**Invariantes da reorg**: (1) `src/tcf/` INTOCADO (acoplamento zero com
`old/`, verificado); (2) `git mv` sempre (preserva history); (3) **NAO**
mover `experiments/results/phase0/reversibility.json` (artefato de FORMATO
v0.6); (4) findings ficam em docs/ (mover quebraria 13 cross-links ../).

## ANTES DE AGIR — Checklist obrigatorio

### Antes de propor download / recriar infra / sintetizar dataset
1. `Glob scripts/**/*.py` — pode ja existir
2. `Glob datasets/**` — pode ja ter dataset
3. `Grep` por termos relacionados (dataset, reader, loader, fetch,
   download, sampler, shaper)
4. `Read STATUS.md` se nao leu recentemente
5. `Read MAP.md` pra layout geral
6. Checar `Z:/tcf-data/` via `Test-Path` ou `ls`

**Sintoma de falha**: propor "vou baixar X", "vou criar Y do zero"
sem ter feito as buscas acima. PARE imediatamente. Ver
[`feedback-discoverability-falha-EXP-012`](C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/feedback_discoverability_falha_EXP_012.md)
pra contexto do incidente que motivou este guia.

### Antes de modificar labs existentes
- Se marcado `closed`, `fechado`, `obsolete` ou `superseded` — **NAO MODIFICAR**
- Abrir novo sub-experimento ao inves

### Antes de criar novo doc
- Buscar doc similar (Glob, Grep) antes
- Decidir LOCAL apropriado:
  - Stable user-facing → `docs/{tutorials,how-to,reference,explanation}/`
  - Decisao arquitetural → `docs/adr/NNNN-*.md`
  - Lab work → `experiments/lab/{dirty,clean}/...`
  - Notas continuas → `experiments/lab/dirty/notas/`
- Adicionar a `MAP.md` se for ponto de entrada novo

### Antes de declarar `confirmada-empirica` (anti-incidente 2026-05-21)

Caso motivador: Pacote 2 (escape deduction) deu 15.7% em sinteticos
D11a-h mas 0.13-1.13% em real-world — fechado `CLOSED-INSUFFICIENT-GAIN`.
Padrao: sub-exp em dataset construido pra testar a hipotese tende a
nao generalizar.

Checklist (5 perguntas obrigatorias):
1. **Real-world testado?** Adult Census / TPC-H / lineitem (nao so' D1-D17)
2. **N >= 5 datasets** de fontes diferentes (sinteticos contam separado)
3. **Sintetico vs real** mostram ganho similar OU diferenca explicada?
4. **Datasets sinteticos** explicitam que foram "construidos pra testar"
   (vies declarado)?
5. **Bytes absolutos** relevantes (>= 5% real-world weighted), nao
   so' % em dataset pequeno?

Se algum **NAO** → marcar `confirmada-empirica` com ressalva ou
`A-revalidar`. Sub-exp em real-world antes de welding/ADR.

Ver [`revisao-conceitual-2026-05-21.md`](experiments/lab/dirty/notas/revisao-conceitual-2026-05-21.md)
pra classificacao A/B/C das hipoteses existentes.

**GATE byte-canonical real-world (2026-05-31, T-REGRESSION-REAL-WORLD)**:
mudanca que toca HCC `_detect_compositions` / pre-pass / qualquer prune
algoritmico **DEVE** passar `tests/test_real_world_snapshots.py` (colunas
free-text reais — retail Description/StockCode, lineitem l_comment — regime
`n_tam_est>=3`). O mini-suite D1-D9 + D17a sozinho NAO basta: candidato
#03 (prune-k-03) passou D1-D9 + D17a mas regrediu +0.59% em real-world.
Welding de prune so' apos os DOIS suites verdes.

## FILOSOFIA DE DESIGN (registrada 2026-05-27, reforco do owner)

TCF nao compete com compressores binarios (gzip, brotli, zstd) — esses
ocupam **areas cinzas** (denso, opaco, exige descompressao pra ler).
TCF ocupa **areas explicaveis**: textual, inspecionavel, com agrupamentos
visiveis enquanto comprimido.

**Pilares**:
1. **Texto + explicabilidade** enquanto comprimido. RLE `*N|linha` mostra
   N items sem descomprimir — **agrupamento natural**. Economiza memoria
   (nao precisa materializar pra iterar). Mesma logica vale pra ranges
   `A..B` e seq-RLE `*N+delta|template`.
2. **Speed-first dentro do espaco textual** — otimizacoes de algoritmo,
   pre-pass, indices (trigrama/Patricia), compilacao Cython sao todas
   valoradas. Mas o output observavel permanece textual.
3. **Binarizacao em camadas (V2-L em ADR-0018) e' INTERNA ao TCF**,
   integrada ao algoritmo. Inspiracao: Parquet faz row groups + column
   chunks + page headers em binario; csv/json tem decisoes proprias
   internas. TCF tem o direito a uma representacao binaria do MESMO
   conteudo logico (HCC body packed em bytes), preservando semantica
   (RLE continua mostrando grupos sem expandir). Header textual mantido
   pra inspecao + roteamento. NAO compete com gzip/brotli/zstd (esses
   sao compressao binaria generica; V2-L e' representacao binaria
   estruturada do TCF, ainda explicavel).
4. **Anti-pattern explicito**: buffer-over-buffer / cache-over-cache.
   Pipeline streaming (V2-J/V2-K em ADR-0018) prioriza latencia
   (time-to-first-byte) e zero-copy IO.

### Suposicao TCF: dados "felizes"

TCF supoe **dados sadios e bem-formados**. NAO e' responsabilidade do
algoritmo entrar no merito de "por que essa data esta 32 de fevereiro"
ou "por que esse CPF tem digito errado". Comprime o que receber, agnostic
de origem.

**EXCECAO**: testes que dao **quase de graca** (anomalias detectaveis
durante operacoes que ja' acontecem). Esses podem ficar internos:
- analyze_column ja' compute is_numeric via sample; se um valor falha
  parse num campo "numerico", podemos flag em SideOutputs
- length variance alto numa coluna "uniforme" pode ser flag de format
  inconsistente
- Princpio: **so' detecta, NUNCA arruma**. Surfaca via SideOutputs.

### SideOutputs como framework de efeito colateral

`src/tcf/side_outputs.py` ja' captura **efeito colateral do encode**:
column_features (n_rows, n_unicas, cardinality, is_numeric, sample),
cadence_info, obat_log, hcc_trace, seq_rle_runs, multi_info, per_col.

Esse mecanismo e' **ponte oficial** entre TCF e gadgets auxiliares:
gadgets podem consumir SideOutputs pra extrair stats/alertas SEM custo
adicional (TCF computa de qualquer jeito). Expansao futura (opt-in):
campos de qualidade (anomaly_flags, format_inconsistencies) — mantendo
filosofia "zero custo, so' o que ja' compute".

### Escopo: o que E' TCF vs o que NAO E'

- **E' TCF (core/integrado)**:
  - Pipeline canonical (CAMADAS 0-3): pre-pass, OBAT, HCC, multi-col
  - Naturezas opt-in (CPF/CNPJ/IP) — ADR-0015
  - PipelineConfig toggles
  - `build_schema` per-tabela em **`src/tcf/schema.py`** (Fase 1+2 welded).
    Isto E' CORE e FICA. NAO confundir com o gadget multi-tabela abaixo.
  - SideOutputs (framework efeito colateral)
  - Deteccao zero-cost de anomalias (sem arrumar) via SideOutputs
  - V2-A/B/C/D/J/K/L (roadmap v2.0, integrados ao formato)
- **NAO e' TCF (gadgets auxiliares EXTERNOS, paralelos)**:
  - Schema gadget multi-tabela (T-RECOVER-SCHEMA-MULTI-TABLE): analisa
    FK/relacionamentos/qualidade cross-table, **emite alertas, NUNCA arruma**.
    NAO existe ainda; vivera em `scripts/schema_gadget/` ou spin-off.
    **Diferente** do `src/tcf/schema.py` (core) — mesma palavra "schema",
    coisas distintas. CUIDADO: existem 4 `schema.py` no repo (src/tcf core;
    old/tcf v0.5; scripts/shaper/strategies; docs/archive/old_tokenizer) —
    NUNCA editar "todos os schema.py" por basename.
  - LLM gadget (T-RECOVER-LLM-SCHEMA-MODE): coleta schema/stats,
    formata em "LLM-binary" (token-otimizado, NAO human-friendly),
    gera SQL a partir de pergunta de negocio, executa, output vai pro
    TCF. **NAO toca TCF, NUNCA arruma dados**. Spin-off recomendado.
  - Phase 1 LLM benchmark (v0.5, em docs/findings/, historic acessorio)
  - Shaper/dataset_reader (tooling de dados em scripts/, nao algoritmo)

### Filosofia dos gadgets auxiliares

- **Pequenos e focados** — NAO sao platform plays
- **So' alertam, NUNCA arrumam** — output e' relatorio/sinal, dev/arquiteto
  decide o que fazer
- **Paralelos** — consomem SideOutputs em paralelo, sem bloquear TCF
- **TCF e' agnostico de origem** — gadgets podem alimentar TCF
  (preparacao limpa) ou consumir output do TCF (analise pos-compressao),
  mas sem dependencia bidirecional
- **Spin-off recomendado** quando crescer — evita bloat do pacote TCF

A ideia: **pequenos gadgets pra manter qualidade do TCF ao maximo**,
evitar lixo e borda, auxiliando quem lida com dados — sem assumir
responsabilidade de corrigir.

Ver [docs/theory/strategies/INDEX.md](docs/theory/strategies/INDEX.md)
pro mapa segmentado de estrategias (preparacao pra otimizacao/binarizacao
independente por camada).

## CONVENCOES

### Naming
- Labs dirty: `YYYY-MM-DD-name/`
- Labs clean: `EXP-NNN-name/`
- Sub-exps: `NN-description/` (numerados dentro do lab)
- ADRs: `NNNN-imperative-phrase.md`
- Memorias user: `<type>_<topic>.md` (project_, feedback_, reference_, user_)
- Datasets: `D<num><suffix>-<description>.csv`

### Formato TCF
- Magic: `#TCF.<minor>` (v0.6 = `#TCF.6`). Major 0 omite "0".
- Multi-column flag: `M` no shebang. Single-col: sem flag.
- Multi-col meta: `# <size1>=<name1>,<size2>=<name2>,...`
- LF only, UTF-8

### Status markers (hipoteses)
- `aberta`, `em-exp`, `confirmada-empirica`, `confirmada-conceitual`
- `refutada`, `refutada-parcial`, `refutada-real-world`
- `absorvida`, `subsumida`, `adiada`, `welded`
- Add `[VERIFICAR: YYYY-MM-DD]` em claims mutaveis
- Add `confianca: Alta|Media|Baixa|A-revalidar` em hipoteses
  confirmada-empirica (introduzido 2026-05-21)
- Tickets podem usar `closed-insufficient-gain`, `closed-adiado`,
  `closed-parcial` no frontmatter YAML
  (ver `tickets/README.md` convencao 2026-05-21)

### Forca do artefato — dispositivo vs probatorio (§3-bis do Strata)
Marcar QUE ATO um artefato executa (ortogonal ao status/confianca). Um
leitor — humano ou agente — que ingere o corpus sem isso le diretiva,
hipotese e registro no mesmo plano e erra. Mapeamento canonico no TCF:
- **dispositivo** (CONSTITUI o que diz; e' a fonte; desfazer = novo ato):
  ADR `accepted`/`welded`, `src/tcf/` (codigo canonical), formato `#TCF.6`,
  decisao de owner. NAO se "revalida na fonte" — ELE e' a fonte.
- **probatorio** (REGISTRA fato verdadeiro alhures; revalida na fonte):
  resultado de experimento, hipotese, metrica medida, dataset (aponta pro
  dado real em Z:), ticket de teste. Carrega proveniencia + confianca.
INDEX.md (`scripts/index.py`) agrupa por `type` do frontmatter — usar
`type: decision|experiment|report|dataset|...` ja' sinaliza a forca. Em
prosa/ticket ambiguo, dizer explicitamente "[dispositivo]" / "[probatorio]".

### Tier de memoria
- **USER scope** (`~/.claude/.../memory/`): preferencias pessoais,
  feedback de processo (cross-projeto)
- **PROJECT scope** (este arquivo + `docs/adr/`): conhecimento
  partilhado via git
- **Diario** (`experiments/lab/dirty/notas/diario/`): cronologico
- **Checkpoints**: pausas explicitas pra retomada

## NUNCA

- Modificar `src/tcf/` sem aprovacao explicita
- Baixar dados externos quando `Z:/tcf-data/` infra existe
- Push pra GitHub sem solicitacao explicita
- Commit com `Co-Authored-By:`
- Usar superlativos ("incrivel", "muito melhor", "onde brilha",
  "campeao", "vencedor", "descoberta", "surpreendente")
- `git rebase -i`, `git add -i` (interativo nao suportado)
- `git reset --hard`, `git push --force` sem aprovacao
- Mexer em servicos rodando sem confirmacao
- Push pra main exige confirmacao explicita
- Skip hooks (`--no-verify`)

## Foco atual e checkpoint

- **Foco**: ver `STATUS.md`
- **Checkpoint mais recente**:
  `experiments/lab/dirty/notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md`
  (3 ADRs welded canonical 0014/0015/0016; 14 sub-exps dirty;
  benchmark consolidado TCF vence 5/6 datasets; pronto pra retomada)
- **Diario do dia ativo**: `experiments/lab/dirty/notas/diario/`

## Bibliografia bibliografica deste guia

Este sistema segue:
- **Diataxis** (Procida) — pra docs estaveis em `docs/`
- **ADR/MADR** (Nygard) — pra `docs/adr/`
- **Research Compendium** (Turing Way) — pra `experiments/`
- **FAIR4RS** — metadata em READMEs
- **Information Architecture** (Morville) — wayfinding (CLAUDE.md +
  MAP.md + cross-links)
- **Claude Code memory hierarchy** — user vs project scope
- **Threats to validity** (Wohlin 2012) — Internal/External/
  Construct/Conclusion. Aplicado em checklist "antes de declarar
  confirmada-empirica" acima.
- **Ecological validity** (Brunswik 1956) — separar datasets de
  design (realistico) de datasets de stress (artificial).

**Doc-mae cross-projeto** (sintese metodologica):
[`../README.methodology.md`](../README.methodology.md) — sintese
operacional dos pilares acima, com refs canonicos. Consulta sob
demanda via routing table do proprio doc.
