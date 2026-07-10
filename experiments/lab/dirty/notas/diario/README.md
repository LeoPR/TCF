# Diario — index

**Proposito**: registro diario das conversas/decisoes/experimentos.
Cada arquivo `YYYY-MM-DD.md` cobre 1 dia. Permite revisitar e
comparar decisoes tomadas ao longo do projeto.

**Regra**: cada sessao significativa termina com entrada no diario
do dia. Decisoes-chave em tabela. Arquivos criados/modificados em
resumo. Aberto pra proxima sessao explicitado.

**Entradas *(retroativa)***: reconstruidas 2026-07-09 (T-CLEAN-3 T3-a) a partir dos
commits do dia + docs da era (blocos SESSAO do STATUS, checkpoints, notas datadas) —
escritas na chave da EPOCA, cada claim rastreia a um hash. 29 dias que tinham
commits mas nao tinham entrada.

## Entradas

- [2026-05-17](2026-05-17.md) — T01 v2 critica, lab obat-delta-aware
  criado, Q15 confirmada (-22.2% bytes), roadmap cross-lab criado
- [2026-05-18](2026-05-18.md) — Pausa estrategica em EXP-012; reorganizacao
  cientifica de docs (CLAUDE.md, ADRs, vocabulary, hooks, index auto, audit recipe)
- [2026-05-19](2026-05-19.md) — Pacote 3 fechado: ADR-0007 welded
  (separator heuristico em ref→lit), EXP-013 TPC-H RT 3/8 → 8/8
- [2026-05-20](2026-05-20.md) — Pacote 4 fechado-parcial (OBAT welded, HCC adiado);
  ADR-0009; lineitem full
- [2026-05-21](2026-05-21.md) — Pacote 2 fechado (insufficient-gain); nova convencao
  YAML tickets
- [2026-05-22](2026-05-22.md) — H-DA-11 (ADR-0010) e Pacote 1 delta-aware (ADR-0011) welded
  canonical — baseline M9 1615B vira M10 1523B; 9.87%/11.73% real-world *(retroativa)*
- [2026-05-23](2026-05-23.md) — Serie de NO-GOs (enumerated, threshold cadence, naturezas
  raras — M10 perto do otimo); CI/CITATION/ADR-0012; multi-col WELDED (multi.py, ADR-0013) *(retroativa)*
- [2026-05-24](2026-05-24.md) — ADR-0014 API unificada + SideOutputs welded; EncoderManager
  + schema builder welded; dirty lab CPF/CNPJ/IP sub-exps 01-10 *(retroativa)*
- [2026-05-25](2026-05-25.md) — Sub-exps 11-14 fecham diagnostico IP (2 bugs em src/tcf);
  ADR-0015 welded (natures CPF/CNPJ); benchmark formats TCF 4/6 *(retroativa)*
- [2026-05-26](2026-05-26.md) — SPEC_IP + ADR-0016 multi-delta welded (subnet 117%→4.18%);
  checkpoint sessao maxima; PipelineConfig Fase 1 *(retroativa)*
- [2026-05-27](2026-05-27.md) — Consolidacao dirty lab + baseline-consolidado (source of
  truth); Sprints 1-2 v1.0: suite regressao formal + ADR-0017 freeze proposed *(retroativa)*
- [2026-05-29](2026-05-29.md) — Sprint 3 v1.0 (ADR-0017 accepted); ADR-0018 roadmap v2.0;
  H-PERF-06 reframed (alvo real = HCC); filosofia de design no CLAUDE.md *(retroativa)*
- [2026-05-30](2026-05-30.md) — H-PERF-06-v2 Fase A: 24 candidatos de prune, so #15
  byte-safe (1.354x); achado metodologico #03 (mini-suite nao basta) *(retroativa)*
- [2026-05-31](2026-05-31.md) — Gate real-world (T-REGRESSION-REAL-WORLD) + welds ADR-0019
  (prune top-K) e ADR-0020 (Cython opcional, 2.67x); gating cientifico do shaper *(retroativa)*
- [2026-06-01](2026-06-01.md) — br-identidades sintetico (500k CPF + 100k CNPJ,
  declared-bias) + samples part/partsupp TPC-H; T-DATA-2/3/4 registrados *(retroativa)*
- [2026-06-02](2026-06-02.md) — receita-cnpj REAL non-PII: nature CNPJ 40.9% em dado real
  (T-DATA-2 closed-done) + reorg separacao de concerns Fases 0-7 (llm-benchmark/) *(retroativa)*
- [2026-06-03](2026-06-03.md) — STATUS.md sincronizado com o estado real — 33 commits desde
  2026-05-27 (datasets BR/CNPJ, Cython, gates, reorg) *(retroativa)*
- [2026-06-07](2026-06-07.md) — ADR-0021 (incidente OneDrive); schema gadget nasce: design
  doc + Fase 1 FK detect + Fase 3 quality zero-custo *(retroativa)*
- [2026-06-08](2026-06-08.md) — Schema gadget COMPLETO (Fase 4 CLI/relatorio + Fase 2 date
  check); ticket closed-done; STATUS sync *(retroativa)*
- [2026-06-12](2026-06-12.md) — Auditoria Strata L0; reorg memorias + consolidacao
  (M3-M9 arquivadas)
- [2026-06-13](2026-06-13.md) — Analise organizacao src/tcf/; registro bibliografico
  in-code
- [2026-06-14](2026-06-14.md) — O-FMT-02 sort_by + V2-B dicionario welded;
  ADR-0024 pre-1.0 versioning; bytes-core 0.7 welded
- [2026-06-15](2026-06-15.md) — Fechamento ciclo 0.7: higiene tickets + 2 decisoes
  do owner
- [2026-06-16](2026-06-16.md) — Pos-0.7: tcf-format 0.7.1 publicado no PyPI; lazy view vira
  gadget L1-L5 (27 testes); ROADMAP em tiers; number-nature e O-FMT-12 PARK *(retroativa)*
- [2026-06-17](2026-06-17.md) — Filtros modulares F1+F1.5 (natures_compiler, 14 testes);
  F2/ADR-0027 parado em (A) por decisao do owner; H-QUERY-04 decode-DAG design *(retroativa)*
- [2026-06-18](2026-06-18.md) — Auditoria Strata read-only: T-CLEAN-2 defrag (QW-1..5
  executados) + META-STRATA-GOVERNANCE (cadencia G-1..G-4) *(retroativa)*
- [2026-06-20](2026-06-20.md) — V2-RLE-STREAM fechado (nicho textual aberto); plano 0.8
  decidido; lazy A1-A3; H-GDICT-01/H-REF registrados; header row-count refutado *(retroativa)*
- [2026-06-21](2026-06-21.md) — Guia honesto de transmissao API (~5-15%); checkpoint Strata;
  faxina pre-0.8; A4: lazy view promovido pro core (src/tcf/view.py) *(retroativa)*
- [2026-06-22](2026-06-22.md) — Drift #TCF.6-default corrigido nos docs; A5 reference fecha
  o workstream A; B1.0 design cross-dict (dobradica = largura base-94) *(retroativa)*
- [2026-06-23](2026-06-23.md) — B1 fechado: brotli fora do gate (correcao do owner);
  cross-dict GANHA em same-domain-refs (−19.3% ca-GrQc real) → recomendacao B2 *(retroativa)*
- [2026-06-24](2026-06-24.md) — Escopo 0.8/0.9 decidido (owner); poda pre-0.7 S1-S5;
  ADR-0028; P1-P4 modularizacao; #TCF.8 natures welded (ADR-0027) + ADR-0029 *(retroativa)*
- [2026-06-25](2026-06-25.md) — Discriminador #TCF.8 de 1 char + colunas anonimas
  (drop_names) + tcf8-estrutura-plano consolidado; lazy-view le #TCF.8 *(retroativa)*
- [2026-06-26](2026-06-26.md) — Fila #TCF.8 consolidada (3 baldes); T-CI-3 gate .pyx vira
  teste; estrategia de distribuicao Cython; ADR-0030 freeze single-col 1.0 *(retroativa)*
- [2026-06-27](2026-06-27.md) — EI encostado; design B2 group-dict + revisao adversarial
  (24 achados, 0 blocker); re-segmentacao em 5 workstreams, gate geral N≥5 *(retroativa)*
- [2026-06-30](2026-06-30.md) — B2 revisado (correcoes A-D) + prototype read-only RT
  lossless valida B1; achado H-DICT-HIGHCARD (cap 1024 deixa 30%+ na mesa) *(retroativa)*
- [2026-07-01](2026-07-01.md) — Pos-gate (B2-naive 1/5): owner reabre o cross-dict por outras
  perspectivas — indices moveis/emprestimo (= H-REF-02 re-derivado); T-CLEAN-2 backlog DB-1..7
- [2026-07-02](2026-07-02.md) — Descapar V2-B forma A welded: cap de compute 1024→8192
  (byte-safe), gate verde sem re-pin; formas B/C deferidas *(retroativa)*
- [2026-07-04](2026-07-04.md) — Revisao critica geral do projeto (6 lentes)
- [2026-07-05](2026-07-05.md) — Execucao pos-revisao: fix RT (direcao 1) + cadeia Cython
  (direcao 3); grupo de labs hierarquico P1-P9
- [2026-07-06](2026-07-06.md) — TCF.8H: omit-closes default + checklist header 5 camadas;
  Ciclo 1 de tipos fechado (1a/1b/1c); reframe tipos-como-specs; motor spec_bin *(retroativa)*
- [2026-07-07](2026-07-07.md) — Specs bN por largura de bits + spec_bin Formato A;
  consolidacao com 2 correcoes (baseline V2-B, colapso brotli); H-TYPE-00..04 *(retroativa)*
- [2026-07-08](2026-07-08.md) — bN: os 3 fluxos medidos (F1 2.4x, F3 5.9%/0.5%);
  nomenclatura b1/b2/b4/b3/B resolvida; revisao critica do dia (reconciliacao)
- [2026-07-09](2026-07-09.md) — ADR-0031 (H) + ADR-0032 (#TCF.8 DEFAULT, M1-M5: flip, corte
  legado, hex, escaping, 0.8.0); survey bases/radix; T-CLEAN-3 defrag
- [2026-07-10](2026-07-10.md) — Release 0.8.0 pré-checado (wheel + clean-room smoke); T-QA-8
  planejado (material comprobatório F0-F6; 10 bugs + 5 doc-drifts registrados, zero fix)
