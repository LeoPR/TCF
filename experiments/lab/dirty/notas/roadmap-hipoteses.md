# Roadmap de hipoteses — TCF v0.6 (cross-lab)

**Criado**: 2026-05-17

`[VERIFICAR: 2026-08-18]` — revisar status de cada hipotese aberta:
ainda relevante? testada? promovida pra ADR? Atualizar tabela.
**Proposito**: registro **central** de toda hipotese identificada nos
dirty labs. Nenhuma e' descartada. Cada uma e' candidata a:
1. Teste isolado em dirty lab proprio (ablacao)
2. Mistura controlada em dirty lab de combinacao (apos isoladas)
3. Inclusao no prototipo clean (resistencia + escala)

**Regra**: hipotese descoberta durante experimento de outra natureza
e' **registrada aqui** (nao misturada no experimento corrente). Apos
fechamento de pacote, decide-se ordem de exploracao isolada/combinada.

## Convencao de status

- `aberta` — identificada, ainda nao testada
- `em-exp` — sub-exp ativo testando
- `confirmada-empirica` — validada empiricamente em datasets
  testados (NAO implica generalizacao); ref ao lab/sub-exp
- `confirmada-conceitual` — alem do empirico, passou revisao
  conceitual (ressalvas explicitas)
- `refutada` — testada e nao funciona (motivo + ref)
- `refutada-parcial` — funciona em alguns cenarios, falha em outros
- `refutada-real-world` — funciona em sintetico mas NAO generaliza
  pra real-world (introduzido 2026-05-21 apos Pacote 2)
- `adiada` — fora de escopo do momento, retomar depois
- `absorvida` — incorporada em hipotese maior
- `subsumida` — coberta por outra hipotese mais geral
- `welded` — implementada em src/tcf canonical (referencia ADR)

## Convencao de evidencia (introduzida 2026-05-21)

Apos revisao conceitual (ver `revisao-conceitual-2026-05-21.md`),
toda hipotese **confirmada-empirica** deve carregar 3 campos
adicionais:

- **`evidencia_realworld`**: "Adult-1k/5k", "TPC-H-customer-5k",
  "lineitem-60k", "(none — so sinteticos)", "(via pipeline EXP-XXX)"
- **`n_datasets_diversos`**: numero de datasets de fontes diferentes
  (sinteticos contam separado de reais)
- **`confianca`**: `Alta` | `Media` | `Baixa` | `A-revalidar`

Tabela resumida em `revisao-conceitual-2026-05-21.md` (categoria
A/B/C). Re-validacao urgente: H-DA-01, H-DA-06, H-DA-10 (categoria B).

## Disclaimer importante — empirico vs conceitual

Hipoteses marcadas `confirmada-empirica` foram validadas nos
**datasets testados**. Generalizacao pra outros dados **nao e'
automatica**.

Datasets D11a-h foram **construidos** pra testar cadencia (sintese,
nao realidade). Resultados confirmando "ganho em cadencia" podem
refletir o teste, nao a realidade.

Datasets D16a-c foram **criados** pra este lab. Pequena amostra,
nao representam todo o universo de IDs numericos.

**Caso documentado de nao-generalizacao** (2026-05-21):
Pacote 2 (escape deduction H-ED-01..04) deu 15.7% em D11a-h
sinteticos mas apenas 0.13-1.13% em real-world (Adult Census +
TPC-H). Fechado `CLOSED-INSUFFICIENT-GAIN`. Confirma necessidade
de testar SEMPRE em real-world antes de declarar generalizacao.

**Revisao conceitual feita 2026-05-21**: ver
[`revisao-conceitual-2026-05-21.md`](revisao-conceitual-2026-05-21.md)
pra classificacao A/B/C de todas as hipoteses confirmada-empirica.

---

## Pacote 1 — Delta-aware (lab `2026-05-17-OBAT-delta-aware`)

**Status do pacote**: cobertura empirica inicial completa (8 sub-exps).
**Revisao conceitual pendente** — generalizacao pra dados real-world
nao testada.

Foco: redutir bytes quando ha' cadencia regular detectavel
(datas como exemplo).

| ID | Hipotese | Status | Onde | Ressalvas conceituais |
|---|---|---|---|---|
| H-DA-01 | OBAT esta quase pronto (quebra ja' isola variacao; HCC sozinho agrupa) | **confirmada-empirica-marginal** -22.2% sint; -1.36% real (16.3x reducao); SELETIVAMENTE potente em colunas com cadencia (c_custkey -92%, c_name -44%) | `02-hcc-sozinho-rle-near-identical/result.md` + `2026-05-21-revalidacao-categoria-B/02-h-da-01-hcc-seqrle-realworld/result.md` | Confianca: A-revalidar. Real-world weighted 1.36% < 5% threshold, MAS ja' welded em EXP-010 + ativacao via auto-detect (gating via H-DA-09b-v2) |
| H-DA-02 | Pre-stage pode gerar dica generica (sem nomear tipo) que calibra OBAT | **subsumida** em H-DA-07 (nao testada isoladamente) | — | Sub-hipotese de H-DA-07, nao validada como pergunta separada |
| H-DA-03 | OBAT pode fazer comparacao relativa (`+N` abstrato) sem nomear unidade | **subsumida** em H-DA-07 (nao testada isoladamente) | — | Idem |
| H-DA-04 | Recuperacao apos transicao de cardinalidade (`\\9` → `\\10`) | **refutada-parcial** (so' com refs ao redor; sem refs ja' funciona) | `03-cadence-break-recovery/result.md` + refinamento em `05-numeric-ids-h-da-06/result.md` (D16a) | Conclusao deriva de auditoria; nao de implementacao completa |
| H-DA-05 | Linhas pos-transicao podem formar novo run se OBAT mantiver alinhamento | **absorvida** em H-DA-07 | confirmada via H-DA-07 | — |
| H-DA-06 | Outros tipos de delta (numerico IDs, signed, step != 1) | **subsumida em H-DA-09b-v2** (welded ADR-0008); cobertura 87.5% das numeric+high-card real-world | `05-numeric-ids-h-da-06/result.md` + `2026-05-21-revalidacao-categoria-B/01-h-da-06-subsumida-em-09b-v2/result.md` | Confianca: Alta (subsumida). H-DA-09b-v2 captura colunas-alvo de H-DA-06 em real-world via regra 2 (numeric+cardinality > 0.5) |
| H-DA-07 | OBAT shape-preserve via dica generica | **CONFIRMADA real-world** (revalidada 2026-05-22, T-REVAL-H-DA-07): gating detect_cadence preserva neutralidade em 62/66 cols real-world; 2 wins enormes (c_name -98.19%, D9 -48.03%), 2 losses pequenas (l_extendedprice +0.65%, c_acctbal +0.20%); welded canonical via Pacote 1 ADR-0011 | `04-...` + `06-...` + `2026-05-22-h-da-07-shape-preserve-revalidacao/01-medicao-on-off/` | Confianca: **Alta**. Welded canonical em src/tcf via Pacote 1 (ADR-0011). Gating funciona corretamente em real-world |
| H-DA-08 | Detector que aceita per-run delta encoding | **refutada** (9 bytes total) | `07-per-run-delta-audit/result.md` | Audit em datasets D11+D16 apenas; outros datasets podem ter perfil diferente |
| H-DA-09 | Pre-stage infere hint automaticamente (always-on) | **refutada** | `06-auto-hint-regression-D1-D9/result.md` | "Always-on" e' a forma mais ingenua; refuta especificamente essa forma |
| H-DA-09b | Auto-detect cadencia via heuristica (length uniformity, LCP stability) | **confirmada-empirica** (-18% total em 20 datasets vs always-on -5.5%) | `09-auto-detect-cadence-heuristic/result.md` | 18/20 acertos; perdeu -14B em D1 e -20B em D11b (lengths variavel). Threshold 0.7 e' arbitrario. |
| H-DA-09b-v2 | Refino real-world: regra adicional numeric+high-cardinality | **CONFIRMADA** (real-world -5.6% adicional, -135,638B em Adult+TPC-H) | `2026-05-19-h-da-09b-refino-real-world/` + ADR-0008 | RT 12/12 OK; captura 12/12 HELP (era 4/12); zero regressao multi-camada |
| H-DA-09c | Tunar threshold da heuristica (0.5..0.8) | **refutada** 2026-05-23: thr 0.7 ja' otimo (0.5/0.6 dao -3.06% regressao real-world; 0.8 idêntico) | `2026-05-23-h-da-09c-d-e-refinos-cadence/01-h-da-09c-threshold/` | T-EXP-H-DA-09c-d-e NO-GO |
| H-RW-05 | Encode tem complexidade quadratica O(N²) | **CONFIRMADA na pratica** (lineitem full 60175 = 21.3min real vs 18.5min estimado, +15%) | EXP-014 + EXP-014 run_full.py (2026-05-20) | RT OK, ratio 89%, 21.2ms/k rows. Mitigacao via ADR-0009. |
| H-PERF-01 | `_melhor_pref` + `_melhor_suf` dominam tempo (>60%) | **confirmada-empirica** (74% em lineitem 5k) | `2026-05-19-obat-perf-optimization/01-profile-baseline/` | cProfile mostrou 191.6s/258.6s. 29M chamadas `lcp_len`/`lcs_len`. 216M `len()` calls. |
| H-PERF-01b | HCC `_detect_compositions` e' o 2o hotspot (>20%) | **confirmada-empirica** (24% em lineitem 5k) | mesmo profile | Nao previsto. Mesmo otimizando OBAT 10x, HCC vira gargalo se nao for tratado. |
| H-PERF-02 | Hash de prefixos/sufixos por bigramas reduz OBAT a O(N) amortizado | **CONFIRMADA + WELDED** (v3, alpha 1.75→1.42, 2.70x em 20k) | `2026-05-19-obat-perf-optimization/` + ADR-0009 | Trigrama (k=3). RT 33/33 OK em D1-D9 + lineitem 1k+5k. Re-val multi-camada zero regressao. Lineitem full 60175 71→18.5min. |
| H-PERF-03 | Eliminar `len()` redundantes via passagem de `len_a`/`len_b` cortar 10-20% | **CONFIRMADA empirica parcial** (v1 = 1.3x) | mesmo sub-exp | Sem hash, ganho modesto. Absorvida em H-PERF-02 welded (idiom embutido). |
| H-PERF-04 | Trigrama de meio dispersa buckets em colunas datetime | **ADIADA (refutada-parcial conceitual)** | `2026-05-20-obat-perf-phase2-trigram-middle/01-profile/` | Profile confirmou max bucket 240x menor com combined_full, MAS hash tradicional nao preserva byte-canonical em datas com prefix popular. Solucao precisaria Patricia trie (out of scope agora). Decisao opcao A: focar H-PERF-05. |
| H-PERF-05 | Otimizar HCC `_detect_compositions` (24% tempo restante) | **investigada-parcial (zero-risk insuficiente)** | `2026-05-20-hcc-perf-optimization/` | Profile confirmou 75% encode. 6 sub-variantes testadas: zero-risk (counting direto, skip trace) so' 1.04x; caps trazem byte loss (3-6%). Counter incremental nao testado (complexo). Decisao: adiar; OBAT (ADR-0009) ja' destrava Pacote 4. |
| H-PERF-05a | Cache `_estimate_baseline_chars` (sub, comp_acc_k) | **adiada** | analise teorica sub-exp 01 | Cache hit baixo (comp_acc_k muda cada iter). Pouco promissor. |
| H-PERF-05b | `_estimate_baseline_chars` counting direto (sem list+join+len) | **CONFIRMADA empirica MARGINAL** (1.03x, bytes IDENTICOS) | `2026-05-20-hcc-perf-optimization/02-prototipos-zero-risk/` | Zero-risk mas ganho minimo (Python ja' otimiza bem list+join). Nao vale welding. |
| H-PERF-05c | Skip `_build_trace`/`_build_rede` (dead code em pipeline) | **CONFIRMADA empirica MARGINAL** (1.04x cumulativo com 05b) | mesmo sub-exp | Zero-risk. Ganho ~0.4s em lineitem 5k. Nao vale welding. |
| H-PERF-05d | Counter incremental (re-conta so' partes afetadas) | **validated-with-byte-divergence (welding adiado)** 2026-05-23: prototype IncrementalSyntax funciona em 37/41 cols byte-canonical; 4 divergencias em datetime TPC-H (+62B / ~80kB = 0.08%) por ordem de iteracao Counter | `2026-05-22-h-perf-05d-counter-incremental/` (T-EXP-H-PERF-05d) | Profile confirma GO (rebuild=46% _dc). Fix byte-canonical requereria reinsert posicional custom (complexo); aceitacao M11 quebra invariant M10. Adiado. |
| H-PERF-05e | Cap K maximo de sub-tupla (K=4/6/8) | **refutada-parcial** | `2026-05-20-hcc-perf-optimization/03-prototipos-cap-K-iter/` | K=8/6 PIOREARAM tempo (overhead check). K=4 deu 1.11x com +0.05% loss. Marginal. |
| H-PERF-05f | Cap iter_traces (50/30 vs 99) | **refutada (trade-off ruim)** | mesmo sub-exp | i=50: 1.37x/+3.44% bytes; i=30: 1.71x/+5.58% bytes. Viola regra invariante M9 ("zero loss"). |
| H-PERF-06 | Cython/Rust port de `lcp_len`/`lcs_len` corta Python overhead | aberta | nao testada | 29M chamadas em lineitem 5k, ~1.7us/chamada. Compilado podia cortar 50%+. |
| H-DA-09d | Heuristica multivariada (lengths + LCP+LCS + variance) | **adiada** 2026-05-23 (H-DA-09c refutada; heuristica atual bem calibrada) | nao testada | T-EXP-H-DA-09c-d-e adiou 09d/e |
| H-DA-09e | Re-avaliar heuristica a cada N strings (adaptativo) | **adiada** 2026-05-23 (idem H-DA-09d) | nao testada | idem |
| H-DA-11 | Auto-detect de min_len otimo por coluna pode capturar ~10% ganho weighted real-world | **WELDED canonical src/tcf** (ADR-0010 — **9.87% real-world weighted** em Adult+TPC-H 57 cols) | `2026-05-21-h-da-11-auto-min-len/` (sub-exps 01-05) + ADR-0010 + `src/tcf/auto_min_len.py` | Confianca: **Alta**. **M9 baseline 1615B EXATO preservado**, RT 100% (D1-D9 9/9 + real-world 57/57). Heur v3 com gating n>=100. Top wins: l_comment -29kB, fnlwgt -22kB, l_extendedprice -20kB |
| H-DA-10 | min_len trade-off existe e pode ser ajustado por dataset | **CONFIRMADA real-world** (9.92% weighted gain em 14 colunas reais Adult+TPC-H; ate -36.78% em fnlwgt; -28% em l_extendedprice) | `08-min-len-trade-off/result.md` + `2026-05-21-revalidacao-categoria-B/03-h-da-10-min-len-realworld/result.md` | Confianca: **Alta** (real-world testado). Generalizou MELHOR que sintetico. Default min_len=3 nao otimo. Hipotese decorrente: H-DA-11 (auto-detect min_len por coluna) |

## Observacoes empiricas (NAO hipoteses — pendentes de teste conceitual)

Achados que pareceram interessantes durante experimentos mas que
podem ser **artefatos do teste**, nao fenomenos reais. Antes de
virar hipoteses, precisam de teste conceitual: replicar em
dataset independente, verificar mecanismo de causalidade.

| ID-obs | Observacao | Origem | Necessario pra promover |
|---|---|---|---|
| O-01 | H-DA-07 deu -58% em D9 wrapper pattern | sub-exp 06 | Testar em outros datasets wrapper-like; N=1 atual |
| O-02 | H-DA-07 deu +72% em D5 mixed patterns | sub-exp 06 | Testar em outros datasets mistos; verificar se sempre piora |
| O-03 | min_len > 3 ajuda em D9 (-33B com min_len=5) | sub-exp 08 | Testar em outros wrapper datasets; verificar correlacao com tamanho de string |
| O-04 | D16a com seq-RLE puro deu -83% sem precisar OBAT cooperar | sub-exp 05 | Testar em outros datasets onde OBAT nao cria refs |

## Pacote 3 — Robustez do parser HCC canonical

**Status do pacote**: planejado (aguardando aprovacao do plano).
Origem: EXP-013 TPC-H revelou bug `,` em literais; ADR-0006 fixou
2 bugs (empty-string + whitespace); bug 3 (`,`) requer analise.

| ID | Hipotese | Status | Onde |
|---|---|---|---|
| H-FIX-01 | Escape de `,` em `_escape_lit` resolve bug e preserva M9 | **refutada (Opcao A perde pra Opcao B)** — sub-exp 04: +116B em c_comment vs +7B Op B | `2026-05-18-canonical-parser-robustness/02-opcao-A-escape-virgula/` | Funcional mas overhead maior; Op B preferida |
| H-FIX-02 | Mesma opcao mas re-baseline M9 necessario (D1-D9 tem `,`) | **N/A** (Op A nao escolhida) | — | — |
| H-FIX-03 | Separator heuristico `*` antes de literal ambiguo (encoder-only) | **WELDED canonical** (ADR-0007 accepted) — 10/10 casos minimos OK (era 7/10), M10 1523B preservado, RT 100% real-world | `src/tcf/composicional/syntax.py:435-442` + `2026-05-18-canonical-parser-robustness/05-validar-welding-canonical/` | Confianca: **Alta**. Welded 2026-05-19 (sem doc na epoca); validado + ADR-0007 finalizado 2026-05-23 |

Plano completo: [ADR-0007](../../../docs/adr/0007-comma-in-literals-bug.md)
+ lab dirty `2026-05-18-canonical-parser-robustness/`.

## Pacote 2 — Escape / supressao implicita (ortogonal)

Foco: reduzir overhead de marcadores de escape (`\digits`, `\*`,
`\\`, `\~`) quando contexto permite deducao.

**Origem**: identificada em 2026-05-17 ao revisar body fork da
tentativa 02 (linhas 1 dos D11a-h tem 7-10 backslashes cada). Nao
e' especifico a delta — afeta qualquer body. Antecedente: ticket
`docs/workbench/_archive/tickets/open/S-supressao-implicita-marcadores.md`
(2026-05-10, v0.5 era).

| ID | Hipotese | Status | Onde |
|---|---|---|---|
| H-ED-01 | Linha 1 do body nunca tem refs → digits sao sempre literais → escape `\` redundante | **refutada-real-world** (0.01% ganho weighted) | `2026-05-21-escape-deduction/01-caracterizacao-escapes/` |
| H-ED-02 | Apos `*` separador, proximo nao-digito-de-ref tem contexto deduzivel | **refutada-real-world** (0.12% ganho weighted) | mesmo sub-exp |
| H-ED-03 | Escape de `*`, `\`, `~` pode ser inferido por posicao em alguns casos | **refutada-real-world** (zero ops escapes em real-world testado) | mesmo sub-exp |
| H-ED-04 | Header da coluna (ex: "tipo=numerico") permite supressao adicional | **adiada** (nao testada, dependeria de H-ED-01..03 funcionar) | — |
| H-ED-original | Digit-run valor > current count → literal deduzivel | **refutada-real-world (lower bound)** (1.13% ganho weighted vs criterio 5%) | mesmo sub-exp |

**Quantificacao rapida (sem mexer)**: ~50-60 backslashes na linha 1
dos 8 datasets D11a-h. Se ~50% deduzivel → ~25-30 bytes potenciais.
Cumulativo (nao ortogonal medivel diretamente) com H-DA-01.

## Pacote 3 — Outras hipoteses identificadas (registradas em outros docs)

Estas ja' existem em outros docs; replicadas aqui pra centralizar.

### Pre-tx por natureza (lab `2026-05-15-naturezas-e-camada`)

| ID | Hipotese | Status |
|---|---|---|
| H-PT-01 | Pre-tx incremental/delta antes do OBAT | refutada parcial (multi-pass viola vertice triplice) — ver `T01-v2-critica-e-direcao.md` |
| H-PT-02 | Pre-tx tz-aware (separar timezone do timestamp) | confirmada — sub-exp 13 do T01 |
| H-PT-03 | Pre-tx unit normalization (ms/us/ns → unit + count) | confirmada — sub-exp 09 do T01 |

### Teoria (memoria do user, sem labs ativos)

| ID | Hipotese | Status |
|---|---|---|
| H-TH-01 | Quebra de linha como marcador (nao estrutura inviolavel) | adiada |
| H-TH-02 | Indice incremental de padroes (Patricia generalizada) | adiada |
| H-TH-03 | Comparacao modular em camadas (pre-tx delta / estrutural / aproximado ortogonais) | adiada |

## Pacote 7 — Templated / Checksummed / Lossy (registrado 2026-05-24)

**Origem**: brainstorm 2026-05-24 do owner, catalogado em
[`naturezas-templated-2026-05-24.md`](naturezas-templated-2026-05-24.md).
Estende T02 (Templated) e T04 (Checked) do META-TYPE-ENCODERS.

**Status do pacote**: registrado, **lab nao iniciado**. Reabertura
condicionada a download de datasets dedicados (T-DATA-1) + caracterizacao
real-world (mesmo padrao Pacote 5 enumerated: testar antes de welder).

### Templated puro

| ID | Hipotese | Datasets alvo | Ganho estimado |
|---|---|---|---|
| H-TM-IP4 | IPv4 pre-tx (omit `.` + slots numericos 0-255) | logs com IP (futuro) | -50 a -70% |
| H-TM-IP6 | IPv6 pre-tx (omit `:` + expandir `::`) | logs com IP6 (futuro) | -40 a -60% |
| H-TM-MAC | MAC pre-tx (omit `:` + 6 bytes hex) | logs de rede, IoT (futuro) | -60 a -70% |
| H-TM-CEP | CEP BR pre-tx (omit `-` + 8 digitos) | datasets BR (futuro) | -10 a -15% |
| H-TM-EAN | EAN/UPC pre-tx (delta-aware numerico) | Online Retail StockCode (T-DATA-1) | depende cadencia |

### Templated com pontuacao opcional

| ID | Hipotese | Datasets alvo | Ganho estimado |
|---|---|---|---|
| H-TM-FONE-BR | Telefone BR (detect mascara + extract digits) | CRMs (futuro) | -20 a -30% |
| H-TM-FONE-INTL | Telefone E.164 (composite CC + local) | datasets globais (futuro) | -15 a -25% |
| H-TM-DATA-BR | Data BR (dd/mm/yyyy normalize ISO) | datasets BR (futuro) | -15 a -20% |

### Templated + Checksummed (dual nature)

| ID | Hipotese | Datasets alvo | Ganho estimado |
|---|---|---|---|
| H-TM-CPF | CPF pre-tx (omit `.`/`-` + 2 digits check regen) | D13 CPF, datasets fiscais BR (futuro) | -25 a -30% |
| H-TM-CNPJ | CNPJ pre-tx similar a CPF | datasets fiscais BR (futuro) | -25 a -30% |
| H-TM-TITULO | Titulo eleitor BR (check digits regen) | datasets eleitorais (futuro) | -15 a -20% |
| H-TM-IBAN | IBAN pre-tx (omit espacos + check mod-97) | bancarios EU (futuro) | -10 a -20% |
| H-TM-LUHN | Cartao credito / IMEI (omit espacos + Luhn check) | financeiros (futuro) | -10 a -15% |

### Lossy-recoverable (erro controlado)

Estende #10 de [naturezas-numericas-2026-05-23.md](naturezas-numericas-2026-05-23.md).

| ID | Hipotese | Datasets alvo | Ganho estimado |
|---|---|---|---|
| H-LR-FLOAT-PREC | Float com precisao fixa (round + N casas) | Wine Quality, Beijing PM2.5 (T-DATA-1) | -20 a -40% |
| H-LR-GEO | Coordenadas geo (truncar lat/long pra N casas) | datasets geo (futuro) | -30 a -50% |
| H-LR-MONETARY | Monetario com round automatico (R$ pra 2 casas) | Online Retail UnitPrice (T-DATA-1) | -10 a -25% |
| H-LR-DIST | Erro distribuido (quantize + delta) | sensor data (futuro) | depende noise |
| H-LR-PERC | Percentual aproximado (round) | reports analiticos (futuro) | -10 a -20% |

### Composite (multi-nature por valor)

| ID | Hipotese | Datasets alvo | Ganho estimado |
|---|---|---|---|
| H-CP-DATETIME | datetime ISO decompor em date+time+tz (cada qual sua nature) | D11, TPC-H date cols, logs (futuro) | -30 a -60% |
| H-CP-ENDERECO | Endereco BR (rua+numero+bairro+cidade+UF+CEP) | datasets BR (futuro) | -20 a -40% |
| H-CP-MONEY | Monetario com moeda (currency enum + amount num) | financeiros (futuro) | -10 a -15% |
| H-CP-VERSION | Semver (major.minor.patch + pre + build) | repositorios de pkg (futuro) | -10 a -20% |

### Criterio de reabertura

Pacote 7 abre quando:
1. Owner roda T-DATA-1 scripts -> dados disponiveis em Z:/tcf-data/
2. Sub-exp tipo `01-caracterizacao` mede baseline M10 em datasets-alvo
3. Se ganho potencial >= 15% em 2+ datasets -> abrir sub-pacote (e.g.,
   `2026-MM-DD-pacote7-templated-cpf/`)

Antes disso, **registrado mas adiado**.

---

## Pacote 8 — Deteccao de composicao HCC (registrado 2026-06-14)

**Origem**: owner inspecionou a saida 0.7 do README (coluna de e-mails) e achou
uma composicao perdida. Diagnostico confirmado por trace (SideOutputs) + leitura
de `_detect_compositions`. Exemplo: `diego` = `dieg5,3` (`o` + `@acme.com.br`),
onde `o@acme.com.br` tambem e' o sufixo de `bruno` — logo deveria virar UM
fragmento composto e `diego` ser `dieg5` (ref unica).

| ID | Hipotese | Status | Diagnostico / ref |
|---|---|---|---|
| H-HCC-01 | Detector SUBCONTA recorrencias: conta sub-tuplas so' dentro de pecas `'refs'` (`syntax.py:246-255`), ignorando a ocorrencia de DEFINICAO (onde o atom e' literal). Unidades recorrentes como `o@acme.com.br` (define em `bruno` = lit`o`+ref3; usa em `diego` = ref5+ref3) contam R=1 em vez de R=2 e nao sao compostas. Contar adjacencias de ATOMS (incl. a def-as-lit) pegaria a composicao. | **closed-insufficient-gain (adiado)** 2026-06-14: composicoes perdidas CONFIRMADAS + simuladas com custo dinamico (Re-Pair). Ganho realista **1.30% weighted** (teto), free-text only, **cauda longa** (centenas-milhares de regras, net/rule 0.34-2.10). Risco alto (detector core + gate) p/ ROI baixo -> adiar. | `2026-06-14-hcc-composicao-perdida/dynamic_sim_result.md` |
| H-HCC-02 | **Custo de referencia e' DINAMICO/relativo, nao estatico** (meta-hipotese do owner): conforme composicoes sao montadas, a largura dos ids de ref (`n_tam`) muda e altera o custo das refs SEGUINTES. O modelo atual (`net=(R-1)*(baseline-n_tam)`) avalia cada candidato quase-independente. | **confirmada-conceitual (adiado junto c/ H-HCC-01)** 2026-06-14: a estrutura abstrata E' grammar compression (Re-Pair sobre a sequencia completa de atoms), net em bytes, recontado a cada pick. Simulada (`dynamic_sim.py`, RT OK): modela overlap+width. Resultado abaixo justifica adiar. | `2026-06-14-hcc-composicao-perdida/dynamic_sim_result.md` |

**Sintoma menor (nao a causa)**: referenciar um fragmento de 1 char (`5`=`o`) e'
byte-neutro (1 char ref vs 1 char literal); nao e' dano, e' sintoma da unidade
decomposta em vez de composta.

**Implicacoes de um fix (H-HCC-01)**:
- Muda `_detect_compositions` -> muda body -> **re-pina D1-D9/D17a** (intencional, ADR-0024).
- **GATE obrigatorio**: `tests/test_real_world_snapshots.py` (CLAUDE.md: qualquer
  mudanca no detector). Foi esse gate que pegou prunes que regrediam.
- Respeitar **body-order** dos refs compostos (check `alias_first_line < sub_first_line` ja' existe).
- **Trade-off**: hoje `@acme.com.br` e' compartilhado flat (ref 3x). Compor
  `a@acme`/`o@acme` pode ENFRAQUECER esse sharing. Ganho NAO garantido — medir.

**Caracterizacao** (sub-exp `2026-06-14-hcc-composicao-perdida/`): upper-bound
~1.21% weighted, concentrado em free-text (l_comment 4.5%, ibge municipio 3.8%,
retail Description 2.6%); shareRisk alto nos hotspots -> realizado < upper-bound.

### Decisao final (2026-06-14): ADIAR o weld

H-HCC-01+02 atacadas juntas (como o owner pediu) via `dynamic_sim.py`: Re-Pair
sobre a sequencia completa de atoms, custo dinamico (overlap recontado + width de
id crescente), RT limpo. **Ganho realista 1.30% weighted (teto)**, free-text only,
em **cauda longa** (r@80% = centenas de regras; net/rule 0.34-2.10 chars). Nao ha'
subconjunto barato. Welder no detector core (sob o GATE, com emit de body-order
pra milhares de aliases) por isso = ROI baixo / risco alto -> **closed-insufficient
-gain por ora**. Reavaliar se surgir emit de composicao barato OU caso de uso
free-text dominante. Detalhe: `2026-06-14-hcc-composicao-perdida/dynamic_sim_result.md`.

#### Contexto original do owner (preservado)

**PRATELEIRA: atacar H-HCC-01 JUNTO com H-HCC-02** (nao em duas passadas). Razao:
o estimador de net precisa ser sequencial/dinamico desde o desenho — fazer a
contagem estendida com o modelo de peso estatico atual seria refazer depois.

**Prioridade do owner (afeta criterio do gate)**: ganho em **payload pequeno** da'
vantagem pra certas categorias de transmissao. No pior caso (pessimista), se o
detector dinamico **inflar dados grandes**, o owner **privilegia os pequenos** —
aceita alguma perda em massa pra ganhar no pequeno. Implicacao: o GATE real-world
hoje proibe regressao em colunas grandes (l_comment etc.); essa prioridade pode
**relaxar** isso (minimizar perda grande, priorizar ganho pequeno) — mas SO' como
fallback. **Alvo real**: um detector dinamico INTELIGENTE que ganha no pequeno
**sem** inflar o grande (a "matemagica" abaixo). Nao relaxar o gate por padrao;
so' se o trade-off for inevitavel e medido.

**Abordagem pra H-HCC-02 (dynamic detector)**: capturar a **estrutura abstrata**
do problema (refs/composicoes como grafo + custo de id dependente do estado) e
ver se da' pra modelar o custo de forma que a decisao greedy/otima leve em conta
o tamanho RELATIVO da referencia vs da otimizacao, recalculado conforme as
composicoes sao montadas. Owner: "se ficar isso vai otimizar muito".

---

## Pacote 9 — datetime-nature (registrado 2026-06-14)

**Origem**: caracterizacao do V2-D (strip de afixo, `2026-06-14-v2d-strip-afixo-
caracterizacao/`). V2-D foi refutado (subsumido pelo OBAT, 0.11% weighted), MAS
os unicos ganhos relevantes foram colunas DATETIME: InvoiceDate 15%, data_cadastro
3.5%. O afixo longo de timestamp (`2010-12...:00`) escapa parcialmente do OBAT.

| ID | Hipotese | Status | ref |
|---|---|---|---|
| H-DT-01 | Timestamps merecem encoder proprio. **GENERALIZADO -> H-STRUCT-01.** | subsumida por H-STRUCT-01 | — |
| H-STRUCT-01 | **Split estrutural + V2-B**: tokenizar valores em runs digito/separador; se template uniforme, os grupos de digito viram colunas-campo (template 1x) -> cada campo low-card e' esmagado pelo V2-B. Generaliza decimais, datas, datetimes, CPF/CNPJ. | **WELDED 2026-06-14 (ADR-0026)**: 4o candidato do fallback `min(tcf, raw, dict, split)`, marcador `%`. 19.39% weighted (8 datasets reais). Gate 100% uniforme, sem mecanismo de excecao (refinamento: 1 near-miss em 80 cols). Complementa natures (min). 398 passed, GATE verde. | `2026-06-14-datetime-nature-caracterizacao/` (result + refine_result) |

---

## Pacote 10 — LOSS (lossy), registrado 2026-06-14

**Origem**: owner ampliou o escopo do V2-C: "loss de dados e amplo e e PRO TCF
FAZER SIM". Revisao exaustiva (workflow 9 vertentes + critico) em
**`loss-taxonomia.md`** (eixo principal = CONTRATO de recuperacao). PoC do
maior-resto valida a ideia-chave (soma exata, loss-no-agregado).

**DECISAO DE ESCOPO (owner, 2026-06-15)**: o ciclo **0.7 permanece lossless-puro**.
Lossy NAO entra no 0.7 — vira **roadmap v2.0**. V2-C round-puro (nicho ~1.5%, so'
wine) e' fechado como caracterizacao de referencia, NAO welded. Quando o lossy for
perseguido (v2.0), comecar pela vertente **cross-coluna** (H-LOSS-02,
`valor=soma(parcelas)`, maior teto) e nao por round simples, sob GATE real-world
N>=5 e a meta-camada de contrato (H-LOSS-00) como pre-requisito. Nenhuma das
H-LOSS-* abaixo entra em src/tcf sem nova decisao explicita do owner.

| ID | Hipotese | Status | ref |
|---|---|---|---|
| H-LOSS-00 | **Meta-camada de contrato** (ABS/REL/DECIMALS/AGG/DIST) + marcador inspecionavel no header + teste valida-invariante. PRE-REQUISITO de toda perda. | aberta (prioridade arquitetural) | taxonomia §4 |
| H-LOSS-01 | **Residuo-redistribuido (soma/media/grupo)** — maior-resto/error-diffusion; loss por-linha, soma EXATA. A ideia-chave do owner (parcelamento). | aberta (alta); PoC OK | taxonomia §1a + poc_soma_preservada.py |
| H-LOSS-02 | **Cross-coluna / DERIVED-DROP** — `C=f(A,B)` dropa coluna inteira; lossless se residuo=0, exato-no-agregado se residuo redistribuido. **Mais promissora** (critico). Exige estrutura cross-coluna no formato. | aberta (alta, maior teto) | taxonomia §3 |
| H-LOSS-03 | **Round precisao-fixa** (V2-C): casas/sig-figs. Pedra fundamental do vocabulario lossy; ganho nicho ~1.5%. | caracterizada (nicho pequeno) | `2026-06-14-v2c-lossy-round-caracterizacao/` |
| H-LOSS-04 | **Quantizacao/binning** (codebook k-means + indices, reusa dict V2-B). Domina round a igual erro em dist. concentradas. | aberta (media) | taxonomia §1b |
| H-LOSS-05 | **Truncamento temporal** (granularidade/snap). Melhor ganho/risco datetime; reusa split+cadence+seq-RLE. | aberta (media) | taxonomia §1b |
| H-LOSS-06 | **Lossy categorico/ID** (merge-OUTRAS, hash, remap-ID). Remap-ID = maior teto em UUID/ID opaco; precisa cross-coluna. | aberta (media) | taxonomia §1c |
| H-LOSS-07 | **Lossy texto** (normalizacao, near-dedup fuzzy, stemming). Alert-only via SideOutputs primeiro. | aberta (media-baixa) | taxonomia §1c |
| H-LOSS-08 | **Transformada/modelo+residuo** (regressao/DCT/wavelet/low-rank) p/ SERIES. Lossy classico; nicho telemetria. | aberta (media) | taxonomia §6 |
| H-LOSS-09 | **Composicao de perdas** (ordem canonica + algebra de erro/ancora). Pre-requisito de seguranca p/ 2+ natures lossy. | aberta (arquitetural) | taxonomia §4 |
| H-LOSS-10 | **Budget / rate-distortion** ("menor arquivo com erro <= E"). Liga com foco byte-level. | aberta (media) | taxonomia §4 |
| H-LOSS-11 | **Tipos esquecidos** (JSON/lista, geo/geohash, bool/enum, unidades) + **inter-linha** (near-dedup de linhas + multiplicidade). | aberta (baixa, sob demanda) | taxonomia §2,§6 |

**Sequenciamento sugerido**: H-LOSS-00 (contrato) -> H-LOSS-02 lossless (cross-coluna
prova-de-conceito) -> H-LOSS-01 (residuo-soma) -> H-LOSS-04/05. Resto sob demanda.

---

## Pacote 11 — Tratamento de valores estruturados (CPF e afins) (registrado 2026-06-16, alvo 0.8)

**Origem**: ao caracterizar o CPF no exemplo do README (2026-06-16), o owner separou
DOIS tratamentos **ortogonais** pra valores estruturados digit-heavy (CPF, CNPJ, IP,
telefone, datas, EAN...). Sao caminhos distintos, nao concorrentes:

**(1) Filtro / nature (SEMANTICO — conhece o tipo) — JA PLANEJADO/welded.**
SPEC_CPF/CNPJ/IP ([ADR-0015](../../../../docs/adr/0015-natures-templated-checked-weld.md))
tira a pontuacao, guarda so' os digitos uteis e regenera o digito verificador no decode.
Welded p/ CPF/CNPJ/IP; os demais templated/checksummed estao no **Pacote 7** (H-TM-*,
aguardam T-DATA-1 + caracterizacao). E' opt-in e conhece a estrutura do tipo.

**(2) Repeticao INTRA-LINHA (GENERICO — nao conhece o tipo) — NOVO, alvo 0.8.**
Caracterizacao empirica (2026-06-16, `encode` real):
- `111.111.111-11` tem repeticao INTERNA (`111.` x3) que o pipeline atual **NAO fatora**.
- O que existe hoje e' tudo **interlinha**: `*N|` = linha inteira repetida adjacente
  (`*3|\111.\111.\111-\11`); `^N` = valor inteiro repetido em qualquer posicao.
- NAO existe captura de repeticao de substring **dentro de um unico valor** (intra-linha).
- Agravante: digito no corpo escapa (`\`) pra nao virar indice de ref -> valor digit-heavy
  **incha** em modo-TCF (`111.111.111-11` 14 chars -> `\111.\111.\111-\11` 18 chars) ->
  por isso cai no **raw fallback** (`!`) no multi-col.

| ID | Hipotese | Status | ref |
|---|---|---|---|
| H-INTRA-01 | Capturar repeticao de substring **intra-valor** reduz bytes em valores estruturados digit-heavy. Recurso novo — decidir o **engine**: OBAT (tokenizar sub-runs dentro do valor) OU HCC (compor atoms intra-valor). | aberta (alvo 0.8) | caracterizacao 2026-06-16 |
| H-INTRA-02 | Interacao com o **escape de digito** (`\`): fatorar a repeticao reduz o numero de `\`? Ou o escape come o ganho? Medir o net real. | aberta | — |
| H-INTRA-03 | **Overlap** com nature (1) + split estrutural (ADR-0026): o ganho intra-linha generico e' marginal/redundante onde nature ou split ja' atuam? Medir o INCREMENTO antes de welder (anti-incidente 2026-05-21). | aberta | — |
| H-NAT-MARK-01 | **Marcador de nature auto-descritivo** no header (tag `cpf`/`cnpj`/`ip` por coluna) pra o `decode` reconhecer a nature SOZINHO. Hoje as natures sao opt-in **OUT-OF-BAND**: o `.tcf` nao diz "esta coluna e' CPF", entao `decode` precisa receber `nature=` (provado: `decode(blob)` sem nature devolve o base-94 cru). O proprio codigo nota "futuro: header carry spec id". Format change (novo marcador, linha `!@%`) -> 0.8. | aberta (alvo 0.8) | `src/tcf/natures/__init__.py` docstring |
| H-NAT-MARK-02 | **Linguagem/registry MODULAR de SPECs em pasta** (plugin, direcao owner 2026-06-16): cada filtro = modulo spec auto-contido (regex + check_fn/transform + spec-id), e um registry descobre os de `natures/` + os de TERCEIROS (drop-in). Permite que outros desenvolvam filtros proprios. **NAO e' versao de formato** (API/registry Python; output base-94/padded identico). **VIRA versao** so' no elo de interop: pra um spec de terceiro ser auto-decodavel sem combinar out-of-band, precisa de **spec-id no header** (= H-NAT-MARK-01, 0.8). Logo: a API/pasta e' pre-1.0 barato; o "spec viaja no header" e' 0.8. | aberta (API pre-1.0; header 0.8) | direcao owner 2026-06-16 |

**Notas de decisao (do owner, 2026-06-16)**:
- Os dois caminhos coexistem: (1) e' semantico/opt-in (o usuario diz "isto e' CPF"),
  (2) e' generico/automatico (vale pra qualquer valor com repeticao interna).
- O recurso (2) e' **format change** (novo marcador/gramatica) -> grupo de formato
  **#TCF.8**, ciclo **0.8** (ADR-0024: minor do formato != badge de versao do pacote).
- OBAT vs HCC = **a decidir** (caracterizar antes). GATE real-world obrigatorio (toca core).
- Medir o overlap (H-INTRA-03) ANTES de welder: nature + split + dedup `^N` ja' cobrem
  parte dos casos; o generico so' vale pelo INCREMENTO sobre eles.

---

## Pacote 12 — Lazy/queryable view (registrado 2026-06-16, alvo pre-1.0)

**Origem**: owner, a partir da secao "consultar quase sem descomprimir" (1.0). Ideia: conectar
ao blob TCF e so' descomprimir o necessario quando um agregador e' puxado — descompressao
SELETIVA por coluna e por linha (filtro). Tese central da 1.0. **PoC pronto** em
[`2026-06-16-lazy-query/`](../../2026-06-16-lazy-query/) (`LazyTCF`, reusa decoders core
byte-exato; `where('cidade','SP').sum('valor')` toca so' `cidade`+`valor`). FORA de src/tcf.

| ID | Hipotese | Status | ref |
|---|---|---|---|
| H-QUERY-01 | **View lazy** sobre o blob: `count/sum/min/max/avg` + `where`, com decode por coluna sob demanda (column pruning) + por linha no filtro. Um `decode()` ou gzip/brotli por cima materializaria tudo antes de qualquer conta; o lazy materializa so' o referenciado. | **GADGET em `scripts/tcf_lazy/`** (13 testes; funcional: filtro+agregacao+alinhamento). NAO e' versao (le #TCF.7). | `scripts/tcf_lazy/` + `tests/test_tcf_lazy.py`; PoC `2026-06-16-lazy-query/` |
| H-QUERY-02 | **Agregar runs sem expandir**: somar/contar `*N|` (RLE) e `*N+delta|` (seq-RLE) lendo o marcador, sem materializar a sequencia. Leva o pilar de explicabilidade ao agregador. | aberta (media); depende H-QUERY-01 | — |
| H-QUERY-03 | **SQL na camada lazy**: o SQL gerado pela tool LLM->SQL (gadget spin-off, T-RECOVER-LLM-SCHEMA-MODE) roda sobre a view lazy. Integracao LEVE, sem dependencia dura. | aberta (baixa, spin-off) | tools_plan (ROADMAP.md) |

**Etapas segmentadas (barato, incremental)**:
- **L1** column pruning + agregadores (`count/sum/min/max/avg` + `where`) — **PoC OK**.
- **L2** quantificar a venda (memoria/latencia): medido — "qtd comprada por um usuario"
  (`where(CustomerID=X).sum(Quantity)`) toca **7.9%** do blob (online-retail 5k, 8 col);
  `count()` 0.2%; vs `decode()` 100%. (`lazy_query_dimensions.py`).
- **L3** **FEITO (via dict/raw)**: `nrows`/`group_count` contam/agrupam sem expandir as N
  linhas — dict (`@`) = tamanho do stream + tally da tabelinha; raw = nº de `\n`. Ex.:
  `group_count('education')` em 5k materializa 5%. **ACHADO**: agregar `*N|` direto no modo-tcf
  NAO e' separavel (OBAT+HCC entrelacam valor com refs; invariante de contagem falhou em IDs;
  0 colunas tcf clean-numeric) -> o ganho limpo vive no dict/raw; tcf/split caem em fallback.
- **L4** **FEITO**: `where` sobre coluna `@` varre so' o stream de indices (compara id;
  value/pred avaliados nos K unicos) — sem decodar os N valores. Encadeado (AND) le so' as
  posicoes ja' filtradas. Ex.: `where(workclass='Private')` em 5k toca 5% e nao cacheia a coluna.
- **L5** **FEITO**: `encode(table, sort_by=key)` agrupa (chave vira runs `*N|` contiguos) ->
  `group_ranges(key)` da' `{valor:(inicio,fim)}` e `agg_by(key,col,op)` faz group-by por SLICE
  (o "qtd por usuario": `agg_by('CustomerID','Quantity','sum')` == group-by manual, verificado).
  **Trade-off de compressao medido**: ordenar ajuda onde a chave correlaciona (adult education
  90%, -10%) e pode piorar onde outras colunas estavam bem ordenadas (online-retail CustomerID
  +2.3%). Ganho de latencia da query sempre presente. **L1-L5 funcional fechado.**

**E' versao de formato?** (pergunta do owner): **lazy-view NAO** (le o `#TCF.7` existente; gadget);
**L5 via `sort_by` NAO** (order-free, welded) — vira versao so' se for **modo de layout novo**.

**Notas**: (1) promover de PoC a gadget (camada externa que le o blob; nao precisa entrar em
src/tcf). (2) Conecta com V2-K (disco zero-copy/column-pruning) no plano binario futuro e com a
tool LLM->SQL (H-QUERY-03). (3) Lab: `2026-06-16-lazy-query/` (result.md). Visao por tier em
[`ROADMAP.md`](../../../../ROADMAP.md).

---

## Estrategia de mistura

**Antes de misturar, esgotar isoladas dentro de cada pacote.**

Quando o Pacote 1 fechar (H-DA-* todas em status terminal), opcao:
- Lab de **mistura intra-pacote 1**: combinar H-DA-01 (seq-RLE) + H-DA-04 (recovery post-transicao) e medir ganho composto
- Lab de **mistura entre-pacotes**: combinar H-DA-01 + H-ED-01 (seq-RLE + escape-deduction) e medir ortogonalidade vs interferencia

Mistura e' **experimentacao tambem** (faster path que prototipo). O
prototipo clean (`experiments/lab/clean/EXP-XXX-*`) e' pra testar
**resistencia + escala** depois das misturas validadas.

## Como adicionar hipotese nova

1. Identificou hipotese durante outro experimento? **Nao misturar.**
2. Adicione entrada nesta tabela com:
   - ID unico (`H-<pacote>-<numero>`)
   - Descricao curta
   - Status (`aberta`)
   - Onde sera testada (lab/sub-exp planejado, ou "candidata a lab proprio")
3. Adicione pointer no `perguntas-abertas.md` do lab em curso, se relevante
4. Continue o experimento corrente sem ser distraido

## Atualizacao

Atualizar quando: hipotese confirmada/refutada/movida-de-status, OU
nova hipotese identificada.

**Ultima atualizacao**: 2026-05-27 — **H-PERF-06 REFRAMED (lcp/lcs descartado, HCC detector novo alvo)**

Workflow 5 dimensoes (profile + 3 research + prototype) revelou:
- **H-PERF-06 original (compilar lcp/lcs)**: **refutada-real-world**.
  Profile cProfile em retail 20k mostra lcp/lcs = 1.8% do encode time
  (Amdahl: 5x speedup → 1.018x overall). Prototipo Cython mediu 6.23x
  em lcp_len isolado, mas em pipeline real e' ruido.
- **HCC `_detect_compositions` e' o real bottleneck**: 88% do tempo
  (17.06s de 19.4s) em syntax.py:246-251 — O(L^2) sub-tuple enumeration
  + Counter.update por iteracao.
- **H-PERF-06-v2 (proposta)**: target `_detect_compositions` em 3 fases:
  (A) algoritmica prune+early-term (~2-3x overall, risco byte-canonical);
  (B) Cython no inner loop (~1.5-2x overall, format-safe);
  (C) V2-J streaming bypassa HCC iterativo (v2.0).
- **Cython como tool**: validado (6.23x microbench em Windows MSVC),
  infraestrutura reutilizavel pra Patricia (V2-C) tambem.

Estudo completo: [docs/theory/h-perf-06-exploration.md](../../../docs/theory/h-perf-06-exploration.md).

**Atualizacao anterior**: 2026-05-27 — **Requisitos owner: streaming low-latency + disk zero-copy**

Owner registrou (2026-05-27) dois requisitos pra v2.0+ alem dos ja
listados em ADR-0018:
- **V2-J streaming online seriado** (low-latency, time-to-first-byte):
  cada etapa do pipeline libera saida o mais rapido possivel; foco
  latencia, nao throughput. Exige sub-formato pra header com sizes
  deferred (chunks ou trailer).
- **V2-K disk write + fast recovery sem buffer-over-buffer**: layout
  com offsets fixos pra column-pruning seek-based; mmap zero-copy;
  writer unico sem text.encode() copia full. Anti-pattern explicito:
  cache-over-cache / buffer-over-buffer.

Ambos registrados em [ADR-0018 V2-J/V2-K](../../../docs/adr/0018-v2-format-roadmap.md).
Conectam com O-FMT-08 (streaming), O-FMT-14 (header desacoplavel),
T-CODE-OUTPUT-SINKS, T-CODE-ENCODER-MANAGER Fase 2+. Reabertura quando
v2.0 abrir.

**Atualizacao anterior**: 2026-05-27 — **H-TH-02 Patricia estudada (workflow 4 dims)**

- **H-TH-02** (Patricia trie generalizada, registrada 2026-05-13 NUNCA testada):
  estudo de viabilidade completo em [docs/theory/patricia-trie-exploration.md](../../../docs/theory/patricia-trie-exploration.md).
  Status: `caracterizada-adiada` (vavel mas nao urgente).
  - 4 dimensoes (teoria, contrato atual, design fit, relacao H-PERF-04) convergem:
    prototipar e' viavel SE seguir protocolo rigoroso (fork dirty lab, validar
    D1-D9 1615B exato, evitar vies dataset de H-PERF-04).
  - Hash trigrama atual (ADR-0009, 5.4x speedup) cobre v1.0; Patricia ganha
    em prefixos populares variados (URLs, factory IDs, datas multi-decada).
  - Effort 10-30h se prototipar; bloqueador principal e' byte-canonical
    (tie-break por ordem de insercao deve ser pixel-identico).
  - **Reabertura quando**: v2.0 abrir, ou se H-PERF-06 (Cython) for primeiro
    e Patricia virar foco depois. Ortogonal a Cython (multiplicariam ganho).
  - ADR-0018 V2-C atualizado com pointer pra este estudo.

**Atualizacao anterior**: 2026-05-27 — **FECHAMENTO DO LIMBO + B-tier resolvido**
(lab `2026-05-27-naturezas-reais-uci/`, ADR-0018, pos-auditoria profunda):

- **Naturezas raras (#5 range, #8 arredondamento) + Pacote 7 H-LR-***:
  re-caracterizadas nos UCI (wine/beijing/online-retail). A estrutura-alvo
  EXISTE (arredondamento `.0`/`.95`, range estreito, precisao fixa) — a
  refutacao anterior foi em datasets gerais (Adult/TPC-H) inadequados.
  Status: `re-aberta-caracterizada` → roadmap **v2.0** (exige format change).
- **NOVO achado — ponto cego baixa-cardinalidade**: colunas numericas curtas
  repetitivas inflam ate' 2.3x (beijing `hour` 24 unicos → 228.8% M10).
  Toggles nao corrigem (nucleo OBAT+HCC). Subsume a hipotese "enumerated"
  (Pacote 5 T03) que foi **refutada prematuramente**. → roadmap v2.0 (V2-B).
- **Fallback identity** prototipado (fork): ganho 0.8-10.2%, RT OK, mas
  exige marcador novo → v2.0 (V2-A em ADR-0018).
- **B-tier RESOLVIDO** (ablacao seq-RLE full UCI):
  - **H-DA-01** `confirmada-empirica-marginal` → **`confirmada-empirica` (A)**:
    seq-RLE economiza **29.5%** em beijing (sensores cadenced). A "1.36%
    real-world" era so' Adult/TPC-H. Revalidado em dado independente.
  - H-DA-06 (subsumida) e H-DA-10 (9.92%) confirmados, sem mudanca.
- Todos os candidatos v2.0 (fallback/dicionario/strip-sufixo/lossy)
  registrados em [ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md).

**Atualizacao anterior**: 2026-05-22 (terceira) — **PACOTE 1 WELDED canonical**
(lab `2026-05-22-pacote1-weld-canonical/`, ticket T-CODE-PACOTE1-WELD-CANONICAL,
ADR-0011):
- Novos modulos canonical: `src/tcf/auto_cadence.py`, `obat_shape.py`,
  `composicional/hcc_seqrle.py`
- `encoder.py` agora usa pipeline delta-aware completo; `decoder.py`
  usa HCCSeqRLE.decode
- **D1-D9 baseline mudou: M9=1615B → M10=1523B (-92B, -5.70%)**
- **Real-world ganho 11.73% weighted** vs M9 puro (1,008,003B → 889,714B)
- RT 100%: 9/9 D1-D9 + 20/20 sint + 57/57 real

**Atualizacao anterior**: 2026-05-22 (segunda) — H-DA-11c WELDED canonical
(refactor zero-risk; lab `2026-05-22-h-da-11c-features-unificadas/`):
- Novo `src/tcf/column_features.py` (ColumnFeatures + analyze_column)
- Refatorado `src/tcf/auto_min_len.py` (2 APIs: from_features + wrapper)
- `src/tcf/encoder.py` chama `analyze_column` 1x
- **Output IDENTICO ao pre-refactor** (1615B baseline + 9.87% real-world + RT 100%)
- Prepara terreno pra T02-T07 + welding canonical futuro de detect_cadence

**Atualizacao anterior**: 2026-05-22 (primeira) — H-DA-11 WELDED canonical src/tcf
(ADR-0010 + sub-exps 01-05 do lab `2026-05-21-h-da-11-auto-min-len/`):
- `src/tcf/auto_min_len.py` (novo) + `src/tcf/encoder.py` modificado
- **Adult+TPC-H ganho 9.87% weighted** (99,501B em 1,008,003B)
- **M9 baseline 1615B EXATO preservado** (gating n>=100)
- RT 100%: D1-D9 9/9 + real-world 57/57
- Top wins: l_comment -29,647B, fnlwgt -22,238B, l_extendedprice -20,038B

**Atualizacao anterior**: 2026-05-21 — revalidacao categoria B
(lab `2026-05-21-revalidacao-categoria-B/`, ticket T-REVAL-H-DA-01-06-10):
- **H-DA-06** → `subsumida em H-DA-09b-v2` (cobertura 87.5% real-world)
- **H-DA-01** → `confirmada-empirica-marginal` (1.36% real-world vs 22.23% sint; 16.3x reducao)
- **H-DA-10** → `confirmada-empirica REAL-WORLD` (9.92% weighted!! ate -36.78% em fnlwgt; generalizou MELHOR que sintetico)
- **H-DA-11** (nova): auto-detect min_len por coluna — candidata futura
- Adicionada coluna `confianca` (Alta/Media/Baixa/A-revalidar) em hipoteses revalidadas

**Atualizacao anterior**: 2026-05-17 — sub-exp 09 (H-DA-09b
confirmada-empirica, auto-detect cadence -18% vs baseline). Tambem
reescrito com:
- distincao `confirmada-empirica` vs `confirmada-conceitual`
- O-01..O-04 (observacoes empiricas separadas de hipoteses)
- ressalvas conceituais explicitas em cada confirmacao
