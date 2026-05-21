# STATUS — TCF (compendio sempre-atualizado)

**Atualizado em**: 2026-05-21 (Pacote 2 escape-deduction fechado
como CLOSED-INSUFFICIENT-GAIN. Caracterizacao em real-world (Adult
1k/5k + TPC-H region/customer/lineitem 5k, 942kB body) mostrou
H-ED-01/02/03 marginais (0.01-0.12% ganho) e H-ED-original lower
bound 1.13% — abaixo criterio 5%. Sub-exp 11 antigo (T01, 15.7%)
NAO generaliza pra real-world (datasets eram "digit-dominant"
construidos). Pacote 4 (OBAT ADR-0009) continua sendo win principal.
M9 baseline preservado.)

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

## Foco atual — Pacote 4 FECHADO-PARCIAL + decisao sobre proximo

**Pacote 4 — Perf OBAT/HCC** (fechamento 2026-05-20):
- **H-PERF-02 WELDED** (ADR-0009): hash trigrama em OBAT, alpha 1.75→1.42,
  lineitem full 60175 **21.3min real** (vs 71min pre-welding)
- **H-PERF-04 ADIADA**: trigrama de meio inviavel byte-canonical em
  datas com prefix popular. Patricia trie como fallback futuro.
- **H-PERF-05 ADIADA**: HCC opt zero-risk so' 1.04x; caps trazem byte
  loss 3-6%. H-PERF-05d (counter incremental) permanece aberta como
  unico caminho zero-risk de alto potencial.
- **H-PERF-06 ADIADA**: Cython/Rust port — dependia de Python opt
  esgotar. Reaberto so' se necessario.

Labs do Pacote 4 (todos fechados):
- [`2026-05-19-obat-perf-optimization/`](experiments/lab/dirty/2026-05-19-obat-perf-optimization/) — OBAT welded (ADR-0009)
- [`2026-05-20-obat-perf-phase2-trigram-middle/`](experiments/lab/dirty/2026-05-20-obat-perf-phase2-trigram-middle/) — H-PERF-04 adiado
- [`2026-05-20-hcc-perf-optimization/`](experiments/lab/dirty/2026-05-20-hcc-perf-optimization/) — H-PERF-05 adiado

**Pacotes fechados recentes**:
- Pacote 4 (Perf OBAT/HCC) — CLOSED-PARCIAL 2026-05-20 (OBAT welded;
  HCC opt e trigrama meio adiados)
- **Pacote 2 (Escape deduction)** — CLOSED-INSUFFICIENT-GAIN 2026-05-21
  (ganho real-world max 1.13% << criterio 5%)

**Proximo pacote — decisao pendente**:
- **Revisao conceitual** de hipoteses confirmada-empirica (sintetico
  vs real-world generalizacao) — anti-incidente, ganha maturidade
- **Phase 3 OBAT/HCC** (Patricia trie + counter incremental) — se HCC
  perf virar prioridade
- **T02-T07** (outras naturezas pre-tx) — META-TYPE-ENCODERS criterio
  ainda nao atingido (precisa 2-3 naturezas validadas)

### Pacotes fechados (referencia)

| Pacote | Foco | Status | Welding |
|---|---|---|---|
| **Pacote 1** (Delta-aware) | auto-pre detect_cadence → OBAT hint → HCC seq-RLE | fechado | EXP-010 (clean), 20/20 RT |
| **Pacote 1 refino** (H-DA-09b-v2) | regra numeric+high-cardinality em real-world | fechado | ADR-0008 em EXP-010/auto_pre |
| **Pacote 3** (parser robustness) | bug `,` em literais HCC | fechado | ADR-0007 em src/tcf/composicional/syntax.py |
| **Pacote 4** (perf OBAT) — parcial | hash trigrama OBAT | **welded** (sub-pacote 1) | ADR-0009 em src/tcf/core/online.py |

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
| [META-TYPE-ENCODERS](tickets/META-TYPE-ENCODERS.md) | **OPEN** | plano-mestre T01-T07 + L01-L05 |

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

### Prioridade alta (ciclo Perf phase 2)

1. **EXP-014b — lineitem full 60175 real** (~18.5min estimado pos-ADR-0009).
   Confirma extrapolacao quadratica. Sem riscos: pipeline ja' validado.
2. **H-PERF-04 trigrama de meio** — datas TPC-H (l_shipdate/commit/receipt)
   so' tiveram 2x speedup; buckets `199/200/202` dispersam mal.
   Esperado: 5x+ adicional nessas colunas.
3. **H-PERF-05 HCC `_detect_compositions`** — gargalo dominante apos
   OBAT-opt (24% antes → ~40% relativo). Sub-exp profile + prototipos.

### Prioridade media (decisao pendente)

4. **Pacote 2 (escape deduction H-ED-01..04)** — adiado desde 2026-05-17.
   Ortogonal ao Pacote 4. Decisao: priorizar agora ou aguardar Pacote 4
   fechar.
5. **H-DA-09c/d/e** — refino threshold/multivariada/adaptativo do
   auto-pre detect_cadence. Decorrentes do Pacote 1.
6. **H-PERF-06 Cython/Rust port** — adiar ate' Python opt esgotar
   (alto overhead, integrar build system).

### Prioridade baixa (adiados explicitamente)

7. **META-TYPE-ENCODERS T02-T07** — outras naturezas (templated,
   enumerated, checked, etc.). Aguardando 2-3 naturezas validadas
   end-to-end.
8. **Track 2 L01-L05** — estudos de camada algoritmo (token-level,
   slot detection, markers tipados, tree-balance, pre-filter).

### Conceitual / revisao

9. **Revisao conceitual** das hipoteses `confirmada-empirica` —
   datasets sinteticos vs real-world. Atualmente: real-world validado
   so' em Adult Census (5k rows) + TPC-H (5k rows lineitem); generalizacao
   pra outros perfis nao testada.

---

## Discipline de manutencao

Este arquivo deve ser **atualizado**:
- Ao fechar sub-experimento (status table)
- Ao tomar decisao estrutural (estrutura de pastas, ticket aberto/fechado)
- Ao mudar foco de natureza (T01 -> T02 etc.)

Se editar, lembrar: **status absoluto, nao incremental**. Substituir
o que mudou, manter o resto coerente.
