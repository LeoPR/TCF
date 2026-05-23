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
| H-DA-07 | OBAT shape-preserve via dica generica | **confirmada-empirica condicional** -32% em D11+D16, MAS +17% em D1-D9 | `04-...` + `06-...` | NAO generaliza pra dados sem cadencia; pode ser MAL pra dados mistos. Conceitualmente: hint global aplicado a coluna heterogenea = problema |
| H-DA-08 | Detector que aceita per-run delta encoding | **refutada** (9 bytes total) | `07-per-run-delta-audit/result.md` | Audit em datasets D11+D16 apenas; outros datasets podem ter perfil diferente |
| H-DA-09 | Pre-stage infere hint automaticamente (always-on) | **refutada** | `06-auto-hint-regression-D1-D9/result.md` | "Always-on" e' a forma mais ingenua; refuta especificamente essa forma |
| H-DA-09b | Auto-detect cadencia via heuristica (length uniformity, LCP stability) | **confirmada-empirica** (-18% total em 20 datasets vs always-on -5.5%) | `09-auto-detect-cadence-heuristic/result.md` | 18/20 acertos; perdeu -14B em D1 e -20B em D11b (lengths variavel). Threshold 0.7 e' arbitrario. |
| H-DA-09b-v2 | Refino real-world: regra adicional numeric+high-cardinality | **CONFIRMADA** (real-world -5.6% adicional, -135,638B em Adult+TPC-H) | `2026-05-19-h-da-09b-refino-real-world/` + ADR-0008 | RT 12/12 OK; captura 12/12 HELP (era 4/12); zero regressao multi-camada |
| H-DA-09c | Tunar threshold da heuristica (0.5..0.8) | aberta — decorrente sub-exp 09 | nao testada | — |
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
| H-PERF-05d | Counter incremental (re-conta so' partes afetadas) | **aberta, nao testada** | candidata futura | Zero-risk teorico, ganho potencial alto (~50-70%). Implementacao complexa (state entre iters, invariants). |
| H-PERF-05e | Cap K maximo de sub-tupla (K=4/6/8) | **refutada-parcial** | `2026-05-20-hcc-perf-optimization/03-prototipos-cap-K-iter/` | K=8/6 PIOREARAM tempo (overhead check). K=4 deu 1.11x com +0.05% loss. Marginal. |
| H-PERF-05f | Cap iter_traces (50/30 vs 99) | **refutada (trade-off ruim)** | mesmo sub-exp | i=50: 1.37x/+3.44% bytes; i=30: 1.71x/+5.58% bytes. Viola regra invariante M9 ("zero loss"). |
| H-PERF-06 | Cython/Rust port de `lcp_len`/`lcs_len` corta Python overhead | aberta | nao testada | 29M chamadas em lineitem 5k, ~1.7us/chamada. Compilado podia cortar 50%+. |
| H-DA-09d | Heuristica multivariada (lengths + LCP+LCS + variance) | aberta — decorrente sub-exp 09 | nao testada | — |
| H-DA-09e | Re-avaliar heuristica a cada N strings (adaptativo) | aberta — decorrente sub-exp 09 | nao testada | — |
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
| H-FIX-01 | Escape de `,` em `_escape_lit` resolve bug e preserva M9 | aberta | sub-exp 02 planejado |
| H-FIX-02 | Mesma opcao mas re-baseline M9 necessario (D1-D9 tem `,`) | aberta | sub-exp 02 mediria |
| H-FIX-03 | Separator heuristico `*` antes de literal ambiguo (encoder-only) | aberta | sub-exp 03 planejado |

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

**Ultima atualizacao**: 2026-05-22 (terceira) — **PACOTE 1 WELDED canonical**
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
