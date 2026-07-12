---
title: T-QA-8 — material comprobatório do #TCF.8/0.8.0 (controle → sintéticos → públicos) com telemetria, dicts e paralelismo
status: open
priority: P1
created: 2026-07-10
updated: 2026-07-12
blocked-by: []
related:
  - docs/adr/0032-tcf8-default-format.md
  - tickets/T-DIST-RELEASE-0.8.0.md
  - tickets/T-REL-08-CLOSEOUT.md
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
4. **Telemetria honesta e PORTÁVEL** (F0-3, owner): conceitos independentes de OS/hardware/
   linguagem, sondas isoladas por plataforma com fallback gracioso (campo ausente ≠ medição
   quebrada). Tempo = `perf_counter_ns`, warmup + n≥9 runs + mediana (+p95) — no Windows o
   `process_time` tem tick de 15.625ms, mais um motivo pro repeat ser parte do CONCEITO;
   memória = tracemalloc peak em RUN SEPARADA da de tempo (overhead) + `peak_rss` melhor-esforço
   por sonda; claims de paralelismo = wall-clock speedup + byte-identidade +
   `multi_info['parallel_workers']` (CPU/mem dos workers é INOBSERVÁVEL via stdlib em qualquer
   OS — não claimar). Registrar sempre: python/os/cpu, versão tcf, sondas ativas, flag
   `_detect_compositions_accelerated` (Cython on/off muda latência, não bytes).
5. **Outputs visíveis**: resultados em `experiments/results/evidencia-0.8/` (NÃO gitignored),
   JSONL com proveniência (dataset id, n_rows/n_cols, seed, ambiente) + artefatos `.tcf` de exemplo.
6. **Nada toca `src/tcf` sem aprovação explícita** — runner/telemetria/anonimizador vivem em
   `scripts/` ou lab. Bugs do §3 só se corrigem em F0, em lote, sob aprovação.
7. **Gates intocados**: D1-D9=1523B, D17a=300B, real-world=89616B são régua, não alvo — o material
   compara, não re-pina. Stress (D10/13/14) apresentado SEPARADO de design-realista.
8. gzip/brotli/zstd aparecem como sinal qualitativo de composição (TCF+br), nunca como gate.

## §3 — REGISTRO DE BUGS (achados no planejamento; arrumar em F0, NÃO agora)

> **PONTE 2026-07-12 (revisão de fechamento por ROI)**: o inventário passa a 14 bugs. Os lotes
> F0 fecharam 12/13 achados originais; a revisão pós-F2 encontrou o **BUG-14**, que quebra RT para
> entrada aceita pelo encoder e por isso é gate R0 antes de F3. BUG-12 e guardas de expansão sob
> blob corrompido continuam importantes, mas ficam no hardening 0.8.1 por decisão de prioridade do
> owner. Ordem dispositiva: [T-REL-08-CLOSEOUT](T-REL-08-CLOSEOUT.md).

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
> **LOTE 2 EXECUTADO (2026-07-10, aprovação + decisões do owner)**: BUG-03+04+05+06 fixados
> red→green (20 repros novos; o xfail histórico de `encode([])` virou contrato `raises`; suíte
> **566 passed**; pins intactos). Verificação adversarial (3 agentes): byte-neutralidade **189/189**
> (encode sha256 + decode cross-check); refutação de falso-positivo FALHOU em 46 combos íntegros
> (split recursivo, V2-B width 1-2, natures, bordas) — e o falso-positivo temido do órfão **fecha por
> construção** (HCC escapa dígito pós-literal: `['#TCF.9M x']` encoda `#TCF.\9M x`, RT ok). Eficácia
> MEDIDA (1474 cortes + 503 flips): truncamento calado-errado **29.2%→3.0%** (fora da zona órfã
> k≤6: 27.5%→**0.6%**; blobs 100%-sized: **0 buracos**); byte-flip loud 42.3%→56.9%; excedente
> sized 0/5→**5/5 loud**. Registros profundos das decisões do owner → **O-FMT-20..23** em
> `futuras-otimizacoes-formato.md` (schema-declare/parquet/tcfx; auto-stamp; #TCF1; completude
> streaming).

- [x] **BUG-03 [média]** — **FIXADO 2026-07-10** (decisão owner: fail-loud por enquanto): encode de
  0 linhas → ValueError nos DOIS ramos (colide com 1-linha-vazia por construção; nada de onde
  deduzir). **Profundo registrado (O-FMT-20)**: registro-'0' declara SCHEMA pro trilho de
  armazenamento append→parquet/tcfx — "visto mais no final".
- [x] **BUG-04 [média]** — **FIXADO 2026-07-10**: versão DEDUZIDA do run completo de dígitos do
  magic — `#TCF.9/.10/.85` → ValueError claro (antes `KeyError: 9` críptico; `.85` nem virava mais
  disc `'5'`); `.6/.7` mantêm a dica de git. **Profundo registrado (O-FMT-21/22)**: auto-stamp no
  encode em colisão de magic; visão owner = subversões são controle de dev, `#TCF1`(M) fecha tudo
  no 1.0, compat real só a partir dele.
- [x] **BUG-05 [média]** — **FIXADO 2026-07-10** (decisão owner: os 3 cheques agora, profundo
  registrado): decode deduz do que o header JÁ declara — (1) size vs bytes disponíveis, (2) fecho
  do blob (excedente), (3) cross-check n_rows (invariante nunca gravado, deduzido de graça). View:
  cheques 1+2 (lazy: sem n_rows, divergência DELIBERADA documentada). Limites conhecidos medidos:
  última-coluna-EOF absorvendo excedente row-consistente (9/1439 cortes) + zona pré-magic do órfão.
  **Profundo registrado (O-FMT-23)**: completude de transmissão/streaming — receptor sabe QUANTO
  esperar, fim-antes-do-aviso, timeout→truncamento; dedução incremental, não só no fim.
  Nota de comportamento: blob `min_header=False` + `\n` final de editor agora é loud (antes decodava
  ignorando; no DEFAULT o mesmo `\n` antes corrompia CALADO com linha fantasma — agora loud).
- [x] **BUG-06 [média]** — **FIXADO 2026-07-10** (sugestão aceita): validação de `\n`/`\r` FUNDIDA
  na passada do `_to_str` em `_encode_multi` — valida o que VAI SER USADO (pós-transformação),
  objetos com `__str__` contendo quebra não furam mais, e o caminho dict perdeu a passada separada
  do guard (1 passada em vez de 2). Ramo list mantém o guard até o lote do BUG-10.
- [x] **BUG-07 [média]** — **FIXADO 2026-07-10** (decisão owner: `body_bytes` é artefato VÁLIDO de
  custo compute/memória — MANTIDO com semântica de candidato documentada; contar NO processo, não no
  fim). Novos campos per-col `emitted_bytes`/`emitted_mode` + `multi_info['col_modes']`, capturados
  **no ponto do min()** — a contagem já existia pro size hex do header, zero passada extra/serialização.
  Nota (verificação): telemetria keyed pelo nome de ENTRADA (`''` na telemetria ↔ `'0'` no decode) —
  documentado no código; consumidor cruza via posição.
> **LOTE 3 EXECUTADO (2026-07-10, aprovação + decisões do owner)**: BUG-08(fold)+09+10+11b fixados
> red→green (16 repros novos; suíte **582 passed**; pins intactos). Verificação adversarial
> (2 agentes): refutação FALHOU em ~310 checks (100 nomes fuzz + 36 dirigidos: **zero** blob
> legítimo rejeitado pela whitelist; `_ESC_OK` cobre exatamente o que `_esc_name` emite);
> byte-neutralidade **103/103** + `parallel=1 ≡ serial` provado byte-a-byte + decode cross-check.
> Filosofia (owner): fronteiras = **ISOLAMENTO** — o código identifica os casos, comportamento
> re-decidível depois → [T-API-BOUNDARY-CONTRACTS](T-API-BOUNDARY-CONTRACTS.md) (pré-1.0);
> integridade do meta → [T-FMT-META-STRICT](T-FMT-META-STRICT.md).

- [x] **BUG-08 [baixa]** — **FIXADO 2026-07-10** (fold no strict; ticket de revisão mantido):
  `decode('#TCF.8M\n')` (meta vazio SEM body, não-emitível — verificado: 1-linha-vazia emite
  `#TCF.8M!\n`) → ValueError em decode E view (paridade); meta vazio COM body segue legítimo
  (1 col anônima tcf). Semântica definitiva do vazio → T-API-BOUNDARY-CONTRACTS + O-FMT-20.
- [x] **BUG-09 [baixa]** — **FIXADO 2026-07-10**: str/bytes como valor de coluna → TypeError que
  ensina (`envolva em [...]`). Sem auto-embrulho (duas leituras possíveis → declarar > deduzir).
- [x] **BUG-10 [baixa]** — **FIXADO 2026-07-10** (os 7 sub-itens): (a) list converte não-str via
  `_to_str` (= semântica dict, None→''; check de quebra fundido na mesma passada; guard antigo
  `_reject_linebreaks` removido — absorvido nos 2 ramos); (b) `layers` valida PipelineConfig;
  (c) `parallel` negativo/tipo → erro, **`parallel=1` → serial DEDUZIDO** (sem spawn; 1 worker ≡
  serial por construção, provado byte-a-byte); (d) `decode(não-str)` → TypeError; (e) `name=` sem
  nature (ou com dict) → ValueError; (f) `stamp`+dict segue ignorado (M já é o stamp — semântica
  correta, documentar em F6); (g) `nature=`+dict / `nature_per_col=`+list → ValueError cruzado.
  Nota da verificação: `parallel=-1`/`2.0` eram tolerados fora-de-contrato no HEAD — agora erro
  (intencional). Revisão profunda dos contratos (tipos anterior/próximo, diffs, specs) →
  T-API-BOUNDARY-CONTRACTS pré-1.0.
- [~] **BUG-11 [média]** — **(b) FIXADO 2026-07-10 (lote 3)**: whitelist de escape `_ESC_OK =
  ",=:\\!@%"` no `_unesc_name_strict` — escape de char não-estrutural (não-emitível) → ValueError;
  dangling integrado no mesmo scan. **(a) coberto em 2 camadas**: o caso comum do `\` inserido é
  pego pelo fecho/n_rows do lote 2 (medido); o residual geometricamente-consistente é
  indistinguível por construção → **checksum** no trilho tcfx/O-FMT-20. Vínculos e decisões
  restantes → [T-FMT-META-STRICT](T-FMT-META-STRICT.md).
- [ ] **BUG-12 [alta]** *(registrado 2026-07-10 pela verificação do lote 2 — PRÉ-existente, NÃO é
  regressão; NÃO fixado)* **DoS por não-terminação no decode HCC sob header corrompido**: 1 flip de
  hex-digit num size (`52=b`→`12=b`) desloca a fronteira das colunas e a fatia deslocada gira em
  `composicional/syntax.py:718` (`_parse_decl`, >1000s CPU medidos) DENTRO de `_decode_column` —
  antes do cross-check n_rows alcançar. Pior modo de falha (nem loud, nem errado: nunca retorna).
  Fix futuro toca o CORE HCC (guard de terminação/progresso no decode) → aprovação + gate
  byte-canônico completo + real-world obrigatórios.
- [~] **BUG-13 [média]** — **(b)(d)(e) FIXADOS 2026-07-10 (lote 4, "vamos fechar os A")**:
  (b) nature-id desconhecido → **ValueError** em decode (multi+single) E view — REVOGA o
  forward-compat de 2026-06-24 (2 testes re-pinados com rastreabilidade; pre-1.0 sem compat,
  ADR-0024); (d) **cross-check incremental na view**: `_col()` compara `len` com qualquer coluna
  já materializada (ints, custo zero, laziness intacta) — view não materializa mais dado errado
  calado em blob EOF-truncado; (e) invariantes internas dos slots: V2-B (`ntable` bound, stream
  múltiplo da width, **índice dentro da tabela** — o byte de editor virava índice NEGATIVO e
  wrapava a tabela em silêncio) + split (`ntmpl` bound) + `_dict_parts` da view (paridade L3/L4).
  8 repros novos; suíte **590 passed**; encode intocado (lote decode-only, pins por construção).
  **Restam (a)(c)**: flips nome/size geometricamente consistentes — só checksum (trilho
  tcfx/O-FMT-20, via [T-FMT-META-STRICT](T-FMT-META-STRICT.md)).
- [x] **BUG-14 [alta · domínio válido · gate R0 do `.8`]** *(FEITO 2026-07-12, lote A)* —
  o decoder dos dois níveis foi alinhado ao contrato LF-only (remoção de `splitlines()` em favor
  de split exclusivo por `\n` em `src/tcf/composicional/syntax.py` e
  `src/tcf/composicional/hcc_seqrle.py`). Prova red→green adicionada em
  `tests/test_core_rt.py` com 10 casos parametrizados (single+multi para `\v`, `\f`, NEL,
  `U+2028`, `U+2029`). Execução: red inicial `5 failed, 5 passed`; pós-fix `10 passed`; gates
  `tests/test_core_rt.py` + `tests/test_regression_v1_baseline.py` +
  `tests/test_real_world_snapshots.py` = `104 passed`.
- [ ] **BUG-15 [alta · domínio válido · NÃO fixado]** *(achado 2026-07-12 pelo RT counter-proof do
  lab `2026-07-12-1917-spec-camadas-v1`)* — **valor literal começando com `^` (marcador de ref do
  HCC) quebra o RT** em modo **tcf E dict** (raw sobrevive): `decode(encode(["^abc"]*30+["y"]*30))`
  → `ValueError: invalid literal for int()`. O HCC escapa dígito-líder (pra não ler literal como
  ref number) mas NÃO escapa `^`-líder. **Domínio válido**: qualquer coluna de texto com valores
  começando com `^` (regex, markup, math). **Relevância pros specs**: o alfabeto BASE94 da nature
  INCLUI `^` — a `nature-delta`/`field-split` (T-SPEC-DEEPDIVE §4-bis/ter) produz base-94 que pode
  começar com `^` e venceria por dict → o CEILING depende deste fix. **Fix candidato**: estender o
  escape-de-líder do HCC (o mesmo mecanismo do dígito) ao `^`; red→green + gate completo (CORE).
  Descoberto porque o lab EXIGIU RT end-to-end — o número anterior (sem RT) escondia o defeito (§RT).

### Doc-drift 0.7→0.8 (bloqueia o "documento bem feito pro pip" — corrigir em F6 com números medidos)

- [ ] **DOC-01 [alta]** `README.md` (embarcado como long-description da wheel!): badges 0.7.1/#TCF.7;
  exemplo-propaganda mostra `#TCF.7 M` decimal 244B — real 0.8: `#TCF.8M!2c=nome,...` hex **242B**
  (medido); "legacy #TCF.6 still read" (CORTADO); knob "forces legacy #TCF.6" (impossível);
  nature 27B → **39B** (header self-describing +12B que não existia); nega o marker self-describing
  que a 0.8 ENTREGA ("target 0.8" — já shipou); D17a 303/322 → **300**; "379 passed" → 530;
  seção "Format 0.7 (default)" inteira; view apontando pro gadget `scripts/tcf_lazy/` (hoje core).
- [x] **DOC-02 [média]** — **FEITO 2026-07-10** (lote 4 + lotes anteriores): docstrings de `src/tcf`
  corrigidas — `__init__.py` (formato #TCF.8 default, dispatch real, D17a 300B com eras no git);
  `decoder.py` (lote 2); `encoder.py` (Args completos: parallel semântica nova, nature
  self-describing, name/stamp/drop_names documentados; Raises real — nomes com separador são
  ACEITOS/escapados); `multi/core.py` (módulo: contratos de fronteira pós-M2/F0; `_encode_multi`:
  fallback/min_header sem promessa de #TCF.6); `dict_v2b.py` (meta #TCF.8M hex; data do weld
  07-02); `view.py` (lê SÓ #TCF.8M; parser único); `natures/__init__.py` (exemplo self-describing,
  decode sem spec); vars mortas `is_v8` removidas (lote 1); `tests/test_tcf_lazy.py`. **Nota**: tudo
  que depende de NÚMERO MEDIDO (README/exemplo/curvas) segue no F6/DOC-01.
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
  **LOTES 1-4 EXECUTADOS 2026-07-10** (BUG-01..11b + 13b/d/e + DOC-02; decisões de design do
  owner, ver §3; byte-neutro 122+189+103 casos; eficácia medida 1474 cortes). **Resta**: só
  **BUG-12** entre os achados originais (hang HCC sob blob corrompido) e os residuais-de-checksum
  13a/c (trilho tcfx, T-FMT-META-STRICT). O BUG-14 foi descoberto depois do F2 e entra no gate
  R0 separado abaixo, não reabre historicamente os lotes F0.
- [x] **F0-2** Suíte completa + gates pós-lotes: **590 passed** (530 + 60 repros F0), D1-D9=1523B /
  D17a=300B / real-world=89616B intactos (byte-neutralidade provada em 414 casos fora dos pins;
  lote 4 é decode-only+docstrings — encode intocado por construção).
- [x] **F0-3** Dependência de medição: **stdlib-only E PORTÁVEL** (owner 2026-07-10): a telemetria
  é feita de **CONCEITOS independentes de OS/hardware/linguagem** — fáceis de identificar e de
  transportar (ex.: Rust) — e, ficando em Python, tem que rodar **em qualquer lugar que o Python
  rode** (nada engessado). Arquitetura do runner (F1):
  - **Camada de conceitos** (portável, é a interface): `wall_time_ns`, `cpu_time_ns`,
    `peak_heap_bytes`, `peak_rss_bytes`, `bytes_in/out`, `rt_ok`, `env_fingerprint` — nomes/
    semântica que um port Rust implementa 1:1 (`Instant`, `jemalloc stats`, `/proc`/`GetProcessMemoryInfo`).
  - **Sondas** (adaptadores ISOLADOS e rotulados por plataforma): tempo/heap = stdlib pura
    (`perf_counter_ns`, `tracemalloc` — rodam em qualquer Python); `peak_rss` = melhor-esforço por
    plataforma (`resource.getrusage` em POSIX; psapi via ctypes SÓ no adaptador win32) com
    **fallback gracioso `None`** — medição NUNCA quebra por plataforma, o campo fica ausente e
    o relatório declara qual sonda rodou.
  - Workers do ProcessPool: inobserváveis via stdlib em QUALQUER OS → claims de paralelismo =
    wall-clock + byte-identidade + `parallel_workers` (conceito portável). psutil só como
    `[bench]` opcional se o F3 provar necessidade (go do owner).
- [ ] **F0-3** Owner decide: psutil como optional-dependency de bench (`[bench]`) ou stdlib-only
  (recomendação: stdlib-only nesta rodada; psutil só se F3 mostrar necessidade).
- [ ] **F0-4** Higiene mecânica sem-risco: rotular `benchmark_compression.py` como quebrado-v0.5
  (comentário topo), decidir destino do `run.log` untracked (add ou ignore).

### F1 — Harness de telemetria (fora de src/tcf; é a régua de TODAS as fases seguintes)

> **F1 FEITO 2026-07-11/12 (T-REL-08 Passo 2a)**: `scripts/bench_evidencia.py` (runner) +
> `scripts/bench_evidencia_probes.py` (conceitos portáveis F0-3: sondas isoladas por plataforma,
> fallback gracioso — sonda RSS ativa nesta máquina: `k32-getprocessmemoryinfo`). 10 testes-guarda
> em `tests/test_bench_evidencia.py`; suíte **600 passed**. Verificação adversarial (2 agentes,
> passa-com-ressalvas → ressalvas FECHADAS): isolamento OS-specific confinado às sondas (grep
> limpo), fallback sem sonda = campo AUSENTE (não crash), registro JSON-portável; protocolo
> auditado POR EXECUÇÃO — RT-gate real (decode adulterado → registro sem números), mediana/p95
> conferidos contra statistics, timing NÃO roda sob tracemalloc (5.3× de overhead evitado,
> medido), validate_pins pega inflação de +1B. **Achado fechado**: idempotência sozinha aceitava
> decode-constante → RT de transformação agora = **conteúdo-sob-transformação (multiset de
> linhas / valores posicionais) + idempotência 2ª geração** (teste pinado). Notas de honestidade
> gravadas: heap=Python-only (cross-linguagem usa RSS); Solaris ru_maxrss em páginas → sonda
> se declara indisponível.

- [x] **F1-1** runner: CSV single/multi (mesma carga da régua), kwargs parametrizáveis, JSONL com
  bytes/RT/rt_mode/determinismo/timing(mediana+p95, n≥9+warmup)/memória(runs separadas)/side/env.
  (Hub via DatasetReader entra no F4, quando os públicos rodarem.)
- [x] **F1-2** `serialize_side` externo (BUG-07 já welded: usa emitted_bytes/col_modes direto;
  traces opt-in).
- [x] **F1-3** `experiments/results/evidencia-0.8/<fase>/<dataset>.jsonl` + `.tcf` via
  `--save-blob` + README com schema `evidencia-0.8/v1`; exceção no .gitignore (outputs visíveis,
  `phase0/reversibility.json` intocado).
- [x] **F1-4** `--validate-pins`: D1-D9=**1523** · D17a=**300** · real-world=**89616** — exatos;
  também é teste da suíte (roda em todo pytest).

### F2 — Controle minúsculo (o owner começa AQUI: single-col, com/sem header, readers, README)

> **F2 FEITO 2026-07-12 (T-REL-08 P2b)**: driver reprodutível `scripts/bench_evidencia_f2.py` →
> **29 casos, RT 29/29**, material em `experiments/results/evidencia-0.8/f2/` (JSONL + 13 blobs
> `.tcf` inspecionáveis + `RESULT.md` GERADO). Régua re-validada antes da rodada. Leituras-chave
> (medidas): custo de header no MESMO dado = órfão **0B** → stamp **+7B** → M-1col **+13B**;
> README default **242B** (era 244 no 0.7 — número pro F6); drop_names 215B; `parallel=2`
> byte-idêntico mas mediana 423ms vs 2ms serial (spawn por chamada — dado pro T-CODE-PARALLEL-BUDGET);
> view toca **14.5%** do corpo num group_count; **boundary do cap V2-B**: K=8192→dict 98005B
> (5.0s) vs K=8193→tcf 113296B (2.7s) = **13.5% de bytes deixados na mesa acima do cap** por
> ~metade do compute (a caracterização que faltava pro V2B-DESCAPAR-B/C do .9). **ACHADO (o gate
> §2.3 pegou)**: os placeholders do README (dígitos repetidos) são **mod-11-VÁLIDOS** — o spec
> COMPRIME (apply_rate 1.0); a "invalidade" deles é convenção de cadastro → nota obrigatória no
> F6/README; fallback-path publicável agora usa a ANONIMIZAÇÃO da regra do owner ((dv+1)%10).

- [x] **F2-1** órfão (emails 32B, D1 118B = régua); view() não cobre órfão — na matriz.
- [x] **F2-2** 3 formas de header medidas no mesmo dado (0/+7/+13B; spec medido em e5-e7).
- [x] **F2-3** matriz decode×view: 8 formas, paridade "igual" em todas as M; órfão/stamp/spec =
  fail-loud por design; seletividade L3 demonstrada (14.5%).
- [x] **F2-4** README re-medido: default **242B** + 5 variantes (tabela pronta pro F6).
- [x] **F2-5** escaping/hex-borda(`f`/`10`/3-dígitos)/fail-loud paramétrico (6 blobs, todos
  loud)/multi-1col/anônima-última/só-vazias.
- [x] **F2-6** 1 blob por mecanismo: V2-B w1+w2, split `%`, HCC implícito, natures cpf/cnpj/ip
  (válidos EFÊMEROS apply_rate==1.0, sem blob salvo; misto 0.5; anonimizado 0.0 publicado).
- [x] **F2-7** boundary 8192/8193 medido (acima).

### F3 — Sintéticos maiores (escala controlada)

> **Gate R0 cumprido (2026-07-12, lote A)**: BUG-14 fechado red→green com suíte/pinos já
> executados no lote técnico. F3 está liberado; BUG-12/corrupção segue em 0.8.1.

> **Update 2026-07-12 (decisão de escopo do closeout `.8`)**: execução massiva foi interrompida
> e consolidada como **amostra**. Foi gerado
> `experiments/results/evidencia-0.8/f3/RESULT.md` com cobertura parcial explícita: F3-1 = 31/31,
> F3-2 = 10/10, F3-3 = 9 casos (faltaram 7), F3-4 = 0. Registro formal: não-população total nesta
> etapa; retomada completa fica para janela dedicada, sem bloquear o fechamento do núcleo `#TCF.8`.

- [x] **F3-1** Suite D1-D17 completa (31 CSVs) no runner — tabela única; stress (D10/13/14)
  SEPARADO de design-realista na apresentação.
- [x] **F3-2** Curva de escala com `tests/fixtures/synthetic_domains.py` parametrizado:
  n ∈ {20, 100, 1k, 10k, 100k} single e multi (fecha o buraco 20→2000 que não existia);
  bytes/linha, tempo/linha, memória vs n — onde o ganho TCF "liga" (README hoje afirma isso sem curva).
- [~] **F3-3** Paralelismo (a verificação pedida pelo owner):
  (a) byte-identidade parallel==serial nos REAL-WORLD snapshots (hoje só D17a);
  (b) speedup vs workers {serial,2,4,8} em multi-col grande (tpch/adult via hub), mediana n≥9;
  (c) MEDIR a porção serial pós-pool (fase de candidatos V2-A/B/split) — % Amdahl documentada;
  (d) combos sem cobertura: parallel × natures_per_col × sort_by × drop_names (byte-identidade);
  (e) registrar limitações honestas: decode serial, Cython sem nogil (3.13t re-ativa GIL), IPC spawn.
- [~] **F3-4** br-identidades (600k, DV-válido seed 20260601): natures em volume, apply_rate==1.0,
  medição efêmera (§2.3) — CPF/CNPJ/IP nos 3 codepaths (spec, fallback, misto).

### F4 — Públicos (bench)

> **F4-MÍNIMO FEITO 2026-07-12 (T-REL-08 R1/2d)**: driver `scripts/bench_evidencia_f4.py`,
> 9 casos nos hubs PRONTOS, **RT 9/9** + determinístico; material em
> `experiments/results/evidencia-0.8/f4-minimo/` (RESULT.md gerado). Amostras determinísticas
> "primeiros 5000" (população total = janela dedicada pós-release, decisão ROI). Δ vs CSV medido:
> adult **81.1%**, ibge **68.5%**, receita-real **62.4%**, lineitem-free-text **50.2%**,
> br-empresas+cnpj **55.3%**. Sinal zlib9 sempre menor no TCF (brotli indisponível no venv → sonda
> graciosa registrou ausência). **ACHADO FORTE (repro)**: a **nature CNPJ PIORA em dado REAL** —
> receita 100121B → 107460B (+7339B) COM `:cnpj`: a coluna cai de `split` (32665B) pra `raw`
> (39999B), porque o corpo base-94 da nature DESTRÓI a estrutura (matriz/filial, prefixos
> compartilhados) que o split/dict já explorava. No SINTÉTICO (br-empresas) a mesma nature AJUDA
> (55.3%). É o gap sintético-vs-real (anti-incidente 2026-05-21) com medição — **reforça a Opção A
> do [T-SPEC-STATUS-08](T-SPEC-STATUS-08.md)** e é caveat obrigatório pro F6 (nunca claimar nature
> CNPJ como ganho geral).

- [x] **F4-1** hubs prontos medidos (adult 48842→5k, tpch-sf001 lineitem 60175→5k + customer FULL
  1500, ibge FULL 5571, br-identidades pessoas/empresas 5k, receita-cnpj 200k→5k). tpch-sf01 600k =
  janela dedicada.
- [~] **F4-2** os 3 hubs faltantes (online-retail/beijing/wine) — **não no mínimo**; janela
  dedicada pós-release (os CSVs já viram no gate real-world via `datasets/samples/`).
- [x] **F4-3** matriz medida (bytes total/header/body + RT + timing indicativo + zlib9 sinal);
  brotli fica pra venv com brotli (sonda registra ausência, F0-3).
- [~] **F4-4** consolidação: RESULT.md por fase pronto; a tabela-mestra cross-fase + nota Wohlin
  entra no F6 (junto do README).

### F5 — Otimização extra (janela pós-evidência; SÓ o que a telemetria apontar)

- [ ] **F5-1** Triagem dos candidatos COM dado das fases F2-F4 (esperados: porção serial pós-pool;
  parallel=1/negativo; custo do obat_log/hcc_trace incondicional; V2-B width≥2). Cada candidato
  vira sub-exp/ticket próprio com gate T-REGRESSION-REAL-WORLD — NENHUM weld dentro deste ticket.

### F6 — Empacotar pro pip com documento bem feito

> **PLANO DETALHADO (owner pediu revisar como o F6 será feito, 2026-07-12)** — o F6 é
> doc-only + build (NÃO toca `src/tcf`); tudo com número MEDIDO do material (F2/F4), nada calculado.
> Ordem e arquivos:

- [ ] **F6-1a — README.md/README.pt-BR.md (o que embarca na wheel; DOC-01)**: substituir os números
  da era 0.7 pelos medidos: exemplo-propaganda **244B→242B** (F2 c1); badges `0.7.1`→`0.8.0` e
  `#TCF.7`→`#TCF.8`; header do exemplo `#TCF.7 M` decimal → `#TCF.8M` hex; remover "legacy #TCF.6
  still read" e o knob "forces #TCF.6" (cortado); D17a 303/322→**300**; "379 passed"→número atual;
  seção "Format 0.7" → "Format 0.8"; view aponta pro core (não `scripts/tcf_lazy/`). **Nature: o
  bloco muda de história** — o exemplo do README ainda diz que CPF "does not compress" e usa
  nature 27B→39B; substituir pela leitura HONESTA do F2/F4: nature CPF comprime em sintético MAS o
  **caveat obrigatório** = "nature CNPJ PIORA a tabela em dado real (F4: +7339B, split→raw); nenhum
  clássico é ganho de tabela garantido — o TCF já explora a estrutura inter-linha que a nature
  normalizaria". Tabela "Results" com os Δ vs CSV reais (adult 81%, ibge 68%, receita 62%).
- [ ] **F6-1b — docstrings src/tcf**: DOC-02 já FEITO (lote 4); só re-conferir que nada regrediu.
- [ ] **F6-1c — spec docs/algorithms/TCF-format.{pt-BR,en}.md (DOC-03)**: exemplo de header que
  contradiz a regra (última-sem-size mostrando size); corrigir com o output real.
- [ ] **F6-1d — pyproject.toml (DOC-04)**: adicionar `[project.urls]` (repo/changelog/homepage) +
  trove classifiers; conferir que o readme apontado é o corrigido.
- [ ] **F6-1e — satélites (DOC-05)**: rotular `benchmark_compression.py` quebrado-v0.5; errata
  T-DOC-3 (shebang→magic) de carona; `datasets/synthetic/README.md` (D1-D15→D17a).
- [ ] **F6-1f — CHANGELOG.md**: conferir a entrada 0.8.0 (já criada em M5) + anexar os fixes F0
  (lotes 1-4) e o C0 (dedup) como itens do 0.8.0.
- [ ] **F6-2** Re-build wheel + clean-room smoke (protocolo pré-verificado 2026-07-09, T-DIST) —
  agora com F0/C0 + docs F6-1; limpar `dist/` (wheels 0.7.1 stale) antes.
- [ ] **F6-3** Publicação = T-DIST C3 (tag v0.8.0 → Trusted Publishing), **go explícito do owner**.
  Avaliar 0.8.0 vs 0.8.1 no CHANGELOG se F0/C0 mudaram comportamento observável (mudaram: fail-loud
  novos — decidir se é minor-note ou espera 0.8.1).

**Pré-F6 (redirect owner 2026-07-12)**: a investigação de specs (R1.5 do T-REL-08) roda ANTES — o
F6 herda dela o caveat definitivo da nature e qualquer decisão de spec pré-1.0. Ver
[T-SPEC-STATUS-08](T-SPEC-STATUS-08.md) (Opção A decidida) + o plano de specs em curso.

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
