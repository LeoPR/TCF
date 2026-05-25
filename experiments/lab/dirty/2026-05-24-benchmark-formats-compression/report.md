# Benchmark formats x compression (report)

**Data**: 2026-05-24
**Escopo**: 6 datasets x 4 formats x 4 transports = 96 medicoes (todas RT)

## Vencedores por dataset

| Dataset | rows×cols | Vencedor | Bytes | vs CSV raw |
|---|---|---|---:|---:|
| D17a-sint | 13×4 | csv + brotli | 194 | 32.28% |
| **D-CPF-uniform-1k** | 1000×1 | **tcf+nature + brotli** | **4552** | **30.34%** |
| **D-CPF-clustered-1k** | 1000×1 | **tcf+nature + brotli** | **3525** | **23.49%** |
| D-IP-subnet-1k | 1000×1 | csv + brotli | 909 | 6.78% |
| **adult-5k** | 5000×15 | **tcf + brotli** | **42243** | **7.83%** |
| **tpch-customer-1500** | 1500×8 | **tcf + brotli** | **70641** | **29.29%** |

**4 dos 6 datasets vencidos por TCF** (com ou sem nature). Outros 2
sao casos especificos: D17a tiny + D-IP-subnet onde HCC bugs
(sub-exp 14) limitam.

## Resultados por formato (medias agregadas)

### TCF + nature pra CPF datasets — destaque

| Cenario | bytes | vs csv raw | vs csv+brotli |
|---|---:|---:|---:|
| D-CPF-uniform-1k | | | |
|   csv raw | 15004 | 100% | — |
|   csv + brotli | 6309 | 42.05% | 100% (baseline best CSV) |
|   tcf raw | 18957 | 126.35% | — |
|   tcf + brotli | 5605 | 37.36% | 88.84% |
|   **tcf+nature + brotli** | **4552** | **30.34%** | **72.15%** |
| D-CPF-clustered-1k | | | |
|   csv + brotli | 4824 | 32.15% | 100% |
|   tcf + brotli | 5849 | 38.98% | 121.25% |
|   **tcf+nature + brotli** | **3525** | **23.49%** | **73.07%** |

**Pre-tx natureza ganha -28% vs csv+brotli** em CPF. ADR-0015 welding
mostra ROI real-world.

### TCF estrutural em datasets multi-coluna real

| Cenario | bytes | vs csv raw |
|---|---:|---:|
| adult-5k | | |
|   csv raw | 539244 | 100% |
|   csv + brotli | 48861 | 9.06% |
|   tcf raw | 193187 | **35.83%** (M10 dramatic vs csv raw!) |
|   tcf + brotli | 42243 | **7.83%** (vence csv+brotli) |
| tpch-customer-1500 | | |
|   csv + brotli | 79278 | 32.87% |
|   **tcf + brotli** | **70641** | **29.29%** |

TCF M10 sozinho ja' captura padroes (-65% adult vs csv raw); brotli
adiciona compressao residual. **Combinacao supera ambos individualmente.**

### Onde TCF perde

| Cenario | TCF | CSV |
|---|---:|---:|
| D-IP-subnet-1k tcf+brotli | 966 | csv+brotli 909 |

Diferenca pequena (~6%). D-IP-subnet eh dataset onde sub-exp 14 mostrou
bugs em HCC (cross-subnet). M10 ratio raw 117% — anti-compressor sem
pre-tx. Brotli geral consegue pegar padroes que HCC perdeu.

**Implicacao**: padding nature pra IP (variante C sub-exp 08 1.71%) NAO
foi welded como SPEC_IP — futuro candidate. Atualmente IP nao tem
nature, perde tudo pra brotli generico.

## Lessons consolidadas

### 1. Brotli vence gzip/zstd em quase tudo

| Transport | Datasets onde venceu |
|---|---:|
| brotli | 5/6 |
| zstd | 1/6 (D-CPF-clustered csv+zstd 4823 vs csv+brotli 4824 marginal) |
| gzip | 0/6 |

Brotli quality=11 + lento (0.5-6s pra adult-5k jsonl) mas vence.
Gzip mais rapido mas perde ~10% bytes.

### 2. TCF estrutural + transport eh combinacao otima

TCF captura padroes ESTRUTURAIS (OBAT prefix/sufix + HCC composicoes
+ seq-RLE near-identical). Brotli captura redundancia ENTROPICA
geral (byte-level n-grams). **Os dois sao ORTOGONAIS** — combinacao
ganha mais que cada sozinho.

Exemplo adult-5k:
- csv + brotli: 48861B (brotli sozinho)
- tcf + brotli: 42243B (-13.5% vs csv+brotli)

TCF "pre-processa" via entendimento de schema; brotli depois
arruma o resto.

### 3. Nature pre-tx eh dramatico onde aplicavel

CPF uniforme: tcf+nature+brotli (4552B) vence csv+brotli (6309B) por
-28%. **Apenas onde nature aplica.**

Schema_builder Fase 3 deve auto-detectar quando ativar nature pra
maximizar ROI sem usuario config.

### 4. JSON Lines eh formato verbose mas comprime tao bem quanto CSV

JSON raw eh 1.7-3.3x maior que CSV raw, mas apos brotli/zstd fica
~mesmo nivel. Trade-off: JSON eh self-describing (key:value) mas custa
mais sem compressao.

Implicacao pra APIs HTTP: se transport tem brotli ativo (Cloudflare,
HTTP/2/3), JSON eh tolerable. Sem compression, CSV ou TCF muito
melhores.

### 5. CSV+brotli eh baseline forte

Em D-IP-subnet, CSV+brotli (909B) vence TCF+brotli (966B). Em D17a
tiny (194B), idem. **Pra datasets gerais sem pre-tx por nature, CSV+brotli
eh standard hard to beat.**

TCF brilha em:
- Datasets com schema repetitivo (TPC-H tables: prefixos comuns)
- Pre-tx nature aplicavel (CPF/CNPJ welded)
- Inspecionabilidade do output (legivel)

## Conexao com EXP-008 historico

EXP-008 (Phase 1, ciclo v0.5) tinha rodado comparacao similar mas
sem TCF v0.6+nature. Findings consistentes:
- csv/brotli vence em maioria (na epoca)
- TCF v0.5 tinha overhead grande
- Pacote 1 weld (ADR-0011) + nature (ADR-0015) mudaram o jogo
- Hoje: TCF + brotli vence em 4/6 datasets testados

## Outputs visiveis (auditoria)

`out_files/<dataset>/`:
- `csv`, `csv.gzip`, `csv.brotli`, `csv.zstd`
- `jsonl`, `jsonl.gzip`, `jsonl.brotli`, `jsonl.zstd`
- `tcf`, `tcf.gzip`, `tcf.brotli`, `tcf.zstd`
- `tcf+nature`, `tcf+nature.*` (se applicable)

Owner pode comparar visualmente / binario qualquer combinacao.

## Conclusao

**TCF v0.6 + nature opt-in eh competitivo com CSV+brotli em real-world.**

Vence em:
- 4 de 6 datasets testados
- Datasets com schema repetitivo (Adult, TPC-H) **mesmo sem nature**
- Datasets templated/checked (CPF) com nature opt-in: ate -28% vs csv+brotli

Perde marginalmente em:
- Datasets onde brotli sozinho ja' maximiza (D-IP-subnet por HCC bugs)
- Tiny datasets (D17a) — header TCF overhead vs raw CSV

Caminhos pra ganhar mais:
- T-CODE-HCC-MULTI-DELTA-FIX (sub-exp 14 bugs)
- SPEC_IP_PADDED (variante C 1.71% welded)
- Schema_builder Fase 3 (auto-detect nature)
