---
title: T-REL-08-CLOSEOUT — ordem por ROI para fechar o núcleo 0.8
status: open
priority: P1
created: 2026-07-10
updated: 2026-07-12
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-DIST-RELEASE-0.8.0.md
  - experiments/lab/dirty/notas/checkpoints/2026-07-12-revisao-roi-fechamento-08.md
  - ROADMAP.md
  - STATUS.md
---

# T-REL-08-CLOSEOUT — fechamento do 0.8, na ordem

**[dispositivo→execução]** Materializa o levantamento de 2026-07-10 (pedido do owner: listar os
tickets abertos e a ordem de ataque com critérios — "fácil e sem risco primeiro, os de alto valor,
e os que ainda tem coisa pra implementar antes de ir pro .9"; e "mesmo a ordem de execução do que
verificamos gera tickets — rastreabilidade e memória, não pode ficar tudo só na conversa").
Este ticket é o GUIA da ordem; cada passo aponta o ticket/fase que o executa.

## Regra vigente de ROI (decisão do owner, 2026-07-12)

O objetivo corrente é **fechar o núcleo `#TCF.8` e publicar o pacote `0.8.0` antes de abrir
hardening amplo ou pesquisa de `.9`**. Bugs e bordas continuam registrados, mas não furam a fila
por simples severidade abstrata. Um item só preempta o caminho crítico do `.8` quando satisfaz ao
menos um destes critérios:

1. quebra `decode(encode(x)) == x` para uma entrada que o encoder público aceita;
2. impede construir, instalar ou usar o artefato `0.8.0` no ambiente declarado;
3. invalida a evidência ou faz a documentação embarcada prometer comportamento diferente do core.

Blob deliberadamente corrompido, orçamento defensivo de expansão, checksum, reparador e contratos
definitivos pré-1.0 permanecem importantes, porém **não preemptam** F3/F4/F6 salvo reclassificação
explícita neste ticket. Otimização F5 tem default **NO-ACTION**: só abre sub-experimento se a
telemetria de F3/F4 demonstrar blocker ou ganho de fechamento claro; ideias de ganho vão para `.9`.

### Fila única de retomada (ROI decrescente)

| ROI | atividade | saída que fecha | próximo estado |
|---|---|---|---|
| **R0 — integridade do núcleo válido** | BUG-14 fechado (red→green; decoder LF-only + testes parametrizados + gates canônicos) | domínio público aceito voltou a ser lossless | F3 |
| **R1 — evidência de fechamento** | F3 amostral + **F4-mínimo (FEITO 2026-07-12, 9/9 RT)** | prova reproduzível nos hubs prontos; população total = janela dedicada pós-release | R1.5 |
| **R1.5 — investigação de specs (REDIRECT owner 2026-07-12)** | investigar o que comprime alem do basico; revisar specs cadastrais, base segura e compilador | laboratorio versionado + matriz `.8`/`.9`; `DateSpec` ISO fica candidato condicional, demais familias aguardam dado real | R2 |
| **R2 — superfície publicável** | F5 somente se gated; F6 reconcilia README EN/PT, referência, metadata, wheel e smoke clean-room (+ **caveat nature-CNPJ-piora-em-real**) | pacote/documentação descrevem o mesmo `#TCF.8` | C3 |
| **R3 — ato de release** | C3: tag `v0.8.0` + Trusted Publishing, somente com go explícito do owner | `0.8.0` publicado e closeout fechado | abrir ciclo seguinte |

**Próxima ação concreta em nova sessão**: reler este bloco → **R2/F6** (README EN/PT, manual,
referência, metadata, wheel e smoke clean-room). R1.5 ficou registrado no laboratório cadastral e
na matriz `.8`/`.9`; `DateSpec` ISO é apenas candidato condicional. Specs do `.8` permanecem
CPF/CNPJ/IP ([T-SPEC-STATUS-08](T-SPEC-STATUS-08.md)). Checkpoint temporal:
[`2026-07-12-revisao-roi-fechamento-08.md`](../experiments/lab/dirty/notas/checkpoints/2026-07-12-revisao-roi-fechamento-08.md).

## Auditoria ROI 2026-07-12 — specs, execucao e integracoes

**[probatório -> ordem]** Revisao feita antes do F6, cruzando tickets ativos, codigo, testes e
artefatos F3/F4. O resultado separa o que pode fechar o `.8` do que e' pesquisa ou integracao
posterior; nao abre uma nova frente de execucao em massa.

| eixo | observado | decisao de fechamento |
|---|---|---|
| **Specs** | Core welded: `TemplatedCheckedSpec` (CPF/CNPJ) e `TemplatedPaddedSpec` (IP); laboratorio cadastral mediu DateSpec/CEP/telefone/RG/codigo fixo fora do core. Compilador DSL/registry existe em `scripts/`, mas nao e' registry publicavel do core. FLOOR compete pelo blob completo. | `.8`: CPF/CNPJ/IP continuam canonicos; `DateSpec` ISO so' entra com aprovacao propria, validacao de calendario e dois gates reais. CEP/CNH/RENAVAM/PIS/titulo, telefone, RG e `FixedAlphabetSpec` ficam `.9`. Specs customizados podem viajar com `:id` mediante spec out-of-band coincidente. |
| **Paralelismo** | `parallel=False|N` ja' e' byte-identico e RT-safe. F3-3 amostral mediu, em 20k Adult, speedup aproximado `1.21x/1.33x/1.34x` para 2/4/8 workers; Lineitem 20k mediu `1.41x` em 2 workers. Faltam Lineitem p4/p8 e cinco combos. | `.8`: documentar como evidencia amostral, sem prometer caracterizacao exaustiva; nao adicionar `TCF_MAX_WORKERS` sem nova medicao. Cap global e revisao da porcao serial vao para `T-CODE-PARALLEL-BUDGET` pos-release. |
| **Processamento, latencia e memoria** | JSONL F3 registra wall-clock, p95, `process_time`, `tracemalloc`, RSS best-effort, ambiente e acelerador Cython. `SideOutputs` paga trace de encode sempre; decode e' serial. Windows exige repeticao/mediana. | `.8`: F6 publica limites e numeros medidos; F5 fica `NO-ACTION` salvo blocker. Benchmark de custo por camada e' `.9`/pre-1.0, nao motivo para alterar o core agora. |
| **Lazy query** | `view()` L1-L4 esta' funcional para column-pruning, `@dict`/raw, filtros e agregacoes; L5 (`group_ranges`/`agg_by`) e' experimental. Coluna `tcf` entrelacada cai em materializacao total. | `.8`: manter API read-only e documentacao correta. QueryPlan/`execute()`, pushdown mais rico e indices derivados ficam em `H-QUERY-04`/`.9`; nao transformar `decode()` em executor monolitico. |
| **SQL** | SQL existe no `DatasetReader`/SQLite e no gadget LLM, fora do core; `view()` nao implementa parser SQL, joins, semantica de NULL/tipos, ORDER/LIMIT/DISTINCT ou plano multi-tabela. | `.8`: nenhuma camada SQL nova. O gadget LLM/schema continua deferred/spin-off; SQL sobre TCF deve consumir `view()` ou dados materializados sem acoplamento ao formato. |
| **Parquet/Arrow/Polars** | Core recebe estruturas Python genericas; nao ha adapter Parquet no pacote. Parquet aparece como trilho de armazenamento, referencia de column-store e pesquisa V2-K/L. | `.8`: nenhuma mudanca. Adapter/Polars, sidecar `.tcfx`, chunking/footer e index-on-arrival sao `.9`/2.0, com benchmark de leitura e custo de memoria proprio. |
| **Corrupcao/hardening** | BUG-12, checksum e orcamento de expansao continuam registrados e fora do dominio emitido pelo encoder. | `0.8.1`/pre-1.0 conforme a regra vigente; nao furam F6/C3 sem reclassificacao neste ticket. |

### Fechamentos possiveis do `.8`

1. Fechar R1.5 com `T-SPEC-STATUS-08` (Opcao A), laboratorio cadastral, FLOOR total-byte e fronteira
  de spec customizado validada por RT. Nenhum novo spec entra automaticamente no pacote; `DateSpec`
  so' pode preemptar F6 por aprovacao explicita e gate proprio.
2. Fechar F3/F4 como **evidencia amostral**, mantendo no material a lista explicita do que faltou
  (F3-3 residual, F3-4 populacao, hubs F4 fora do minimo). A afirmacao de paralelismo deve ser
  limitada aos casos medidos.
3. Executar F6 doc-only + wheel + clean-room: README EN/PT, referencia lazy/formato, metadata,
  changelog, satelites e smoke. So' depois avaliar C3.
4. C3 permanece ato separado: tag/publicacao `v0.8.0` exige go explicito do owner.

### Revisoes deliberadamente deixadas para `.9` ou depois

- Ceiling de nature (delta-aware/field-decomposed), novos specs BR e registry carregavel.
- `DateSpec` ISO/calendar-aware, caso nao receba aprovacao e dois gates reais antes do F6.
- Cap global de workers, paralelismo intra-coluna e reengenharia C1/C2 do core HCC.
- QueryPlan/`execute()`, joins, indices/sidecar `.tcfx`, Parquet/Arrow/Polars e camada SQL.
- Quoting avancado, inferencia de specs/tipos, TCF.8H e formas B/C do V2-B.
- BUG-12, checksum/tcfx, orcamento de expansao e contratos definitivos pre-1.0.

### Janela de execucao em massa apos o fechamento

A execucao populacional pode ser feita **depois** de F6, do rebuild/smoke clean-room e do closeout
do pacote, sem reabrir o escopo do `.8`. Ela deve ser registrada como uma atividade separada:

1. **Gate de reentrada**: commit/tag do candidato, ambiente registrado, hubs em `Z:/tcf-data/`,
  sem dados externos novos e sem alterações em `src/tcf` durante a rodada.
2. **Passo de integridade**: `decode(encode(x)) == x`, byte-determinismo serial/paralelo, pins e
  ausência de corrupção em cada dataset; falha interrompe a rodada.
3. **Passo de custo**: wall-clock mediano/p95, memória heap/RSS best-effort, modo Cython,
  workers efetivos e bytes total/header/body; claims de paralelismo ficam limitados ao ambiente.
4. **Passo populacional**: F3-4 600k e hubs F4 fora do mínimo, sem misturar os números com os
  artefatos de closeout; os resultados recebem runner, seed, proveniência e `RESULT.md` próprios.

Essa janela não é pré-requisito para publicar se o owner mantiver a decisão amostral já registrada;
é uma validação pós-closeout para escala e planejamento `.9`.

## Estado corrente (2026-07-12)

- F0 e Passo 1 concluídos; F1/F2 concluídos e versionados; FLOOR + fronteira de spec customizado
  verificados; suíte local completa: **634 passed,
  2 skipped** (inclui os testes `requires_data` com os hubs de `Z:`).
- Avaliação de fechamento confirmou o core regular verde e separou dívida de release de pesquisa.
- R0 concluído: BUG-14 fechado no lote A (decoder LF-only, testes parametrizados e gates
  `test_core_rt` + `test_regression_v1_baseline` + `test_real_world_snapshots` verdes: 104 passed).
- A branch local estava 10 commits à frente de `origin/main` na avaliação; push e publicação seguem
  atos explícitos do owner, não tarefas automáticas desta fila.

## Protocolo temporal de continuidade

- **Ao abrir**: `STATUS` (bloco vigente) → este ticket → checkpoint vigente → último diário.
- **Ao concluir uma fase/bug**: marcar primeiro o checkbox/estado neste ticket ou no T-QA; registrar
  evidência no artefato dono; depois atualizar o resumo do `STATUS`.
- **Ao encerrar sessão significativa**: criar/atualizar o diário do dia com “aberto para próxima
  sessão”. Criar checkpoint novo somente em pausa explícita ou quando a rota mudar materialmente.
- **Memória Copilot repo-scoped**: manter apenas ponteiros + próximo concreto. Atualizá-la na mesma
  sessão em que mudar o checkpoint ou o próximo item; nunca copiar métricas mutáveis para ela.
- **Sem churn**: se a rota não mudou, não reescrever checkpoint/memória. Git + diário guardam o
  tempo; este ticket guarda a ordem vigente.

## Estado de partida (2026-07-10, pós-F0)

F0 do T-QA-8: **12 de 13 bugs resolvidos** em 4 lotes (60 repros pinados; suíte 590 passed;
byte-neutralidade 122+189+103 casos; eficácia medida 1474 cortes). Resta BUG-12 (lote próprio,
CORE) + residuais-de-checksum (trilho tcfx). Release pré-verificado (wheel + clean-room smoke,
T-DIST). F0-3 fechado stdlib-only. Flag de paralelismo registrado (T-CODE-PARALLEL-BUDGET,
design pós-F3).

## PASSO 1 — fácil e sem risco (higiene de status; só rotulação rastreável)

- [x] **1a** `T-FMT-HEADER-BASE-HEX` → `closed-welded` (weld `a381cdb` + ADR-0032 §3 `da0ea35` +
  claim `6bbc86c`). FEITO 2026-07-10.
- [x] **1b** `T-CODE-DESCAPAR-V2B` → `closed-parcial` (forma A `a201c1e`; formas B/C → linha
  V2B-DESCAPAR-B/C no ROADMAP Tier 1). FEITO 2026-07-10.
- [x] **1c** `T-DATA-TRANSMISSION-GROUPING` → `closed-done` (entrega = coverage-matrix.md,
  `033bba3`). FEITO 2026-07-10.
- [x] **1d** `T-FMT-NAME-ESCAPING` → `closed-parcial` (interim `58f7dee` + endurecimento F0;
  estudo → ticket-FILHO [T-FMT-QUOTING-STUDY](T-FMT-QUOTING-STUDY.md), .9 — preferência do owner:
  filho em vez de linha solta; linha QUOTING-STUDY no ROADMAP aponta pro ticket). FEITO 2026-07-10.
- [x] **1e** `T-FMT-TCF8H-HEADER` → `closed-decided` (slot `H` `a001fd3`/ADR-0031; codec → .9 via
  T-STUDY-HIERARCHICAL-TCF, que segue ABERTO). FEITO 2026-07-10.
- Regra cumprida: bloco de encerramento datado no topo de cada um citando commit/ADR; conteúdo
  histórico intocado; zero moves/renames.

## PASSO 2 — alto valor (o caminho crítico do .8)

- [x] **2a** T-QA-8 **F1** — runner de telemetria FEITO (2026-07-12): `bench_evidencia.py` +
  `bench_evidencia_probes.py` (conceitos portáveis F0-3), 10 testes-guarda, pinos exatos
  (1523/300/89616), verificação adversarial com ressalvas fechadas (RT de transformação =
  conteúdo+idempotência). Suíte 600 passed. NOTA: o ponteiro no T-FLOW-ENCODE-STRATEGIES-TELEMETRY
  fica pro momento F3 (quando a telemetria de estratégias rodar de fato).
- [x] **2b** T-QA-8 **F2** FEITO (2026-07-12): 29 casos RT 29/29 via driver reprodutível
  (`bench_evidencia_f2.py`), material versionado em `evidencia-0.8/f2/` (RESULT.md gerado).
  Números-chave: header 0/+7/+13B; README **242B**; cap V2-B deixa **13.5%** na mesa em K>8192;
  ACHADO placeholders-README mod-11-válidos (nota pro F6). Suíte 600 passed.
- [x] **2b-gate (R0)** T-QA-8 **BUG-14** — fechado 2026-07-12 (lote A): red→green + fix LF-only
  no decoder dos dois níveis + regressão/baseline/real-world verdes.
- [~] **2c** T-QA-8 **F3 (amostra)** — sintéticos + curva de escala completos; paralelismo parcial
  consolidado em `experiments/results/evidencia-0.8/f3/RESULT.md` (F3-1 31/31, F3-2 10/10,
  F3-3 parcial, F3-4 não executado). Decisão explícita 2026-07-12: **não rodar população total**
  durante o closeout do `.8`; completar massa fica para janela dedicada.
- [~] **2d** T-QA-8 **F4-mínimo** FEITO (2026-07-12): 9 casos nos hubs prontos, RT 9/9,
  `evidencia-0.8/f4-minimo/`. Δ vs CSV 50-81%. **ACHADO**: nature CNPJ PIORA em receita REAL
  (+7339B, split→raw) mas ajuda no sintético — gap sintético-vs-real com repro; reforça Opção A do
  T-SPEC-STATUS-08 + caveat pro F6. População total (tpch-sf01 600k) + 3 hubs a criar = janela
  dedicada pós-release (não bloqueia o closeout).
- [ ] **2e** T-QA-8 **F5** — janela condicional, default **NO-ACTION**. Só o que a telemetria
  apontar como blocker ou ganho direto de fechamento vira sub-exp próprio com gate real-world;
  otimização de produto sem blocker vai para `.9`.
- [ ] **2f** T-QA-8 **F6** — DOC-01 (README com números MEDIDOS; embarca na wheel) + DOC-03/04/05
  + errata T-DOC-3 de carona + re-build wheel + clean-room smoke.
- [ ] **2g** `T-DIST-RELEASE-0.8.0` **C3** — tag v0.8.0 → Trusted Publishing. **GO explícito
  do owner.**

## PASSO 3 — decididos pra DEPOIS do .8 (fronteira registrada; nada a fazer agora)

| destino | itens | razão |
|---|---|---|
| **0.8.1** | BUG-12 (hang HCC decode) + guardas básicos de expansão/RLE sob blob corrompido | hardening importante, mas fora do domínio emitido pelo encoder; lote próprio + gate completo CORE |
| **.9** | codec TCF.8H (T-STUDY-HIERARCHICAL-TCF + EXP-015); T-OPT-INFERENCE (specs induzidas + bN, gate H-TYPE-03); estudo CSV-quoting; V2-B formas B/C; T-FLOW (parte estratégias H) | slot/registro já no .8; carga é research |
| **pré-1.0** | T-API-BOUNDARY-CONTRACTS; T-FMT-OMIT-OR-DECLARE; T-FMT-META-STRICT itens 1-2/6 (checksum→tcfx) | contratos definitivos, sem pressa pré-material |
| **paralelo** | T-TOOL-TCF-FIX-CORRUPTION; T-CODE-PARALLEL-BUDGET (design pós-F3); META-STRATA-GOVERNANCE (cadência) | não bloqueiam release |
| **deferred (intocados)** | T-CODE-OUTPUT-SINKS, T-CODE-PLAN-CONTRACT, T-DATA-3, T-RECOVER-LLM-SCHEMA-MODE, T-SHAPER-CODE-HARDENING | sem relação com o .8 |

## Critério de aceite

- [ ] Passos 1 e 2 executados NA ORDEM (cada checkbox cruza o commit que o fechou).
- [ ] Regra de ROI respeitada: apenas bugs do domínio aceito, artefato ou evidência furam F3/F4/F6;
  bordas de corrupção permanecem rastreadas sem sequestrar o fechamento.
- [ ] Fronteira do Passo 3 respeitada: nada dessa tabela entra no .8 sem decisão nova do owner.
- [ ] Ao publicar (2g): este ticket fecha `closed-done` e o que sobrar de F5/otimização vira
  ticket próprio do ciclo seguinte.
