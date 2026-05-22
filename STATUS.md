# STATUS — TCF (compendio sempre-atualizado)

**Atualizado em**: 2026-05-22 (**H-DA-11 WELDED canonical src/tcf**
via ADR-0010 — auto-detect min_len por coluna captura **9.87% weighted
real-world** em Adult+TPC-H. M9 baseline 1615B preservado EXATO. RT
100%. API publica `tcf.encode` agora chama `detect_min_len` por
dentro com gating n>=100. Wins: l_comment -29kB, fnlwgt -22kB,
l_extendedprice -20kB. Tickets fechados na sequencia 2026-05-21/22:
Pacote 2 INSUFFICIENT-GAIN, T-REVAL H-DA-01/06/10 (surpresa: H-DA-10
confirmada 9.92%), T-EXP-H-DA-11 CANONICAL-WELDED.)

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
> [`2026-05-18-pausa-para-organizar-documentacao.md`](experiments/lab/dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md)
> — pendente: retomar **EXP-012** (real-world test via shaper)

---

## TCF — visao 1 paragrafo

**TCF** (Tabular Compact Format) e' um formato de **compressao de
strings tabulares** v0.6 com 2 camadas canonicas:
- **OBAT** (Online Bidirectional Affix Tokenizer, alg16) — tokeniza
  via LCP+LCS contra strings anteriores. Em `src/tcf/core/`.
- **HCC** (Hierarchical Compositional Coding, M8.A) — compactacao
  composicional via detector unificado (refs atomicos+virtuais)
  + emit (`~` cria ref, `,` concat). Em `src/tcf/composicional/`.

API publica: `from tcf import encode, decode`. RT byte-canonical
validado em 9 datasets sinteticos (D1-D9, 1615 bytes total, ratio
medio 54.2%).

---

## Foco atual — H-DA-11 WELDED canonical + decisao sobre proximo

**Ciclo 2026-05-21/22 — Revalidacao + H-DA-11 fechado**:

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

**Pacote 4 — Perf OBAT/HCC** (fechado 2026-05-20):
- H-PERF-02 WELDED (ADR-0009) — hash trigrama, alpha 1.75→1.42
- H-PERF-04/05/06 ADIADOS (Patricia trie, counter incremental, Cython)

**Proximo pacote — decisao pendente**:
- **H-DA-11c** consolidar pre-pass features (detect_cadence + detect_min_len)
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

`datasets/synthetic/`:

### Core TCF (D1-D9) — controle algoritmo
Padroes estruturais (afixos, wrappers). Cobertos pelo TCF-CORE
canonical. Total 2981 raw -> 1615 TCF (54.2%). Referenciados em
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
| [T-DOC-1-citation-cff](tickets/T-DOC-1-citation-cff.md) | OPEN P3 | CITATION.cff + DOI |
| [T-DOC-2-diataxis-naming](tickets/T-DOC-2-diataxis-naming.md) | OPEN P3 | mapeamento docs Diataxis |
| [T-CLEAN-1-pre-commit-hooks](tickets/T-CLEAN-1-pre-commit-hooks.md) | OPEN P3 | pre-commit hooks |

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

## Estrutura de pastas (apos reorg 2026-05-16)

```
TCF/
├── STATUS.md                        # este arquivo
├── README.md, CHANGELOG.md, ...
├── src/tcf/                         # canonical (OBAT + HCC)
├── datasets/
│   ├── synthetic/                   # D1-D15 + D11a-d
│   └── canonical/                   # Adult Census, TPC-H
├── docs/
│   ├── algorithms/                  # OBAT.md, HCC.md, TCF-format.md
│   ├── theory/                      # data-natures-taxonomy, perspectiva-triplice
│   └── workbench/                   # research notes
├── tickets/                         # META-* (planos meta)
├── experiments/
│   └── lab/
│       ├── clean/                   # EXPs validados
│       └── dirty/                   # workbench experimental
│           ├── README.md
│           ├── notas/               # narrativas
│           ├── 2026-05-15-naturezas-e-camada/   # **ATIVO**
│           └── old/                 # M0-M14 historia (movidos 2026-05-16)
└── old/tcf/                         # v0.5 obsoleto
```

---

## Proximas direcoes (ordenado por prioridade)

### Prioridade alta (caminho feliz pos-H-DA-11)

1. **H-DA-11c consolidar pre-pass features** — unificar `detect_cadence`
   (ADR-0008, regra numeric+card) + `detect_min_len` (ADR-0010, heur v3)
   em pre-pass unico `analyze_column(values) → ColumnFeatures`. Reduz
   duplicacao + prepara terreno pra T02-T07. Medio risco/medio valor.
2. **H-DA-07 revalidacao real-world** — categoria B unica nao revalidada
   em T-REVAL. OBAT shape-preserve "confirmada-condicional" sem
   evidencia real-world. Baixo risco.

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
8. **T-DOC/T-CLEAN abertos** (P3) — CITATION.cff, mapeamento Diataxis,
   pre-commit hooks. Aderencia metodologica.

---

## Discipline de manutencao

Este arquivo deve ser **atualizado**:
- Ao fechar sub-experimento (status table)
- Ao tomar decisao estrutural (estrutura de pastas, ticket aberto/fechado)
- Ao mudar foco de natureza (T01 -> T02 etc.)

Se editar, lembrar: **status absoluto, nao incremental**. Substituir
o que mudou, manter o resto coerente.
