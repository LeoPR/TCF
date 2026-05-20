# STATUS — TCF (compendio sempre-atualizado)

**Atualizado em**: 2026-05-19 (ADR-0009 welded. OBAT hash trigrama
index reduz O(N²) a O(N) amortizado. **alpha 1.75 → 1.42** em
EXP-014, lineitem full 60175 estimado **71min → 18.5min** (-74%).
Speedup escala com volume (1.3x em 1k, 2.70x em 20k). Bytes IDENTICOS,
RT 100% em todos EXPs (007/010/011/012/013/014). M9 baseline preservado.)

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

## Foco atual — Pacote 1 (Delta-aware) FECHADO + Prototype Welded

**Mudanca de direcao 2026-05-17**: T01 incremental (pre-tx multi-pass)
abandonado por violar **vertice triplice** (single-pass/low-mem/low-latency).
Novo lab `2026-05-17-OBAT-delta-aware/` explorou alternativa OBAT-level.

**Pacote 1 (Delta-aware) — cobertura empirica completa**:
9 sub-exps em
[`experiments/lab/dirty/2026-05-17-OBAT-delta-aware/`](experiments/lab/dirty/2026-05-17-OBAT-delta-aware/).
Pipeline final: **auto-pre detect_cadence → OBAT canonical/hint → HCC fork seq-RLE**.

**Resultado consolidado** (20 datasets sinteticos):
- baseline (canonical) = 2770 B
- pipeline delta-aware = 2272 B (**-18.0%**)
- RT 20/20 OK
- 5 hipoteses confirmadas-empiricas (H-DA-01, H-DA-06, H-DA-07, H-DA-09b, H-DA-10)
- 1 refutada (H-DA-08), 2 refutadas parciais (H-DA-04, H-DA-09)

**Roadmap cross-lab**: [`experiments/lab/dirty/notas/roadmap-hipoteses.md`](experiments/lab/dirty/notas/roadmap-hipoteses.md)
**Diario do dia**: [`experiments/lab/dirty/notas/diario/2026-05-17.md`](experiments/lab/dirty/notas/diario/2026-05-17.md)

**Prototype clean welded**:
[`experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/`](experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/)
— single-column, 20/20 RT, 20/20 byte-match vs sub-exp 09. **src/tcf
intocado** — prototype IMPORTA e ESTENDE.

**Aviso conceitual**: confirmacoes sao `confirmada-empirica` em
datasets sinteticos. Real-world (TPC-H, Adult Census) **nao testado**.

### Foco anterior — T01 incremental (pre-tx, dirty old)

13 sub-experimentos em
[`experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/)
Mantido como referencia historica; superseded pelo Pacote 1 Delta-aware.

### Sub-experimentos T01 (cronologico)

| # | Pasta | Dataset | Encoder | TCF C | RT |
|---|---|---|---|---:|---|
| 01 | [`01-prova-conceito-D11a-dia/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/01-prova-conceito-D11a-dia/) | D11a (12 linhas, dia) | v0 monolitico | 42 | OK |
| 02 | [`02-bordas-D11b/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/02-bordas-D11b/) | D11b (14 linhas, bordas + leap year) | v0 monolitico | 59 | OK |
| 03 | [`03-cadencia-mensal-D11c/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/03-cadencia-mensal-D11c/) | D11c (13 linhas, fatura mensal) | v1 monolitico (escalas M/Y) | 22 | OK |
| 04 | [`04-staged-pipeline-D11c/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/04-staged-pipeline-D11c/) | D11c | v1 em 3 estagios (A/B/C separados) | 22 (identico ao 03) | 4/4 |
| 05 | [`05-staged-multi-dataset/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/05-staged-multi-dataset/) | D11a+b+c | 3 estagios copia 04 | 42/59/22 | 3/3 |
| 06 | [`06-staged-granularity-second/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/06-staged-granularity-second/) | D11a-d (D11d novo) | 3 estagios estendido (day + second) | 42/59/22/34 | 4/4 |
| 07 | [`07-cadencia-mensal-datetime-D11e/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/07-cadencia-mensal-datetime-D11e/) | D11c+d+**D11e** (novo) | 3 estagios copia de 06 | **D11e=34 (vs 80 sem escala = +57%)** | 3/3 |
| 08 | [`08-granularidades-finas/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/08-granularidades-finas/) | D11a-e + **D11f/g/h** (ms/us/ns) | 3 estagios estendido + multi-char | **D11f=39 (`1s`), D11g=43 (`1ms`), D11h=46 (`1us`)** | 8/8 |
| 09 | [`09-auditoria-self-contained-D11a/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/09-auditoria-self-contained-D11a/) | so D11a | decoder standalone | 42 bytes -> D11a byte-canonical SEM hint externo | OK |
| 10 | [`10-pacote-completo-com-validacao/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/10-pacote-completo-com-validacao/) | D11a-h (8) | pipeline staged + standalone | **08+09 unificado**: 7 fases sub-segmentadas por dataset + 3 checks de validacao | 8/8 |
| 11 | [`11-escape-dedutivel/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/11-escape-dedutivel/) | D11a-h (8) | smart_encode + smart_decode | **Escape dedutivel** (Track 2 L06): remove `\digits` onde valor fora de [1, count]. TOTAL 319->269 bytes (**-15.7%**) | 8/8 RT |
| 12 | [`12-templated-marker/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/12-templated-marker/) | D11c, D11g, **D11i** (novo, mensal com correcao de dia) | template `??` no marker + deltas sem sufixo de escala | D11c=18, D11g=34, D11i=36 (vs v2: 18.9/30.9/80.0%) | 3/3 RT |
| 13 | [`13-tz-aware-pretx/`](experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/13-tz-aware-pretx/) | **D11j/k/m** (novos: tz constante `Z`, constante `-03:00`, variavel) | detect tz constante -> extrai pro template; variable -> no-op | D11j=28, D11k=33 (vs v2: 26.9/30.3%); D11m=105 (fallback, igual v2) | 3/3 RT |

### Linguagem das escalas (v2 cumulativa apos sub-exp 08)

| Sufixo | Significado | Valida em granularidade |
|---|---|---|
| (sem letra) | unidade base detectada em A | sempre |
| `Y` | ano | sempre |
| `M` | mes (capital pra distinguir de minuto) | sempre |
| `D` | dia | second, ms, us, ns |
| `h` | hora | second, ms, us, ns |
| `m` | minuto | second, ms, us, ns |
| `s` | segundo | ms, us, ns |
| `ms` | milissegundo (multi-char) | us, ns |
| `us` | microssegundo (multi-char) | ns |
| sinal `-` | explicito pra negativos | sempre |

Parser **longest-first** pra distinguir `1ms` de `1m`.

### Pipeline staged (canonical apos sub-exp 04)

```
linhas brutas
    ▼ stage A: identify -> meta {type, format, granularity}
    ▼ stage B: normalize_to_unit -> [base, deltas em unidade base]
    ▼ stage C: optimize_scales -> [base, deltas com escala onde exato]
    ▼ TCF.encode (OBAT + HCC)
bytes
```

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
| EXP-014-tpch-lineitem-scale | Performance scale lineitem (1k-20k). Pre-ADR-0009: O(N^1.75) / 71min full. **Pos-ADR-0009: O(N^1.42) / 18.5min full.** RT 4/4 OK | concluido |

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

## Proximas direcoes registradas

Pipeline T01 incremental cobre **toda a hierarquia temporal**
(ano → ns) com 13 sub-experimentos. Self-containment validado em
todos. 3 sub-exps mais recentes:

- **11 escape dedutivel**: remove `\digits` redundantes
  (-15.7% em 8 datasets, principio materializacao minimal)
- **12 templated marker**: `??` no template + deltas sem sufixo de
  escala (-30-80% vs v2 em 3 datasets). Sintaxe `??` ilustrativa
  (engenhoca): preserva format hint (2-char zero-padded).
- **13 tz-aware pretx**: tz constante extraida pro template (-75%
  vs v2 nos 2 casos constantes); variavel cai em fallback no-op.

Proximas opcoes:

1. **Documentar `conclusoes_T01.md`** e fechar T01, abrir T02
   templated (CPF/UUID).
2. **Estudos OBAT/HCC (Track 2)** — L06 escape dedutivel ja' tem
   prototipo dirty; outras camadas (L01-L05) tambem podem abrir.
3. **Welding escape dedutivel + templated marker em src/tcf** —
   requer versionamento do formato + revalidacao D1-D9. Adiar.
4. **Outra direcao**.

---

## Status do repo (commits locais nao pushados)

Cronologico recente:
- (todos os commits T01 sub-exps 03/04/05/06)
- `e668b3b` — diretriz dados realistas + plano atualizado (pushed)
- `d644789` — sub-exp 01 (pushed)
- `b49ac53` — fix bug src/tcf HCC RLE (pushed)
- `9373012` — EXP-008 inicial (pushed)
- `f7ae71f` — D10-D15 + README (pushed)

Sub-exps 03-06 + reorg dirty: locais, **nao pushados** ainda.

---

## Discipline de manutencao

Este arquivo deve ser **atualizado**:
- Ao fechar sub-experimento (status table)
- Ao tomar decisao estrutural (estrutura de pastas, ticket aberto/fechado)
- Ao mudar foco de natureza (T01 -> T02 etc.)

Se editar, lembrar: **status absoluto, nao incremental**. Substituir
o que mudou, manter o resto coerente.
