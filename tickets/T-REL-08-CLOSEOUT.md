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
| **R1.5 — investigação de specs (REDIRECT owner 2026-07-12)** | investigar a fundo o que comprime além do básico (CPF já estudado; CNPJ no básico); revisar o inventário geral de specs + o compilador (tirar specs do welded); PLANEJAMENTO pra fechar 0.8 E pré-1.0 | plano de specs registrado (o que atacar no .8 vs .9) | R2 |
| **R2 — superfície publicável** | F5 somente se gated; F6 reconcilia README EN/PT, referência, metadata, wheel e smoke clean-room (+ **caveat nature-CNPJ-piora-em-real**) | pacote/documentação descrevem o mesmo `#TCF.8` | C3 |
| **R3 — ato de release** | C3: tag `v0.8.0` + Trusted Publishing, somente com go explícito do owner | `0.8.0` publicado e closeout fechado | abrir ciclo seguinte |

**Próxima ação concreta em nova sessão**: reler este bloco → **R1.5 investigação de specs**
(redirect do owner 2026-07-12: antes do F6, investigar o que comprime + revisar specs + compilador
pra tirar do welded; planejamento 0.8+pré-1.0), depois R2 (F6). Specs do `.8` já DECIDIDOS
(Opção A, [T-SPEC-STATUS-08](T-SPEC-STATUS-08.md)). Checkpoint temporal:
[`2026-07-12-revisao-roi-fechamento-08.md`](../experiments/lab/dirty/notas/checkpoints/2026-07-12-revisao-roi-fechamento-08.md).

## Estado corrente (2026-07-12)

- F0 e Passo 1 concluídos; F1/F2 concluídos e versionados; suíte local completa: **600 passed,
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
