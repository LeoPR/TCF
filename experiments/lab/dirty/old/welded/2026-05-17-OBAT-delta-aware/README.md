---
title: OBAT delta-aware (Pacote 1)
type: dirty-lab
status: empirical-coverage-complete
tags: [tcf, delta-aware, obat, hcc, package-1]
created: 2026-05-17
updated: 2026-05-18
welded_to: experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/
related:
  - docs/adr/0002-vertice-triplice-restricao.md
  - docs/adr/0003-tripartite-pre-obat-hcc.md
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
sub_experiments:
  - 01-baseline-obat-hcc-atual
  - 02-hcc-sozinho-rle-near-identical
  - 03-cadence-break-recovery
  - 04-obat-shape-consistency-hint
  - 05-numeric-ids-h-da-06
  - 06-auto-hint-regression-D1-D9
  - 07-per-run-delta-audit
  - 08-min-len-trade-off
  - 09-auto-detect-cadence-heuristic
---

# 2026-05-17 — OBAT delta-aware (estudo)

**Estado**: cobertura empirica inicial completa (9 sub-exps).
Pronto pra welding em clean prototype. Revisao conceitual real-world
pendente.
**Macro pai**: [`../README.md`](../README.md)
**Origem**: continuacao do T01 incremental. Discussao em
[`../notas/T01-v2-critica-e-direcao.md`](../notas/T01-v2-critica-e-direcao.md)
levou a esta direcao — em vez de continuar como pre-tx multi-pass
(violando latencia/memoria do **vertice triplice**), explorar **OBAT
+ HCC** como ponto natural pra delta-awareness.

## Pergunta principal

Quando dois nos consecutivos sao do mesmo tipo (datas, p. ex.) e
OBAT detecta similaridade via LCP/LCS:

- Quanto OBAT pode/deve **propor** sobre delta?
- Quanto HCC pode/deve **complementar** (RLE, virtual refs, body)?
- Onde fica a **linha cinzenta** (areas onde ambos podem agir)?

A hipotese de trabalho (revisada 2026-05-17): **tripartite Pre /
OBAT / HCC**, onde:
- Pre detecta tipo e emite **dica generica** (sem nomear tipo)
- OBAT permanece **type-agnostic**, faz comparacoes relativas,
  emite marcadores abstratos
- HCC materializa em bytes e agrupa inteligentemente

As linhas cinzentas sao parte do estudo — nao pre-decidir, observar
via tentativas praticas. Detalhes em `notas/modelo-conceitual.md`.

## Outra direcao paralela: hints **genericos** (nao tipo-nomeados)

TCF e' orientado a colunas, e colunas tendem a ter formato estavel.
Detectar **previamente** (antes de chamar OBAT) e passar dica
**generica** evita que OBAT precise saber semantica.

Dicas aceitaveis (genericas):
- `byte_window=(X,Y)` — onde provavelmente esta a variacao
- `enable_relative=True` — habilitar modo quanto-maior/quanto-menor
- `monotonic_expected=True` — esperar sequencia ordenada
- `max_delta=N` — limiar pra emitir delta vs literal

Dicas rejeitadas (viciadas):
- `type="date"` — viola separacao
- `parse_as_datetime=True` — viola separacao

Hipotese: dicas genericas sao **mais baratas** que deteccao interna,
nao quebram vertice triplice, e mantem OBAT type-agnostic.

## Vertice triplice (restricao dura)

Nao perder de vista: TCF e' **online + single-pass + low-mem**.
Tecnicas que precisam de:
- multi-pass (DoD, GCD do stream, block min subtraction)
- buffer de janela > O(1)
- look-ahead de stream

**Sao descartadas mesmo com ganho de compressao**, porque o projeto
nao otimiza so' compressao. Ver [feedback-rigor-cientifico] e
[`docs/theory/perspectiva-triplice-e-pre-tx.md`](../../../../docs/theory/perspectiva-triplice-e-pre-tx.md).

## Restricao: src/tcf intocado

OBAT (`src/tcf/core/online.py`) e HCC (`src/tcf/composicional/syntax.py`)
sao **fonte de verdade**. Validados byte-canonical em D1-D9. Estudo
faz **fork dirty** — `obat_fork.py`, `hcc_fork.py` — e compara
contra canonical. **Nada altera src/ ate' welding deliberado** (cf.
[feedback-cuidado-fonte-verdade], M14).

## Escopo de datasets

Foco inicial: **D11a-h** (incremental, ja' bem estudados em T01).
Cobrindo:
- D11a (12 dias sequenciais)
- D11b (14 datas com bordas — Feb 29, transicoes mes/ano)
- D11c (13 datas mensais, dia 5)
- D11d (13 datetimes top-of-minute, cadencia 1m)
- D11e (13 datetimes mensais)
- D11f/g/h (cadencias ms/us/ns)

D11j/k/m (timezone) ficam pra fase posterior — uma natureza por vez.

## Estrutura (atualizada 2026-05-17 pos sub-exp 09)

```
2026-05-17-OBAT-delta-aware/
├── README.md (este)
├── notas/
│   ├── modelo-conceitual.md             ← tripartite Pre/OBAT/HCC
│   ├── perguntas-abertas.md             ← Q1-Q18 lab-specific
│   └── observacoes.md                   ← diario continuo (8 entradas)
├── 01-baseline-obat-hcc-atual/          ← caracteriza baseline 958B
├── 02-hcc-sozinho-rle-near-identical/   ← H-DA-01: HCC seq-RLE (-22%)
├── 03-cadence-break-recovery/           ← H-DA-04: refutada parcial (audit)
├── 04-obat-shape-consistency-hint/      ← H-DA-07: OBAT shape-preserve (-32%)
├── 05-numeric-ids-h-da-06/              ← H-DA-06: generaliza IDs (-61%)
├── 06-auto-hint-regression-D1-D9/       ← H-DA-09: always-on refutado (+275B)
├── 07-per-run-delta-audit/              ← H-DA-08: refutada (9B so')
├── 08-min-len-trade-off/                ← H-DA-10: D9 min_len=5 (-33B)
└── 09-auto-detect-cadence-heuristic/    ← H-DA-09b: confirmada (-18%, 18/20)
```

Status detalhado em [`../notas/roadmap-hipoteses.md`](../notas/roadmap-hipoteses.md).
Diario de decisoes em [`../notas/diario/2026-05-17.md`](../notas/diario/2026-05-17.md).

## Criterios de aceite — fechamento empirico inicial

| # | Criterio | Status |
|---|---|---|
| 1 | Baseline documentada (D11a-h) | ✓ sub-exp 01 |
| 2 | HCC sozinho extrai ganho (Q15) | ✓ sub-exp 02 (-22%) |
| 3 | Dica generica viavel (Q16/Q17) | ✓ sub-exp 04+09 (auto-detect) |
| 4 | Integracao tripartite end-to-end | ✓ sub-exp 04+09 |
| 5 | Generalizacao alem de datetime | ✓ sub-exp 05 (IDs numericos) |
| 6 | Regressao avaliada em data sem cadencia | ✓ sub-exp 06+09 |
| 7 | Documentacao continua | ✓ observacoes + diario + roadmap |

**Pendente pra clean prototype welding**: aplicar pipeline final
(auto-pre + OBAT canonical/hint + HCC seq-RLE) em **single-column**;
validar 20/20 datasets. Multi-column fica fora de escopo deste lab.

## Conexoes

- [feedback-dirty-lab-filosofia] — naive primeiro, engenhoca descartavel
- [feedback-materializacao-minimal] — abstrato em construcao, minimo em .tcf
- [feedback-rigor-cientifico] — 3 vertices, vocabulario disciplinado
- [feedback-validacao-e-dados] — D11a-h sao dados realisticos
- [META-TYPE-ENCODERS L02 / L03] — slot detection online, markers tipados
  (este lab e' a execucao parcial desses estudos diferidos)

## See also

- **Welded em**: [EXP-010](../../clean/EXP-010-tcf-delta-aware-prototype/) (single-col) + [EXP-011](../../clean/EXP-011-multi-column-basic/) (multi-col)
- **Roadmap cross-lab**: [`roadmap-hipoteses.md`](../notas/roadmap-hipoteses.md)
- **Diario do dia**: [`diario/2026-05-17.md`](../notas/diario/2026-05-17.md)
- **ADRs derivados**:
  - [ADR-0002 vertice triplice](../../../../docs/adr/0002-vertice-triplice-restricao.md)
  - [ADR-0003 tripartite Pre/OBAT/HCC](../../../../docs/adr/0003-tripartite-pre-obat-hcc.md)
  - [ADR-0004 multi-col header](../../../../docs/adr/0004-multi-column-header-compacto.md)
- **Origem (T01 superseded)**: [`T01-incremental-base-delta/`](../../2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/)
- **Critica que motivou pivot**: [`T01-v2-critica-e-direcao.md`](../notas/T01-v2-critica-e-direcao.md)
- **Checkpoint atual**: [`2026-05-18 pausa`](../notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md)
