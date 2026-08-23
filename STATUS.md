# STATUS — TCF

**O estado VIGENTE.** Este arquivo diz o que É, não o que foi (invariante **I1** do
[`AGENTS.md`](AGENTS.md) §0: a superfície carrega só o presente). A história vive no **git**,
no [`CHANGELOG.md`](CHANGELOG.md), nos [ADRs](docs/adr/README.md) e no diário
(`experiments/lab/dirty/notas/diario/`).

> Até 2026-08-23 este arquivo acumulava um bloco `⚑ SOLDADO <data>` por sessão, e nada saía:
> 1083 das 1523 linhas eram histórico empilhado antes da primeira seção — o erro que a própria
> I1 nomeia (*append-only* aplicado à superfície). Nada se perdeu: cada bloco corresponde a
> commits, ADR e diário.

## Agora

| | |
|---|---|
| **publicado** | `tcf-format 0.8.0` no PyPI (23/08, via Trusted Publishing) · tag `v0.8.0` |
| **formato** | `#TCF.8` default — `.8M` multi-col · `.8H` hierárquico · rota tipada · single-col |
| **ciclo aberto** | **`.9`** — otimização **e** integração com armazenamento |
| **números vivos** | nos TESTES, não aqui: `pytest -q` |
| **gates** | `test_regression_v1_baseline.py` (D1-D9, D17a) + `test_real_world_snapshots.py` — os dois obrigatórios (§4) |

A superfície pública está **congelada por teste**: assinaturas de `encode`/`decode` e a lista
de exports em `tests/test_regression_v1_baseline.py`. Mudar exige re-pin deliberado.

## Em curso — o `.9`, dois eixos

- **desempenho e bordas** — [`T-PERF-BORDAS-E-MODOS-09`](tickets/T-PERF-BORDAS-E-MODOS-09.md):
  o eixo quente é **cardinalidade**, não volume; o alvo é o **encode** (o decode já é rápido);
  os modos rápido/normal/máximo nunca foram testados.
- **armazenamento e ecossistema** — HDFS/Parquet, composição de compressão, leitura com
  índice. **O trilho já existe e não é novo**: `O-FMT-20` (registro-'0'/schema-declare para
  append e conversão a parquet, com **index sidecar `.tcfx`**) em
  [`futuras-otimizacoes-formato.md`](experiments/lab/dirty/notas/2026-05/futuras-otimizacoes-formato.md),
  e **H-QUERY-04** (design de índices, 2026-06-17) — princípio já decidido: *derivável >
  {in-file inerte / sidecar `.tcfx`} > formato*, e a escolha é **por perfil de uso**
  (transmissão sem índice; at-rest index-on-arrival).

Fila completa: [`tickets/README.md`](tickets/README.md) · [`ROADMAP.md`](ROADMAP.md).

## Onde achar o quê

| pergunta | fonte |
|---|---|
| o que mudou entre versões | [`CHANGELOG.md`](CHANGELOG.md) |
| por que se decidiu assim | [`docs/adr/README.md`](docs/adr/README.md) |
| o que está aberto | [`tickets/README.md`](tickets/README.md) |
| como usar | [`docs/`](docs/) · [`README.md`](README.md) |
| regras de trabalho | [`AGENTS.md`](AGENTS.md) — comece pela **§0** |
| onde fica cada coisa | [`MAP.md`](MAP.md) |
| a narrativa de uma sessão | `experiments/lab/dirty/notas/diario/` (fora do git desde 22/08) |

## Escala de verificação (decisão de processo, vigente)

**E0** ingênuo · **E1** round-trip · **E2** assimetria · **E3** fail-loud barato ·
**E4** canonicidade · **E5** adulteração ("homem no meio").

**`.8` = E1/E2 obrigatórios + E3 (custa zero) + E4 quando trivial. `.9` = E4
sistemático + E5 opt-in.** Evidência: **4 dos 6 bugs catastróficos do ciclo eram
E1/E2** — os únicos alcançáveis por `encode→decode`. Orçamento de auditoria vai pra
round-trip e assimetria, não pra wire escrito à mão. Ressalva do próprio `malloc`:
ele não pré-verifica, mas devolve `NULL` — E3 fica no `.8` porque falhar CORRETAMENTE
custa zero no caminho feliz.

Detalhe + classificação das 17 checagens do bN:
[`escala-de-verificacao-e-fechamento-do-bn`](experiments/lab/dirty/notas/2026-08/2026-08-07-escala-de-verificacao-e-fechamento-do-bn.md).


## TCF em um parágrafo

**TCF** (Tabular Compact Format) comprime dados **tabulares e aninhados** para **texto ASCII
inspecionável**: o que se repete vira referência, o que é único fica cru (sem inflar). O motor é
**OBAT** (Online Bidirectional Affix Tokenizer) + **HCC** (Hierarchical Compositional Coding),
com camadas que competem num `min()` **nunca-pior** por coluna — fallback raw, dicionário, split
estrutural, polaridade, bN de domínio, seq-RLE. Round-trip é o contrato: **ou preserva byte a
byte, ou falha alto**. Sem dependências de runtime.

Formato vigente `#TCF.8` ([ADR-0032](docs/adr/0032-tcf8-default-format.md)); pacote
`tcf-format 0.8.0`. Pré-1.0 ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)): os
minors são iterações de desenvolvimento, **sem compatibilidade rígida entre eles** — versão
antiga se recupera pelo git. O congelamento definitivo é ato do 1.0.

Detalhe do formato: [`docs/algorithms/TCF-format.en.md`](docs/algorithms/TCF-format.en.md).

## Datasets ativos

### Canonical (`datasets/canonical/` — metadata+sample no git, dados reais em Z:)
| Dataset | Tipo | Volume | Nota |
|---|---|---|---|
| adult-census | real (UCI) | 48842 | single-table mixed |
| tpch-sf001 | gerado (DuckDB) | 60k lineitem | SF=0.01, 8 tabelas FK |
| tpch-sf01 | gerado (DuckDB) | 600k lineitem | SF=0.1, ~866k total |
| online-retail | real (UCI) | 541909 | free-text Description, .99 prices |
| beijing-pm25 | real (UCI) | 43824 | sensor decimais, range narrow — **ATENCAO: `Z:/tcf-data/interim/beijing-pm25.db` tem 0 BYTES** (arquivo vazio, sem tabelas; verificado 2026-08-14 na varredura de float). Buraco do corpus, nao erro de leitura |
| wine-quality | real (UCI) | 6497 | features quimicas decimais |
| ibge-municipios | real (IBGE) | 5571 | BR, categoria hierarquica acentuada |
| br-identidades | **sintetico** | 600k | CPF+CNPJ validos, geografia IBGE; vies declarado |
| receita-cnpj | **real non-PII** | 200k | CNPJ Receita; nature CNPJ 40.9% real |

> Gaps de cobertura + roadmap em memoria `project-dataset-coverage-map`
> (free-text longo, IP/UUID, monetary-string, >1M linhas).
>
> **VARREDURA DE FLOAT 2026-08-14** (9 bancos, 23 tabelas, 186 colunas, **31 com float**; classificacao na coluna INTEIRA, nao na amostra): **(a)** float real so' existe em 2 dos 9 bancos — `online-retail` e `wine-quality`; o resto do float e' TPC-H (sintetico) e **conta em dobro** (`sf001` e `sf01` sao o mesmo gerador em escala 10x: 18 das 31 colunas sao a duplicata). Os 4 bancos BR/censo tem **zero** float, inclusive escondido em TEXT (verificado por regex). **(b)** **ZERO notacao cientifica** e **ZERO artefato binario** no corpus inteiro — nenhum `0.30000000000000004` em lugar nenhum; fora de `wine.alcohol`, o maximo de casas de QUALQUER coluna e' 6 (`wine.density`). **(c)** `wine.alcohol` e' a UNICA coluna com decimal longo: histograma bimodal com buraco (6413 val em 1 casa, 44 em 2, **nada entre 3 e 12**, 40 em 13-14). Os 40 sao **n/30** — medias/divisoes por 3 exportadas com `%.15g`. **(d)** IDENTIFICADOR que virou float: `online_retail.CustomerID`, 406.829 valores, 100% inteiros, declarado `REAL` — paga um `.0` por valor em qualquer serializacao via `str`; idem `l_quantity`. **(e)** regime **semi-inteiro**: `free_sulfur_dioxide` 99,11% inteira e `total_sulfur_dioxide` 99,55%, com o residuo TODO em `.5`. **(f)** o teste de "money" por casas decimais e' QUEBRADO — `str()` suprime o zero final dos centavos (`45523.10` -> `45523.1`), entao "exatamente 2 casas" trava perto de 0,90 por construcao e **nenhuma** coluna monetaria do corpus passaria de 95%; o invariante real e' **"e' multiplo exato de 0,01"**. Fonte: `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-1745-grafia-fracional-e-escala-com-excecoes/result.md`.

### Synthetic (`datasets/synthetic/`):

### Core TCF (D1-D9) — controle algoritmo
Padroes estruturais (afixos, wrappers). Cobertos pelo TCF-CORE
canonical. Total 2981 raw -> 1523 TCF (51.1%, baseline M10/ADR-0011 pinado
em test_regression_v1_baseline.py; 1615B era M9 antigo). Referenciados em
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

## Tickets

**Fonte unica: [`tickets/README.md`](tickets/README.md)** — o indice e' reconciliado
contra o `status:` de cada arquivo, que e' quem manda.

> Ate' 2026-08-22 esta secao replicava a tabela de tickets aqui, e a copia parou de
> ser atualizada em 2026-06-14: mostrava como OPEN itens fechados havia meses
> (inclusive os dois pre-requisitos de feature-complete do `.8`). Duas superficies
> para o mesmo fato, uma delas apodrecendo — Strata §5, fonte unica por altitude.

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
| EXP-015-tcf-hierarquico-csv-json | Prototipo TCF.8H: JSON<->TCF.8H<->JSON preserva a arvore; CSV nao precisa de hierarquia | concluido |
| EXP-016-bn-familia-bits | Bateria sintetica da familia bN + polaridade: 72 casos / 11 familias, 4 provas por caso (RT estrito, determinismo, nunca-pior, correcao≠bN). **0 falhas**; bN ativa em 52. A lacuna da rota tipada (`regimes-que-perdem.md` §2) FECHOU com o weld do `T-BN-TIPADO` 2026-08-07; 6 casos re-pinados de `recusa` p/ `ativa`, bN ativa em 58 | concluido |

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

## Estrutura de pastas (apos reorg separacao de concerns 2026-06-02)

```
TCF/
├── STATUS.md                        # este arquivo
├── README.md (enxuto v0.6), CHANGELOG.md, CLAUDE.md, MAP.md, AGENTS.md
├── src/tcf/                         # CANONICAL v0.6 (OBAT + HCC + natures + _core/detect.pyx)
├── datasets/
│   ├── synthetic/                   # D1-D17
│   ├── canonical/                   # 9 datasets (metadata+sample; dados em Z:)
│   └── samples/                     # fixtures committed (real-world gate)
├── llm-benchmark/                   # benchmark LLM v0.5 (ACESSORIO) — harness eval/ + scripts/
├── old/tcf/                         # motor v0.5 niveis L0-L3, congelado (LEVELS-REVIEW.md)
├── docs/
│   ├── algorithms/ adr/ theory/ how-to/ tutorials/   # v0.6 (Diataxis)
│   ├── findings/                    # catalogo cientifico v0.5 LLM (historico, FICA aqui)
│   └── archive/                     # v0.5/v0.1 congelado
├── tickets/                         # planejamento markdown (YAML frontmatter)
├── experiments/
│   ├── lab/{clean,dirty}/           # labs v0.6 (dirty/old/ = M0-M14 + welded + refuted)
│   ├── results/ scratch/            # output LLM (gitignored)
└── tests/                           # suite v0.6 + fixtures
```

---

## Proximas direcoes (ordenado por prioridade)

### Prioridade alta (caminho feliz)

1. ~~**H-DA-07 revalidacao real-world**~~ (FEITO 2026-05-22,
   T-REVAL-H-DA-07: CONFIRMADA)
2. ~~**H-PERF-05d counter incremental HCC**~~ (FEITO 2026-05-23,
   validated-with-byte-divergence; welding adiado)
3. ~~**Pacote 5 T03 enumerated**~~ (TESTADO 2026-05-23: NO-GO,
   M10 ja' captura via dedup+seq-RLE)
4. ~~**H-DA-09c/d/e** refinos detect_cadence~~ (TESTADO 2026-05-23:
   NO-GO, thr 0.7 ja' otimo; 09d/e adiados)
5. ~~**H-FIX-01/02/03** Pacote 3 parser robustness~~ (FEITO 2026-05-23:
   ADR-0007 ACCEPTED + WELDED, H-FIX-03 win via Opcao B separator)
6. ~~**T-DOC-1/2 + T-CLEAN-1**~~ (FEITO 2026-05-23: CITATION.cff,
   ADR-0012, .pre-commit-config.yaml)
7. **H-PERF-06 Cython/Rust port** — adiado, requer build system
8. ~~**Naturezas raras** (#5 range, #8 arredondamento)~~ (TESTADO
   2026-05-23: NO-GO em datasets gerais; #8 -4.45%, #5 +1.08%)
9. ~~**Multi-column scaling** — EXP-011 base, expansao futura~~ (FEITO
   2026-05-23 com Fase 4 lineitem + WELDED canonical: T-EXP-MULTI-COL-SCALING
   port M10 + 9 tabelas real-world + src/tcf/multi.py via ADR-0013;
   API publica encode_table/decode_table; 17/17 tests novos)
10. ~~**CI** — GitHub Actions com pre-commit + tests~~ (FEITO COMPLETO
    2026-05-23: T-CI-1 lint + T-CI-2 tests refactor + job test ativo)
11. ~~**T-CI-2** — refactor tests CI-friendly~~ (FEITO mesmo dia)

### Prioridade media (decisao pendente)

0. **⛔ bN-dense no FLOOR — COMO entrar (owner decide)**: (a) ligado por
   padrao + re-pin D17a/real-world com ADR, ou (b) atras de flag desligado
   (`fallback_bn=False`). Plano pronto, escopo multi-col `.8M`, marcador `#`
   ja' reservado no registry, nunca-pior por construcao (entra no `min()`).
   Ganho medido: tabela real 1.86x menor; mas gzip encolhe e N pequeno anula.
   Ver bloco ⚑ no topo + labs `2026-07-23-1857` (v2) e `-1832`. **Nada em
   `src/tcf` foi tocado.**
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

### Aberto/pendente apos sessoes 2026-05-30..06-02

- **T-SHAPER-CODE-HARDENING** (P2) — hardening shaper p/ >100k linhas
  (A1 filter-before-load destrava escala; A3/A4/A6). Nao bloqueia <=100k.
- **T-DATA-3-EDGE-QUALITY-FIXTURES** (deferred) — plano de dados de borda;
  bloqueado por T-RECOVER-SCHEMA-MULTI-TABLE (gadget de qualidade nao existe).
- **Roadmap v2.0** (ADR-0018) — format changes p/ naturezas raras reais
  (low-card padding, fallback identity); requer mudanca de formato.
- **Datasets gaps** (project-dataset-coverage-map) — free-text longo real,
  IP/UUID, monetary-string, >1M linhas, geo lat/lon.
- **CNPJ gate forte** — nature CNPJ e' confirmada-empirica com 1 fonte real;
  N>=5 fontes diferentes p/ confianca Alta (so' se quiser fortalecer claim).
- **Spin-off llm-benchmark/** — extrair p/ repo separado via git filter-repo
  quando a fronteira estabilizar (futuro, so' se owner quiser).
- **Fases parciais T-CODE** — ENCODER-MANAGER (1c/2-4), SCHEMA-BUILDER
  (Fase 3 naturezas), LAYERED-PIPELINE (Fase 2 online adaptive),
  OUTPUT-SINKS/PLAN-CONTRACT (bloqueados).

---

## Discipline de manutencao

Este arquivo deve ser **atualizado**:
- Ao fechar sub-experimento (status table)
- Ao tomar decisao estrutural (estrutura de pastas, ticket aberto/fechado)
- Ao mudar foco de natureza (T01 -> T02 etc.)

Se editar, lembrar: **status absoluto, nao incremental**. Substituir
o que mudou, manter o resto coerente.
