---
title: T-QA-8 — material comprobatório do #TCF.8/0.8.0 (controle → sintéticos → públicos) com telemetria, dicts e paralelismo
status: open
priority: P1
created: 2026-07-10
updated: 2026-07-10
blocked-by: []
related:
  - docs/adr/0032-tcf8-default-format.md
  - tickets/T-DIST-RELEASE-0.8.0.md
  - tickets/T-CODE-DESCAPAR-V2B.md
  - tickets/T-CODE-ENCODER-MANAGER.md
  - tests/test_real_world_snapshots.py
  - src/tcf/side_outputs.py
  - scripts/dataset_reader.py
---

# T-QA-8 — material comprobatório do #TCF.8/0.8.0

**[dispositivo→execução]** Diretriz do owner (2026-07-10): gerar o **material comprobatório**
de TUDO que foi feito no `.8` até o momento, com dados mais sólidos — todos os **dicts**,
verificação de **paralelismo**, **telemetria** interna (derivada dos dados via SideOutputs)
e a obtível "de graça" (Python/OS). Plano escalonado: **testes de controle bem pequenos**
(single-col com/sem header, variações de reader, o exemplo-propaganda do README) →
**sintéticos maiores** → **datasets públicos** pra bench. Depois disso: alguma **otimização
extra** (se a evidência apontar) e **empacotar pro pip com documento bem feito**.
Este ticket é a tarefa-grande com as microtarefas NA ORDEM — **nada de executar na louca**;
cada fase fecha antes da seguinte.

Fonte do levantamento: workflow de 10 agentes (6 inventário + 4 sweep adversarial),
2026-07-10, read-only, claims verificadas por leitura/execução (repros colados nos achados).

## §1 — O que o levantamento achou (estado real, resumo por eixo)

- **Dicts — são 3 welded + 2 de lab** (o material cobre os 3 welded; os de lab só se documenta):
  1. **V2-B dict per-coluna** (`@`, ADR-0025) — `src/tcf/multi/dict_v2b.py`; candidato do
     `min(tcf,raw,v2b,split)`; cap de compute 8192 (T-CODE-DESCAPAR-V2B forma A, 2026-07-02).
     Tem suite (TestV2BDict) mas **zero teste do boundary 8192 e do índice width≥2 (K>94)**.
  2. **Dict IMPLÍCITO do HCC/OBAT** (aliases inline + `^eid`) — sempre ativo, coberto pelos
     pins byte-canônicos. Dois sistemas de ref coexistem (`^N` decimal vs base-94 do V2-B) — H-REF-01.
  3. **SPEC_REGISTRY das natures** (`:cpf/:cnpj/:ip` self-describing, ADR-0027) — registry fechado.
  4. (lab, CLOSED) cross-dict/group-dict `&<G>` B1/B2 — closed-insufficient-generalization; nicho 0.9+.
  5. (lab, gated) família bN/spec_bin b/b2/b4/b8 — sem API pública, sem teste; weld gated por H-TYPE-03.
- **Paralelismo — JÁ EXISTE welded**: `encode(parallel=True|N)` via ProcessPoolExecutor com
  work-stealing e reordenação determinística (`src/tcf/multi/parallel.py`; T-CODE-ENCODER-MANAGER
  fases 1+1b, byte-identidade pinada em `tests/test_parallel.py`). Limites reais: fase de candidatos
  V2-A/B/split roda SERIAL no pai DEPOIS do pool (porção Amdahl não medida); decode 100% serial;
  Cython sem `nogil` (free-threaded 3.13t re-ativa o GIL); byte-identidade parallel==serial só
  testada em D17a (nunca nos snapshots real-world). Speedup histórico ~1.3x teto (IPC Windows spawn).
- **Telemetria**: SideOutputs = 13 campos, todos populados só no ENCODE (decode não tem side).
  `obat_log`/`hcc_trace`/`seq_rle_runs` são gerados INCONDICIONALMENTE (custo sempre pago — relevante
  pra claims de latência). "De graça" verificado no venv real (Py 3.13.13, Windows): perf_counter_ns,
  tracemalloc, getallocatedblocks OK; `resource` AUSENTE; `os.times()` inútil p/ filhos (children=0.0);
  `process_time` quantizado em **15.625ms** → payload pequeno EXIGE repeat+mediana (padrão n=9 do lab f1);
  peak-RSS stdlib-only via ctypes psapi (verificado disponível); **psutil NÃO é dep** (decisão de opt-in
  é do owner). Precedentes: `benchmark_compression.py` QUEBRADO (API v0.5, não rotulado);
  `benchmark_parallel.py` mede 1 run só. Não existe runner vivo bytes+tempo+memória.
- **Datasets**: 31 CSVs sintéticos (7-20 linhas; D1-D9 controle, D10/13/14 stress); hubs SQLite prontos:
  adult 48842, tpch-sf001 60175, tpch-sf01 600572, ibge 5571, br-identidades 600k, receita-cnpj 200k;
  **online-retail/beijing-pm25/wine-quality SEM hub** (só CSV em external/ — rodar csv_to_sqlite).
  Buraco de escala: nenhum sintético entre 20 e 2000 linhas (single) / 13 e 100 (multi);
  `tests/fixtures/synthetic_domains.py` é parametrizável em n e cobre o gap.
- **Modos/readers**: 12 kwargs de encode + PipelineConfig (3 toggles) + natures + view lazy.
  Só existem DOIS readers: `decode()` e `view()` (view cobre SÓ `#TCF.8M`; library-only, sem CLI).
  Matriz modo×teste tem furos: escaping×view sem teste, hex sem teste direto de parse, fail-loud só
  testado com 'H', drop_names+última-anônima sem teste, parallel×natures/sort_by sem byte-identidade.
- **Natures/CPF**: spec CPF valida o DV DE VERDADE (mod-11); DV inválido → status `check_invalid` →
  **fallback literal `_<valor>`** (repro: 3 valores DV-válido=33B/apply_rate=1.0 vs DV-inválido=72B/
  apply_rate=0.0; RT 100% nos dois). Consequência dura pra regra de anonimização (ver §2).
  Gerador DV-válido existe: `scripts/setup_br_identidades.py` (`_gen_cpf/_gen_cnpj`, seed 20260601).
  Anonimizador (re-invalidar DV) NÃO existe — criar fora de src/tcf.

## §2 — REGRAS do material (dispositivo; valem pra todas as fases)

1. **RT sempre**: nenhum byte reportado sem `decode(encode(x)) == x` validado na mesma run.
2. **Medir, não calcular**: todo número do material sai de execução; a prosa aponta pra artefato/teste.
3. **Regra CPF do owner (2026-07-10)** — medição vs publicação são artefatos DISTINTOS:
   - **Medição**: dados DV-**válidos** sintéticos, EFÊMEROS, regenerados por gerador+seed
     (`setup_br_identidades.py`, seed 20260601); assert `nature_apply.apply_rate == 1.0`
     (garante que o codepath base-94 do spec foi exercitado, não o fallback).
   - **Publicação**: NUNCA publicar CPF DV-válido — nem cru, nem dentro de `.tcf`
     (o header self-describing `:cpf` decoda sem spec out-of-band: publicar o blob = publicar os CPFs;
     verificado por execução). Material publicado = gerador+seed referenciado e/ou exemplos
     DV-**inválido** explicitamente ROTULADOS como fallback-path (o fallback deixa os dígitos
     verbatim `_<valor>` e NÃO reproduz os bytes da medição — dizer isso no material).
   - Anonimizador: re-invalidar trocando os 2 DVs por `(dv+1)%10` (não colide com o correto).
   - CPF reporta SEMPRE com ressalva "sintético é o teto" (PII → fonte real impossível);
     só CNPJ (receita-cnpj real) fecha confirmada-empirica (gate registrado).
4. **Telemetria honesta no Windows**: tempo = `perf_counter_ns`, warmup + n≥9 runs + mediana (+p95);
   memória = tracemalloc peak em RUN SEPARADA da de tempo (overhead) + peak-RSS via ctypes psapi;
   claims de paralelismo = wall-clock speedup + byte-identidade + `multi_info['parallel_workers']`
   (CPU/mem dos workers é INOBSERVÁVEL via stdlib — não claimar). Registrar sempre: python/os/cpu,
   versão tcf, flag `_detect_compositions_accelerated` (Cython on/off muda latência, não bytes).
5. **Outputs visíveis**: resultados em `experiments/results/evidencia-0.8/` (NÃO gitignored),
   JSONL com proveniência (dataset id, n_rows/n_cols, seed, ambiente) + artefatos `.tcf` de exemplo.
6. **Nada toca `src/tcf` sem aprovação explícita** — runner/telemetria/anonimizador vivem em
   `scripts/` ou lab. Bugs do §3 só se corrigem em F0, em lote, sob aprovação.
7. **Gates intocados**: D1-D9=1523B, D17a=300B, real-world=89616B são régua, não alvo — o material
   compara, não re-pina. Stress (D10/13/14) apresentado SEPARADO de design-realista.
8. gzip/brotli/zstd aparecem como sinal qualitativo de composição (TCF+br), nunca como gate.

## §3 — REGISTRO DE BUGS (achados no planejamento; arrumar em F0, NÃO agora)

Sweep adversarial 2026-07-10 (4 agentes; repros executados). Nenhum corrigido ainda — regra do
owner: "SE identificar algum bug sem querer, registre apenas pra arrumarmos depois".

### Corrupção/RT (candidatos a fix pré-medição — tocam src/tcf, exigem aprovação)

> **LOTE 1 EXECUTADO (2026-07-10, aprovação + decisões de design do owner)**: BUG-01+02+07 fixados
> red→green (16 repros pinados em `tests/test_f0_boundary_fixes.py`; suíte 546 passed; pins intactos).
> Verificação adversarial por workflow (3 agentes): **byte-neutralidade old-vs-new PROVADA em 122/122**
> casos (encode E decode, incl. side_outputs e parallel=2); refutador rodou 320 checks (313 pass) e
> achou 1 alta REAL — **gramática ambígua do último token** (`<size>` bare com `min_header=False` +
> anônima parseava como NOME, pré-F0) — fechada no EMIT (última anônima SEMPRE sem size) + 1 falso-
> positivo do guard de colisão com drop_names (fechado). Paridade view/decode confirmada até em
> natures e meta-vazio.

- [x] **BUG-01 [alta]** — **FIXADO 2026-07-10** (decisão owner: `''` = coluna SEM nome). Encode
  TRANSFORMA na fronteira: `''` vira ANONIMA no meta (decode dá o nome posicional; warning
  UserWarning; colisão `''`→`str(pos)` vs coluna existente = ValueError, exceto sob drop_names);
  o meta nunca emite escape-vazio. Decode agora MARCA corrupção (fail-loud): nome DECLARADO vazio
  (`<size>=`), backslash dangling (cauda ímpar), size hex inválido — ganchos do
  [T-TOOL-TCF-FIX-CORRUPTION](T-TOOL-TCF-FIX-CORRUPTION.md). `_esc_name` com guard `s[:1] and`.
- [x] **BUG-02 [alta]** — **FIXADO 2026-07-10** (decisão owner: mínimo de verificação, check
  implícito): parse do meta extraído pra **fonte única `_parse_meta`** em `multi/core.py`; decode E
  view consomem dela → **paridade por CONSTRUÇÃO**, zero verificação extra. Idiom `part[:1] in "!@%"`
  eliminado da view; vars mortas `is_v8` removidas nos 2 arquivos.
- [ ] **BUG-03 [média]** `encoder.py:189` + `multi/core.py:372-380` — **0 linhas viram 1 linha vazia**:
  `encode([]) == encode(['']) == '\n'`; `decode(encode({'a':[]})) == {'a':['']}`. Colisão por
  construção (formato não grava row-count). Single-col tem xfail documentado; multi não tem NADA.
  Decidir contrato: raise no encode de 0-rows OU xfail documentado nos dois ramos.
- [ ] **BUG-04 [média]** `decoder.py:90-104` — **`#TCF.9M`/versão futura NÃO é fail-loud**: cai no
  decode órfão e estoura `KeyError: 9` cru de dentro do HCC (por acidente). Contraste: `#TCF.8X` tem
  ValueError claro. Fere o espírito fail-loud do ADR-0032.
- [ ] **BUG-05 [média]** `multi/core.py:370-374` + `view.py:98` — **body truncado decoda sem erro**
  (colunas ragged/valores cortados): slicing não valida que os bytes do size hex existem; sem
  cross-check de n_rows entre colunas. Paridade mantida (decode e view aceitam a corrupção igual).
- [ ] **BUG-06 [média]** `encoder.py:91` — bypass do guard de `\n`: `_reject_linebreaks` roda ANTES
  do `_to_str`; objeto não-str cujo `__str__` contém `\n` corrompe calado (coluna ganha linhas).
- [x] **BUG-07 [média]** — **FIXADO 2026-07-10** (decisão owner: `body_bytes` é artefato VÁLIDO de
  custo compute/memória — MANTIDO com semântica de candidato documentada; contar NO processo, não no
  fim). Novos campos per-col `emitted_bytes`/`emitted_mode` + `multi_info['col_modes']`, capturados
  **no ponto do min()** — a contagem já existia pro size hex do header, zero passada extra/serialização.
  Nota (verificação): telemetria keyed pelo nome de ENTRADA (`''` na telemetria ↔ `'0'` no decode) —
  documentado no código; consumidor cruza via posição.
- [ ] **BUG-08 [baixa]** `multi/core.py:356-360` — `decode('#TCF.8M\n')` (meta vazio, não-emitível)
  fabrica `{'0': ['']}` em vez de fail-loud; view crasha (mesmo root do BUG-02).
- [ ] **BUG-09 [baixa]** `multi/core.py:156` — `encode({'a': 'xyz'})` trata str como sequência de
  chars (3 linhas de 1 char) sem erro — uso plausível, tabela errada calada.
- [ ] **BUG-10 [baixa]** fronteiras da API (lote): não-str em list crasha fundo (`analyze_column`,
  assimetria com dict que faz `_to_str`); `layers=` sem validação (AttributeError obscuro);
  `parallel=-2` liga pool de 1 worker (docstring promete N≥1); `parallel=1` paga spawn sem paralelismo;
  `decode(int)` AttributeError em vez de TypeError; `name=` ignorado calado sem nature (validação de
  `:` só roda com nature); `stamp=`/`nature=` ignorados calados pra dict; `nature_per_col` idem pra list.
- [ ] **BUG-11 [média]** *(registrado 2026-07-10 pela verificação adversarial do lote 1 — NÃO fixado)*
  leniência residual do unescape do meta: (a) um `\` INSERIDO antes de separador funde duas colunas
  caladas (`decode('#TCF.8M2=a\\,z\n...')` → 1 coluna `'a,z'`, dados da 2ª descartados); (b) escape
  de char NÃO-separador é aceito e ALIASA nomes (`'2=a\bc'` ≡ `'2=abc'`). O encoder nunca emite
  nenhum dos dois — candidatos a strict-mode/marcação (ganchos do T-TOOL-TCF-FIX-CORRUPTION). A
  verificação também CONFIRMOU o BUG-05 com repros (bytes sobrando descartados; size>body decoda errado).

### Doc-drift 0.7→0.8 (bloqueia o "documento bem feito pro pip" — corrigir em F6 com números medidos)

- [ ] **DOC-01 [alta]** `README.md` (embarcado como long-description da wheel!): badges 0.7.1/#TCF.7;
  exemplo-propaganda mostra `#TCF.7 M` decimal 244B — real 0.8: `#TCF.8M!2c=nome,...` hex **242B**
  (medido); "legacy #TCF.6 still read" (CORTADO); knob "forces legacy #TCF.6" (impossível);
  nature 27B → **39B** (header self-describing +12B que não existia); nega o marker self-describing
  que a 0.8 ENTREGA ("target 0.8" — já shipou); D17a 303/322 → **300**; "379 passed" → 530;
  seção "Format 0.7 (default)" inteira; view apontando pro gadget `scripts/tcf_lazy/` (hoje core).
- [ ] **DOC-02 [média]** docstrings de `src/tcf` (user-facing via help(), vão na wheel):
  `__init__.py:1-2,26,57` (0.7 default/.6 lido/D17a 303B); `decoder.py:5-8,72-74` (dispatch .6/.7 vivo);
  `encoder.py:146-149,169-170` (forçar #TCF.6/header legado `# `/ValueError de `,`/`=` — hoje escapa);
  `multi/core.py:27-30` (restrições INTERIM já resolvidas pelo escaping); `dict_v2b.py:5` (#TCF.7)
  e `:21` (data do cap-raise 07-01 vs weld 07-02); `view.py:3` (lê .7/.6 — só lê 8M);
  `natures/__init__.py:30-32` (exemplo manda passar nature no decode — redundante com self-describing);
  var morta `is_v8` (`core.py:322`, `view.py:70`); `tests/test_tcf_lazy.py:3`.
- [ ] **DOC-03 [média]** `docs/algorithms/TCF-format.pt-BR.md:94` — exemplo `@a=uf,1e=nome` mostra
  size na ÚLTIMA coluna contradizendo a própria regra (última sem size); equivalente real:
  `#TCF.8M@14=uf,!nome`. Conferir o .en.md no mesmo ponto.
- [ ] **DOC-04 [baixa]** `pyproject.toml` — wheel 0.8.0 sem `[project.urls]` e sem classifiers
  (página PyPI sem link pro repo/changelog); readme apontado é o stale do DOC-01.
- [ ] **DOC-05 [baixa]** satélites: `scripts/benchmark_compression.py` QUEBRADO (API v0.5) sem rótulo
  (CLAUDE.md só marca o llm_accuracy); `benchmark_parallel.py` 1 run sem mediana/warmup;
  `datasets/synthetic/README.md` título "D1-D15" e faltam D11f-m nas tabelas; `metadata.json` dos
  canônicos sem row_count; `tickets/README.md:64` row do T-FMT-NAME-ESCAPING diz OPEN mas o interim
  backslash foi WELDED (M2, `58f7dee`) — resta só o estudo CSV-quoting (re-rotular parcial);
  `experiments/lab/dirty/2026-07-08-2355-f3-bn-seletivo/run.log` untracked (sujeira de lab).

## §4 — FASES (microtarefas na ordem; cada fase fecha antes da seguinte)

### F0 — Gate de entrada: decisões do owner + lote de fixes (pré-medição)

- [~] **F0-1** Owner decide o lote de fix pré-medição (toca `src/tcf` → aprovação explícita).
  **LOTE 1 (BUG-01+02+07) EXECUTADO 2026-07-10** com as decisões de design do owner (ver §3) +
  verificação adversarial (byte-neutralidade 122/122). **Restam à decisão do owner**: BUG-03/04/05/06
  ("modo fail-loud", desejáveis pré-medição) e BUG-08/09/10/11 (podem esperar 0.8.1) — "retornamos
  pra resolver os outros aos poucos" (owner, 2026-07-10).
- [x] **F0-2** Suíte completa + gates pós-lote 1: **546 passed** (530 + 16 repros F0), D1-D9=1523B /
  D17a=300B / real-world=89616B intactos (byte-neutralidade também provada em corpus de 122 casos
  fora dos pins).
- [ ] **F0-3** Owner decide: psutil como optional-dependency de bench (`[bench]`) ou stdlib-only
  (recomendação: stdlib-only nesta rodada; psutil só se F3 mostrar necessidade).
- [ ] **F0-4** Higiene mecânica sem-risco: rotular `benchmark_compression.py` como quebrado-v0.5
  (comentário topo), decidir destino do `run.log` untracked (add ou ignore).

### F1 — Harness de telemetria (fora de src/tcf; é a régua de TODAS as fases seguintes)

- [ ] **F1-1** `scripts/bench_evidencia.py` (runner): recebe dataset (inline/CSV/hub via
  DatasetReader), roda encode/decode com kwargs parametrizáveis, e emite JSONL com:
  bytes (total/header/body; per-col via meta), RT bool (obrigatório), timing
  (mediana+p95 de n≥9 com warmup, encode E decode separados), memória (tracemalloc peak em run
  separada + peak-RSS psapi), SideOutputs serializado (multi_info completo: fallback/dict/split cols),
  ambiente (python/os/cpu/tcf-version/cython-flag), proveniência (dataset id, n_rows/n_cols, seed).
- [ ] **F1-2** Serializador de SideOutputs (externo, `to_dict` no runner — dataclass não tem;
  respeitar BUG-07: enquanto não corrigido, extrair bytes per-col do META, não do side).
- [ ] **F1-3** Formato do artefato: `experiments/results/evidencia-0.8/<fase>/<dataset>.jsonl` +
  `.tcf` de exemplo inspecionável + README da pasta com o schema dos campos.
- [ ] **F1-4** Validar o runner nos 3 pins (D1-D9, D17a, real-world snapshot) — os bytes do runner
  DEVEM bater com os testes (mesma régua); divergência = bug do runner, parar.

### F2 — Controle minúsculo (o owner começa AQUI: single-col, com/sem header, readers, README)

- [ ] **F2-1** Single-col órfão (default 0B de header): lista de 3-6 valores (o exemplo
  getting-started) + D1 — bytes/tempo/RT; registrar que `view()` NÃO cobre órfão (matriz de reader).
- [ ] **F2-2** Single-col "com header", as 3 formas: (a) dict de 1 coluna → `#TCF.8M`;
  (b) `stamp=True` → `#TCF.8\n`; (c) `nature=` → `#TCF.8 :cpf`. Medir o CUSTO de header de cada
  uma vs órfão no mesmo dado (é a resposta concreta a "com e sem headers").
- [ ] **F2-3** Variações de reader sobre os MESMOS blobs: `decode()` vs `view()` (columns/iteração/
  agregação) — paridade de conteúdo + tempo + bytes tocados; matriz reader × {órfão, M, M+escaping,
  M+drop_names, M+natures, M+sort_by, stamp, spec} com "não-suportado" explícito onde for o caso.
- [ ] **F2-4** README-propaganda (4 rows × 5 cols) re-medido sob 0.8: gravar output REAL
  (`#TCF.8M` hex, 242B), variantes fallback=False, min_header=False, drop_names=True, sort_by,
  parallel=2 — tabela pro F6 re-escrever o README com números medidos.
- [ ] **F2-5** Controles específicos do .8 que NÃO existem hoje (criar como strings inline no runner):
  nomes com separadores escapados (`a:b,c=d`, `\`, unicode); hex na borda (15/16 → `f`/`10`,
  size multi-dígito ≥256); discriminador fail-loud paramétrico (H, X, @, 9M...); multi de 1 coluna;
  drop_names com última anônima (após BUG-02 fixado); coluna só-vazias `['','','']`.
- [ ] **F2-6** Dicts em controle (1 blob-exemplo inspecionável POR mecanismo, com bytes+RT):
  V2-B (low-card K=3 width1; K=95..200 width2 — cobre o gap), split `%` com V2-B interno
  (a sinergia declarada nunca testada), dict implícito HCC (`^eid` + alias `~`), natures
  :cpf/:cnpj/:ip DV-válido efêmero (§2.3, apply_rate==1.0) + coluna MISTA válido/inválido.
- [ ] **F2-7** V2-B boundary do cap: K=8192 (candidato) vs K=8193 (skip) em coluna sintética —
  o weld de 07-02 nunca teve teste dedicado; medir também o custo de compute nos dois lados.

### F3 — Sintéticos maiores (escala controlada)

- [ ] **F3-1** Suite D1-D17 completa (31 CSVs) no runner — tabela única; stress (D10/13/14)
  SEPARADO de design-realista na apresentação.
- [ ] **F3-2** Curva de escala com `tests/fixtures/synthetic_domains.py` parametrizado:
  n ∈ {20, 100, 1k, 10k, 100k} single e multi (fecha o buraco 20→2000 que não existia);
  bytes/linha, tempo/linha, memória vs n — onde o ganho TCF "liga" (README hoje afirma isso sem curva).
- [ ] **F3-3** Paralelismo (a verificação pedida pelo owner):
  (a) byte-identidade parallel==serial nos REAL-WORLD snapshots (hoje só D17a);
  (b) speedup vs workers {serial,2,4,8} em multi-col grande (tpch/adult via hub), mediana n≥9;
  (c) MEDIR a porção serial pós-pool (fase de candidatos V2-A/B/split) — % Amdahl documentada;
  (d) combos sem cobertura: parallel × natures_per_col × sort_by × drop_names (byte-identidade);
  (e) registrar limitações honestas: decode serial, Cython sem nogil (3.13t re-ativa GIL), IPC spawn.
- [ ] **F3-4** br-identidades (600k, DV-válido seed 20260601): natures em volume, apply_rate==1.0,
  medição efêmera (§2.3) — CPF/CNPJ/IP nos 3 codepaths (spec, fallback, misto).

### F4 — Públicos (bench)

- [ ] **F4-1** Hubs prontos: adult (48842), tpch-sf001 (60175), tpch-sf01 lineitem (600572),
  ibge (5571), receita-cnpj (200k, CNPJ REAL não-PII — o dataset que fecha gate de nature).
- [ ] **F4-2** Criar os 3 hubs faltantes com infra existente (`scripts/csv_to_sqlite.py`):
  online-retail, beijing-pm25, wine-quality (NÃO é download novo — CSVs já em Z:/external/).
- [ ] **F4-3** Matriz de medição por dataset: raw CSV/JSON vs TCF 0.8 (bytes+tempo+mem+RT) +
  composição TCF+brotli como sinal (§2.8); degraus de volume via shaper (seed fixa, reproduzível).
- [ ] **F4-4** Consolidação: tabela-mestra do material (todas as fases), cross-check com os pins,
  e nota metodológica (Wohlin: ameaças a validade; sintético-construído-pra-testar declarado).

### F5 — Otimização extra (janela pós-evidência; SÓ o que a telemetria apontar)

- [ ] **F5-1** Triagem dos candidatos COM dado das fases F2-F4 (esperados: porção serial pós-pool;
  parallel=1/negativo; custo do obat_log/hcc_trace incondicional; V2-B width≥2). Cada candidato
  vira sub-exp/ticket próprio com gate T-REGRESSION-REAL-WORLD — NENHUM weld dentro deste ticket.

### F6 — Empacotar pro pip com documento bem feito

- [ ] **F6-1** Aplicar DOC-01..05 com os números MEDIDOS do material (README re-gravado do exemplo
  242B + curvas F3-2; docstrings; spec; pyproject urls/classifiers). O README embarca na wheel —
  é parte do pacote, não cosmético.
- [ ] **F6-2** Re-build wheel + clean-room smoke (repetir o protocolo pré-verificado de 2026-07-09,
  registrado em T-DIST-RELEASE-0.8.0) — agora com os fixes F0 e docs F6-1.
- [ ] **F6-3** Publicação = T-DIST-RELEASE-0.8.0 C3 (tag v0.8.0 → Trusted Publishing),
  **go explícito do owner**. Se F0 mudou comportamento observável, avaliar 0.8.0 vs 0.8.1 no CHANGELOG.

## §5 — Critérios de aceite

- [ ] Todo número do material rastreia a um artefato JSONL reproduzível (runner+seed) com RT validado.
- [ ] Os 3 dicts welded + natures têm blob-exemplo inspecionável e medição própria; os de lab
  documentados como research (sem claims de produto).
- [ ] Paralelismo verificado: byte-identidade em real-world + curva de speedup + % serial medida +
  limitações registradas.
- [ ] Telemetria em 2 famílias (SideOutputs + free) com as ressalvas Windows documentadas.
- [ ] Regra CPF cumprida: nenhum artefato publicado contém CPF DV-válido (nem em `.tcf`).
- [ ] Bugs do §3: todos ou fixados (F0, sob aprovação, red→green) ou explicitamente adiados com rótulo.
- [ ] README/docstrings/spec sem promessa que a 0.8.0 não entrega (F6-1) ANTES do go de publicação.
