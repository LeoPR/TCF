---
title: T-REL-08-CLOSEOUT — ordem de execução pra fechar o 0.8 (fácil-sem-risco → alto-valor → fronteira .9)
status: open
priority: P1
created: 2026-07-10
updated: 2026-07-10
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-DIST-RELEASE-0.8.0.md
  - ROADMAP.md
  - STATUS.md
---

# T-REL-08-CLOSEOUT — fechamento do 0.8, na ordem

**[dispositivo→execução]** Materializa o levantamento de 2026-07-10 (pedido do owner: listar os
tickets abertos e a ordem de ataque com critérios — "fácil e sem risco primeiro, os de alto valor,
e os que ainda tem coisa pra implementar antes de ir pro .9"; e "mesmo a ordem de execução do que
verificamos gera tickets — rastreabilidade e memória, não pode ficar tudo só na conversa").
Este ticket é o GUIA da ordem; cada passo aponta o ticket/fase que o executa.

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
- [ ] **2b** T-QA-8 **F2** — controle minúsculo (single c/s header ×3 formas, readers
  decode×view, README-propaganda re-medido, escaping/hex/fail-loud, 1 blob-exemplo por dict,
  boundary do cap 8192).
- [ ] **2c** T-QA-8 **F3** — sintéticos + curva de escala + paralelismo (alimenta o design do
  T-CODE-PARALLEL-BUDGET).
- [ ] **2d** T-QA-8 **F4** — públicos (6 hubs prontos + 3 a criar via csv_to_sqlite) +
  consolidação com nota metodológica.
- [ ] **2e** T-QA-8 **F5** — janela de otimização SÓ do que a telemetria apontar (gated,
  cada candidato em sub-exp próprio com gate real-world).
- [ ] **2f** T-QA-8 **F6** — DOC-01 (README com números MEDIDOS; embarca na wheel) + DOC-03/04/05
  + errata T-DOC-3 de carona + re-build wheel + clean-room smoke.
- [ ] **2g** `T-DIST-RELEASE-0.8.0` **C3** — tag v0.8.0 → Trusted Publishing. **GO explícito
  do owner.**

## PASSO 3 — decididos pra DEPOIS do .8 (fronteira registrada; nada a fazer agora)

| destino | itens | razão |
|---|---|---|
| **0.8.1** | BUG-12 (hang HCC decode — lote próprio, gate completo CORE) | DoS só em blob corrompido; não segura a publicação |
| **.9** | codec TCF.8H (T-STUDY-HIERARCHICAL-TCF + EXP-015); T-OPT-INFERENCE (specs induzidas + bN, gate H-TYPE-03); estudo CSV-quoting; V2-B formas B/C; T-FLOW (parte estratégias H) | slot/registro já no .8; carga é research |
| **pré-1.0** | T-API-BOUNDARY-CONTRACTS; T-FMT-OMIT-OR-DECLARE; T-FMT-META-STRICT itens 1-2/6 (checksum→tcfx) | contratos definitivos, sem pressa pré-material |
| **paralelo** | T-TOOL-TCF-FIX-CORRUPTION; T-CODE-PARALLEL-BUDGET (design pós-F3); META-STRATA-GOVERNANCE (cadência) | não bloqueiam release |
| **deferred (intocados)** | T-CODE-OUTPUT-SINKS, T-CODE-PLAN-CONTRACT, T-DATA-3, T-RECOVER-LLM-SCHEMA-MODE, T-SHAPER-CODE-HARDENING | sem relação com o .8 |

## Critério de aceite

- [ ] Passos 1 e 2 executados NA ORDEM (cada checkbox cruza o commit que o fechou).
- [ ] Fronteira do Passo 3 respeitada: nada dessa tabela entra no .8 sem decisão nova do owner.
- [ ] Ao publicar (2g): este ticket fecha `closed-done` e o que sobrar de F5/otimização vira
  ticket próprio do ciclo seguinte.
