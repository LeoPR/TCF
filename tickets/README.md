# TCF -- Tickets de Pesquisa e Implementacao

**Projeto:** Textual Columnar Format -- encoder/decoder compacto para LLMs.
**Objetivo:** Paper cientifico comparando formatos de dados para raciocinio de LLMs.

## Estrutura

```
tickets/
  README.md        Este arquivo (indice geral)
  open/            Tickets em andamento ou planejados
  closed/          Tickets concluidos
```

**Prefixos de tipo:**
- `H-` Hipotese (algo a comprovar/refutar por experimento)
- `E-` Experimento (teste com dados/modelos)
- `P-` Pesquisa (investigacao, survey, busca de referencias)
- `T-` Tarefa tecnica (implementacao, infra, entregavel)
- `R-` Resultado/finding (achado comprovado por experimento)

---

## Open (24)

Agrupado por area de interesse (atualizado 2026-04-10):

### LLM Understanding — core do paper (5)
| Ticket | Tipo | Status |
|--------|------|--------|
| [H-G30](open/H-G30-hiperparametros.md) | hypothesis | Thinking/temp — DONE (F60-F63) |
| [H-3layer](open/H-diagnostic-3layer-v02.md) | hypothesis | Diagnostic 3-layer — DONE (F80-F84) |
| [E-scale](open/E-scale-progression.md) | experiment | Scale 20→1000 — DONE (F85-F89) |
| [E-stats](open/E-stats-ablation.md) | experiment | STATS ablation — DONE (F90-F94) |
| [E-prompt](open/E-prompt-presentation.md) | experiment | Idioma, decoracao, wording |

### LLM Advanced — alem de Q&A (3) [NOVOS 2026-04-10]
| Ticket | Tipo | Descricao |
|--------|------|-----------|
| [E-qualitative](open/E-qualitative-reasoning.md) | experiment | Perguntas aproximadas, intuicao, tendencias |
| [E-codegen](open/E-code-generation.md) | experiment | LLM gera codigo validador (PoT sobre TCF) |
| [E-decompress](open/E-llm-decompress.md) | experiment | LLM descomprime TCF → CSV |

### Protocolo & Compressao (2) [NOVO 2026-04-10]
| Ticket | Tipo | Descricao |
|--------|------|-----------|
| [E-http](open/E-http-protocol.md) | experiment | TCF como substituto JSON/CSV em HTTP (brotli, zstd, overhead) |
| [H-compress](open/H-compression-layers.md) | hypothesis | Niveis progressivos L0-L3 |

### Formato & Schema (3) [1 NOVO 2026-04-10]
| Ticket | Tipo | Descricao |
|--------|------|-----------|
| [P-data-types](open/P-data-types.md) | research | Tipos: base64, binario, datas, nulls |
| [P-schema](open/P-schema-extension.md) | research | **NOVO** Schema completo (PK, FK, constraints) |
| [H-rounding](open/H-smart-rounding.md) | hypothesis | **NOVO** Arredondamento com % erro |

### Implementacao & Distribuicao (3) [1 NOVO 2026-04-10]
| Ticket | Tipo | Descricao |
|--------|------|-----------|
| [T-multi-lang](open/T-multi-lang.md) | task | **NOVO** JS, C, Go, Rust decoders |
| [T-G41](open/T-G41-cli-lib.md) | task | pip package + CLI (expandido) |
| [T-G42](open/T-G42-input-adapters.md) | task | SQLite, Parquet, Pandas (expandido) |

### Metodologia & Pesquisa (5) [1 NOVO 2026-04-10]
| Ticket | Tipo | Descricao |
|--------|------|-----------|
| [M-stability](open/M-stability-testing.md) | methodology | **NOVO** N>=3 runs para separar sinal de ruido |
| [P-G33](open/P-G33-metodologia.md) | research | CoT, PoT, repeticoes — REVIEWED |
| [P-G34](open/P-G34-dados-reais.md) | research | Datasets reais (TPC-H, WikiTableQA) |
| [P-G35](open/P-G35-modelos-llm.md) | research | Selecao de modelos — REVISADO |
| [P-questions](open/P-question-bank-review.md) | research | Banco de perguntas — REVIEWED |

### Formatos concorrentes & Analise (3)
| Ticket | Tipo | Descricao |
|--------|------|-----------|
| [P-formats](open/P-competing-formats.md) | research | TOON, MD Table |
| [E-plan](open/E-benchmark-plan.md) | experiment | Plano combinatorio completo |
| [T-figures](open/T-figures-analysis.md) | task | Figuras + analise estatistica |

## Closed (25)

| Ticket | Tipo | Titulo |
|--------|------|--------|
| [E-G01](closed/E-G01-encode-decode-v01.md) | experiment | Encode/decode v0.1 — 7/7 PASS |
| [E-G01b](closed/E-G01b-compression-v01.md) | experiment | Compression benchmark v0.1 |
| [E-G02](closed/E-G02-comprehension-v01.md) | experiment | Phase 1 v0.1 — 210 combos |
| [E-G03](closed/E-G03-ablation-v01.md) | experiment | Phase 2 v0.1 — 720 combos |
| [E-G04](closed/E-G04-stats-v01.md) | experiment | Stats ablation v0.1 |
| [T-G20](closed/T-G20-encoder-v02.md) | task | Encoder v0.2 implementado |
| [E-G20b](closed/E-G20b-benchmark-v02.md) | experiment | Compression benchmark v0.2 |
| [E-G21](closed/E-G21-llm-v02.md) | experiment | LLM accuracy v0.2 — 288 combos |
| [R-F30](closed/R-F30-tcf-escala.md) | finding | TCF escala, CSV colapsa |
| [R-F51](closed/R-F51-gemma3-melhor.md) | finding | gemma3:12b melhor modelo |
| [P-H01](closed/P-H01-reversibility.md) | hypothesis | Reversibilidade — 7/7 PASS |
| [T-P04](closed/T-P04-encoder-variants.md) | task | 24 variantes implementadas |
| | | |
| **Consolidados (2026-04-09):** | | |
| [E-G22](closed/E-G22-decode-reverso.md) | experiment | → absorvido por E-llm-decompress |
| [E-G23](closed/E-G23-perguntas-progressivas.md) | experiment | → absorvido por P-question-bank-review |
| [E-G24](closed/E-G24-multi-step.md) | experiment | → absorvido por P-question-bank-review |
| [E-G32](closed/E-G32-escala.md) | experiment | → absorvido por E-scale-progression |
| [E-pareto](closed/E-pareto-accuracy-tokens.md) | experiment | → absorvido por T-figures-analysis Fig 4 |
| [H-G31](closed/H-G31-thinking-mode.md) | hypothesis | → absorvido por H-G30-hiperparametros |
| [H-G36](closed/H-G36-idioma-perguntas.md) | hypothesis | → absorvido por E-prompt-presentation |
| [H-G37](closed/H-G37-notacao-decoracao.md) | hypothesis | → absorvido por E-prompt-presentation |
| [T-G40](closed/T-G40-paper.md) | task | → absorvido por T-figures-analysis |
| [T-naming](closed/T-cleanup-naming.md) | task | Renomeado _v02 → nomes limpos |
| [P-transport](closed/P-transport-compression.md) | research | TCF+gzip 29% menor que CSV+gzip |
| [R-F70](closed/R-F70-transport-compression.md) | finding | TCF+gzip comprime mais que CSV+gzip (F70-F73) |
| [R-F80](closed/R-F80-stats-shortcut.md) | finding | STATS como shortcut cognitivo (F80-F84) |

---

## Grupos de Trabalho (resumo)

```
--- HISTORICO v0.1 (baseline, experimentos concluidos) ---
G01  Encode/Decode v0.1  Codificacao multimodal (fk_mode, sorted) CLOSED
G01b Compression v0.1    Benchmark compressao sintetica            CLOSED
G02  Comprehension v0.1  Phase 1: JSONL 63% > CSV 48% > TCF 43%   CLOSED
G03  Ablation v0.1       Phase 2: dict/True=67% > JSONL 63%       CLOSED
G04  Stats Ablation v0.1 Hints +12pp global, -22pp em FK queries   CLOSED

--- CORRENTE v0.2 (compressao real, formato limpo) ---
G20  Formato v0.2        Encoder/decoder com 4 niveis compressao   CLOSED
G20b Benchmark v0.2      L3: 26% < CSV, 84-89% < JSONL             CLOSED
G21  Compressao LLM      L0=49% > L2=36% > CSV=19% (12 modelos)   CLOSED
E-decompress             LLMs descomprimem TCF → CSV (D1-D4)      OPEN
E-scale                  Escalabilidade 20→1000 rows               OPEN
E-prompt                 Ablacao: idioma + decoracao + sintaxe      OPEN

--- INFRAESTRUTURA (ortogonal a versao) ---
G30  Hiperparametros      think ON+t0=100% L0; L2 max 67%          DONE
H-3layer                 Diagnostico 3 camadas v0.2                OPEN
G34  Dados Reais          Datasets canonicos, representatividade   OPEN
G35  Modelos LLM          Selecao por familia/tier                 OPEN
G33  Metodologia          Prompting, CoT, PoT, repeticoes, survey  OPEN

--- ENTREGAVEIS ---
T-figures                Figuras + analise estatistica (7 figs)    OPEN
G41  CLI/Lib UX           Modos auto/niveis/grouped, pip            OPEN
G42  Input Adapters       SQLite, Parquet, SQL direto -> TCF        OPEN
```

---

## G01 — Encode/Decode [CLOSED]

Tudo que envolve codificar CSV -> TCF e decodificar TCF -> CSV.
Sem chamadas LLM — testes puramente deterministicos.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| P04 | Variantes do Encoder (EncoderConfig) | CLOSED | 3 numeric x 4 fk x 2 sorted |
| G01-T01 | Testes progressivos L0-L6 | CLOSED | 48 testes, 7 fixtures |
| G01-T02 | Testes roundtrip dados reais | CLOSED | 7 testes (test_roundtrip.py) |
| G01-T03 | Testes variantes encoding | CLOSED | 28 testes (test_p04) |
| H01 | Reversibility gate (phase0) | CLOSED | 7/7 configs passam |

**Documentacao:** [docs/TESTS.md](docs/TESTS.md) capitulos 1-9

**Como rodar:**
```bash
python -m pytest tests/test_g01_encode_decode.py -v    # Testes progressivos
python -m experiments.eval phase0                       # Gate automatico
```

---

## G01b — Compression Benchmark [CLOSED]

Mede quando o TCF comprime vs nao, com dados sinteticos realistas.
Responde perguntas cientificas criticas antes de envolver LLMs.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G01b-T01 | Benchmark CRM Sales (3 escalas) | CLOSED | 4 testes |
| G01b-T02 | Benchmark Service Logs | CLOSED | 2 testes |
| G01b-T03 | Benchmark Survey Likert | CLOSED | 2 testes |
| G01b-T04 | Benchmark Unique Data (worst case) | CLOSED | 3 testes |
| G01b-T05 | Crossover analysis (TCF vs CSV por escala) | CLOSED | 2 testes |
| G01b-T06 | Overhead features (sorted, stats) | CLOSED | 3 testes |
| G01b-T07 | Benchmark report (print com -s) | CLOSED | 1 teste |

**Documentacao:** [docs/TESTS.md](docs/TESTS.md) secao G01b

**Como rodar:**
```bash
python -m pytest tests/test_g01_compression.py -v
python -m pytest tests/test_g01_compression.py::TestBenchmarkReport -s  # print relatorio
```

**Conclusoes Cientificas:**

| ID | Conclusao | Evidencia |
|----|-----------|-----------|
| C1 | TCF vs JSONL: sempre comprime (59-83% menor) | Todos os 7 cenarios, sem excecao |
| C2 | TCF vs CSV: paridade so a partir de ~1000 linhas | crm_1000 = 0.97x; crm_50 = 1.34x |
| C3 | RLE eficiente com FK repetitiva (10-40x) | crm_5c=10x; crm_30c_1000r=40x |
| C4 | Sorted columns: overhead 5-15% sem RLE | unique_200: puro overhead |
| C5 | Stats: overhead < 5% | custo baixo para hints gratuitas |

**Implicacoes para o Paper:**
- Comparacao principal deve ser **TCF vs JSONL** (nao CSV) — JSONL e o formato de entrada mais comum para LLMs
- TCF vs CSV so faz sentido a partir de ~500+ linhas
- O beneficio real pode nao ser compressao mas **interpretabilidade** columnar
- Dataset recomendado para experimentos LLM: crm_sales(200, 20, 15) — maximiza contraste TCF vs JSONL

---

## G02 — LLM Comprehension [OPEN]

Testa se LLMs conseguem ler e entender dados em diferentes formatos.
Corresponde a Phase 1 do pipeline experimental.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| P01 | Token Count capture (Ollama API) | CLOSED | GenerateResult TypedDict |
| P02 | Response Parser (think-block + error) | CLOSED | 7 categorias de erro |
| P03 | Ground Truth programatico | CLOSED | Derivado dos CSVs |
| P05 | Banco de Perguntas Q1-Q10 | CLOSED | 3 camadas diagnosticas |
| P06 | Pipeline em fases | CLOSED | discover/phase0-3/status |
| G02-FIX01 | q6/q7 dict ground truth bug | CLOSED | count_ana/sum_ana no GT; TypeError no handler |
| H02 | Efeito principal do formato na accuracy | CLOSED | JSONL 63% > CSV 48% > TCF 43% |
| H03 | Diagnostico 3 camadas | CLOSED | math_ctrl separa modelos 100% vs 0% |

**Pre-requisitos:** G01 CLOSED (encode/decode funciona)

**Como rodar:**
```bash
python -m experiments.eval discover                     # Ver modelos
python -m experiments.eval phase1 --models auto         # Rodar Phase 1
```

---

## G03 — LLM Ablation (Variantes TCF) [OPEN]

Testa qual configuracao TCF maximiza accuracy e quais modelos performam melhor.
Corresponde a Phase 2 do pipeline.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| H04 | raw_float vs int_scaled vs bins_16 | OPEN | Phase 2 |
| H05 | Sort mode: com vs sem [sorted] | OPEN | Phase 2 |
| H06 | FK representation (4 modos) | OPEN | Phase 2 — candidato a maior impacto |
| H09 | Pareto: accuracy x tokens | OPEN | Derivado (sem calls extras) |

**Pre-requisitos:** G02 concluido (survivors.json gerado)

**Como rodar:**
```bash
python -m experiments.eval phase2                       # Variantes TCF
```

---

## G03b — Supertable Mode [OPEN]

Novo modo de encoding: JOIN de todas as tabelas em 1 supertabela.
FKs resolvidos para nomes, IDs eliminados, RLE sobre nomes repetidos.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G03b-T01 | Implementar `table_mode="supertable"` no encoder | OPEN | JOIN + drop ref tables |
| G03b-T02 | Decoder supertable (reconstruir tabelas via uniques) | OPEN | Header `from:` orienta |
| G03b-T03 | Testes unitarios supertable (encode/decode) | OPEN | G01-style progressivo |
| G03b-T04 | Benchmark compressao supertable vs multi-table | OPEN | Especialmente em escala |
| G03b-T05 | Phase 2b: supertable x modelos survivors | OPEN | Novo eixo combinatorio |

**Hipotese:** Uma unica tabela desnormalizada e mais facil para LLMs do que
3 tabelas com relacoes FK. Elimina confusao de "quantas linhas?" (erro gpt-oss=83)
e permite perguntas diretas sem resolucao de FK.

**Reversibilidade:** Sim. Header `(from: pessoas=pessoa, produtos=produto)` permite
reconstruir tabelas de referencia via `unique()`. IDs originais perdidos, relacoes preservadas.

**Compressao:** RLE sobre nomes repetidos escala muito bem:
- 41 vendas, 12 produtos → produto[sorted] 3.4x
- 1000 vendas, 12 produtos → produto[sorted] ~83x (estimado)

**Quando implementar:** Apos G02 (Phase 1) e G03 (Phase 2). Pode rodar como Phase 2b
usando survivors da Phase 1. Nao bloqueia o pipeline atual.

---

## G04 — LLM Deduction (Sem hints) [OPEN]

Testa se LLMs deduzem informacoes nao fornecidas explicitamente.
Encode "pobre" (sem stats/hints) vs encode "rico" (com stats).

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G04-T01 | Encode sem stats — LLM deduz sum/avg/count? | OPEN | Compara com stats=True |
| G04-T02 | Encode sem sorted — LLM deduz distribuicao? | OPEN | sorted=False vs True |
| G04-T03 | Encode pobre vs rico — delta accuracy | OPEN | Mede valor dos hints |

**Logica:** Se a LLM acerta com hints prontos, valida que stats sao uteis.
Se acerta SEM hints, TCF e intrinsecamente interpretavel.

---

## G05 — LLM Decode Reverso [OPEN]

Testa se LLMs conseguem fazer decode — gerar CSV a partir de TCF comprimido.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G05-T01 | LLM gera CSV a partir de TCF | OPEN | Compreensao total |
| G05-T02 | Verificar round-trip LLM decode vs real | OPEN | Diff com decode programatico |
| G05-T03 | Decode com variantes FK (dict/inline) | OPEN | Nomes ajudam no decode? |

---

## G06 — Perguntas Progressivas [OPEN]

Sequencia de perguntas que orientam a LLM a deduzir melhor.
Testar tanto em TCF quanto em formatos nativos (CSV/JSONL).

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G06-T01 | Sequencia: "quantas linhas?" -> "soma?" -> "quem comprou mais?" | OPEN | Chain of questions |
| G06-T02 | Comparar accuracy de pergunta unica vs progressiva | OPEN | Delta accuracy |
| G06-T03 | Progressiva em TCF vs progressiva em CSV/JSONL | OPEN | Beneficio e geral ou TCF-especifico? |

**Logica:** Se melhora em ambos formatos, a tecnica e geral.
Se so melhora em TCF, e TCF-especifica. Se TCF + progressiva
supera CSV + progressiva, compressao + orientacao e vencedora.

---

## G07 — Perguntas Complexas (Multi-step) [OPEN]

Perguntas que exigem leitura + FK resolution + agregacao + ranking.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G07-T01 | "Quem vendeu mais?" (argmax sobre grupo) | OPEN | Top-N modelos |
| G07-T02 | "Pessoas que compraram mais Abacaxi" (filter+group) | OPEN | Exige FK + filtro |
| G07-T03 | Dados de suporte (hints com totais por grupo) | OPEN | Pre-computar hints |
| G07-T04 | Benchmark multi-step em todos formatos | OPEN | CSV vs JSONL vs TCF |

**Logica:** Para os testes mais avancados, possibilidade de incluir dados
de suporte prontos (contagem, total por grupo, media) para ajudar a LLM.

---

## G08 — Telemetria e Timing Cientifico [OPEN]

Garantir que as medicoes de tempo sao cientificamente validas.
Ollama retorna breakdown detalhado que precisamos capturar e analisar.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G08-T01 | Capturar timing detalhado Ollama | CLOSED | load_duration, prompt_eval, eval |
| G08-T02 | Warmup protocol: descartar 1a chamada | OPEN | load_duration alto = warmup |
| G08-T03 | Repeticoes (3x) + media + outlier removal | OPEN | Protocolo de fisica experimental |
| G08-T04 | Separar load vs prefill vs decode no Pareto | OPEN | load nao conta como processamento |
| G08-T05 | stream=True vs stream=False: delta tempo | OPEN | Verificar se afeta tempo total |
| G08-T06 | Tokens/segundo por modelo (eval_count / eval_duration) | OPEN | Metrica de throughput |
| G08-T07 | temperature=0 como baseline (reproducibility) | CLOSED | Implementado como DEFAULT_OPTIONS |
| G08-T08 | temperature ablation (0 vs 0.3 vs 0.7) | OPEN | Testar com top configs |
| G08-T09 | seed=42 fixo para reproducibilidade | CLOSED | Implementado como DEFAULT_OPTIONS |

**Breakdown do Ollama:**
```
total_duration = load_duration + prompt_eval_duration + eval_duration
```
- `load_duration`: disco/cache -> GPU. Varia MUITO na 1a chamada (warmup).
- `prompt_eval_duration`: processar prompt (prefill). Depende de prompt_tokens.
- `eval_duration`: gerar resposta (decode). Depende de response_tokens.

**Protocolo cientifico proposto:**
1. Warmup: 1 chamada trivial ("2+2?") por modelo antes dos testes
2. Repeticoes: 3 chamadas por combinacao (apos todos modelos testados 1x)
3. Outlier: se max > 3x mediana, descartar e repetir
4. Reportar: mediana + IQR (nao media, que e sensivel a outliers)
5. Separar load_duration (infra) de eval_duration (capacidade do modelo)

---

## G09 — Thinking Mode [OPEN]

Testar impacto do modo de pensamento (thinking) na accuracy e tempo.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G09-T01 | Mapear modelos por thinking capability | OPEN | none / bool / scaled |
| G09-T02 | qwen3 thinking=True vs False | OPEN | qwen3 tem thinking toggle |
| G09-T03 | gpt-oss think levels (low/med/high) | OPEN | Se suportado |
| G09-T04 | Thinking vs no-thinking: accuracy delta | OPEN | Mais think = mais acerto? |
| G09-T05 | Thinking vs no-thinking: latency delta | OPEN | Mais think = mais lento? |
| G09-T06 | Strip think-blocks: verificar metricas | OPEN | Ja temos strip_think() |

**Tipos de thinking:**
- **Sem thinking:** phi3, gemma2, llama3.1 — respondem direto
- **Thinking booleano:** qwen3 — `<think>...</think>` (on/off)
- **Thinking em escala:** gpt-oss — low/medium/high effort

**Hipotese:** Thinking ajuda em perguntas complexas (sum, avg, multi-step)
mas nao em perguntas simples (max, min, nome). O tradeoff e accuracy vs tempo.

**Impacto combinatorio:** 
Thinking e ortogonal ao formato. Testar apenas com melhores configs de Phase 2.

**Estrategia de reducao:**
Se gpt-oss com thinking=high performa melhor, usar como baseline para
testes subsequentes (G04-G07). Depois voltar aos outros modelos para confirmar.
Modelos ordenados por velocidade (menores primeiro) para feedback rapido.

---

## G10 — Escala, Volume e Agrupamento [OPEN]

Testa escalabilidade com volumes maiores e estrategias de reducao de dados.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| H07 | Tamanho do modelo x formato | OPEN | Phase 3 |
| H08 | Familia do modelo x formato | OPEN | Phase 3 |
| H10 | Escalabilidade: chunk size | OPEN | Phase 3 |
| G10-T01 | Progressive scale: 100/500/1K/5K/10K rows | OPEN | Accuracy vs context limit |
| G10-T02 | Context window analysis por modelo (8K/32K/128K) | OPEN | Quando estoura? |
| G10-T03 | Chunking: partir tabela grande em pedacos | OPEN | Estrategia de split |
| G10-T04 | GROUP BY pre-agrupamento vs compressao raw | OPEN | Grouped 5x menor |
| G10-T05 | Hybrid: grouped + STATS globais | OPEN | Melhor dos dois mundos? |
| G10-T06 | Perspectiva/view: filtrar antes de comprimir | OPEN | "vendas de Caneta" |
| G10-T07 | Accuracy grouped vs raw nas mesmas perguntas | OPEN | O que se perde? |
| G10-T08 | Multi-provider (OpenAI, Claude, Gemini APIs) | OPEN | Validar com frontier models |
| G10-T09 | Comparar modelos locais (quantizados) vs APIs | OPEN | Ameaca a validade |
| G10-T10 | Impacto do tamanho de parametros (3B vs 8B vs 20B) | OPEN | Ja temos dados parciais |

**Dados de scale (estimativa de tokens TCF dict mode):**
```
    Rows    Tokens    Fits 8K?    Fits 32K?    Fits 128K?
     100       826    OK          OK           OK
     500     2,329    OK          OK           OK
   1,000     4,043    OK          OK           OK
   5,000    17,707    NO          OK           OK
  10,000    34,737    NO          NO           OK
```

**Grouped vs Raw (5000 vendas, 50 clientes, 20 produtos):**
```
  Raw supertable:  27,145 tokens  (5000 rows)
  Grouped (p×pr):   5,476 tokens  (900 rows) → 80% menor!
  Hybrid (grp+stats): 5,492 tokens (recupera min/max/avg)
```

**Trade-off agrupamento:**
- [OK] Total/count por dimensao, top-N, combinacoes
- [NO] Valores individuais, distribuicao, mediana, percentis
- Hybrid (grouped + STATS) recupera min/max/avg sem custo significativo

**Estrategia de escolha para o usuario:**
1. Se cabe no contexto → RAW (maximo de informacao)
2. Se nao cabe → GROUPED com STATS (perde detalhes, mantem agregacoes)
3. Se quer perspectiva → VIEW/filtro antes (menos dados, mais foco)

**Pre-requisitos:** G03 concluido (top_configs.json gerado)

---

## G11 — Prompting, PoT e Insights [OPEN]

Avaliar tecnicas de prompting, geracao de codigo, e producao de insights.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G11-T01 | Direct prompting baseline (atual) | CLOSED | "Responda apenas com um numero" |
| G11-T02 | Chain-of-thought: "pense passo a passo" | OPEN | Variante de prompt |
| G11-T03 | PoT: LLM gera codigo Python, nos executamos | OPEN | PAL/PoT (Gao 2023) |
| G11-T04 | Self-consistency: N respostas + majority vote | OPEN | temperature>0, 5x, voto |
| G11-T05 | Ablacao system prompt (com vs sem instrucoes) | OPEN | Prompt ajuda ou atrapalha? |
| G11-T06 | Repeticoes 3x + CI 95% para significancia | OPEN | Protocolo estatistico |
| G11-T07 | Baseline random/majority para cada questao | OPEN | Floor de accuracy |
| G11-T08 | Comparar com benchmarks padrao (WikiTQ, SQA) | OPEN | Posicionamento do paper |
| G11-T09 | PoT+Verify: LLM gera script de autoverificacao | OPEN | Script standalone |
| G11-T10 | PoT TCF vs PoT JSONL: formato ajuda code-gen? | OPEN | Columnar = array slicing? |
| G11-T11 | Text-to-Insight: respostas analiticas/relativas | OPEN | Narrativa, nao numeros |
| G11-T12 | Comparar insight raw vs grouped vs view | OPEN | Qual reducao gera melhor insight? |

### PoT (Program-of-Thought) — alto impacto esperado

Ao inves de "responda com um numero", pedir "escreva codigo Python".
O modelo gera codigo, nos executamos, comparamos com ground truth.

**Por que isso e critico:**
- Nosso erro dominante e arithmetic_error (62%). O modelo ENTENDE o formato
  mas ERRA a conta. Se ele gerar codigo correto, o erro desaparece.
- TCF columnar pode FACILITAR code-gen: dados ja estao em formato array.
  `vl = [2.5, 11, 1, 3.75, ...]` → `sum(vl)` trivial.
  JSONL precisa: `[json.loads(l)["vl"] for l in lines]` → mais complexo.

**PoT+Verify (script de autoverificacao):**
O modelo gera um script standalone (Python/JS/etc) que:
1. Parseia os dados TCF
2. Calcula as metricas pedidas
3. Exibe resultados formatados
A pessoa pode rodar o script nos dados originais para verificar.
Isso transforma o TCF de "formato para LLM ler" em "formato para LLM gerar ferramenta".

### Text-to-Insight — respostas analiticas

Ao inves de perguntas factuais ("qual a soma?"), perguntas analiticas:
- "Quais tendencias voce observa nos dados?"
- "Bob vende mais que Alice?"
- "Quais produtos saem mais? Tem sazonalidade?"
- "O que voce recomendaria para o gerente desta loja?"

**Avaliacao:** Nao e exact-match — precisa de avaliacao qualitativa ou
checklist de insights esperados (ex: "menciona que Caneta e o top produto").
Mais dificil de automatizar mas altamente relevante para uso pratico.

**Hipotese:** TCF grouped com STATS pode gerar melhores insights que raw,
porque os dados ja estao pre-resumidos. Testar raw vs grouped vs view.

### Principio cientifico

Nao afirmar "bom" ou "ruim". Medir com rigor e excluir alternativas.
Se TCF performa pior com direct prompting mas melhor com PoT, o gargalo
era o prompting, nao o formato.

**Logica de reducao:**
1. Direct prompting baseline (CLOSED)
2. CoT → melhora? Se sim, gargalo era raciocinio
3. PoT → melhora? Se sim, gargalo era aritmetica (confirmado pelo F3)
4. PoT TCF vs PoT JSONL → formato afeta code-gen?
5. Insights → qual reducao gera melhor narrativa?

---

## G12 — Analysis & Paper [OPEN]


Analise estatistica dos resultados, figuras, e escrita do artigo.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| P07 | Analise estatistica e figuras | OPEN | Testes de significancia |
| A01 | Accuracy heatmap (formato x modelo) | OPEN | Phase 1 results |
| A02 | Bar chart 3 camadas diagnosticas | OPEN | Phase 1 results |
| A03 | Ablation table (variantes TCF) | OPEN | Phase 2 results |
| A04 | Pareto scatter (accuracy x tokens) | OPEN | Phase 2+3 results |
| A05 | Scaling curve (accuracy x chunk size) | OPEN | Phase 3 results |
| A06 | Error distribution (stacked bar) | OPEN | All phases |
| A07 | Comparacao TCF vs TOON | OPEN | Trabalhos relacionados |
| W01 | Escrita do artigo | OPEN | Estrutura em ARCHITECTURE.md |
| W02 | Guia pratico de uso do TCF | OPEN | Manual para usuarios |
| W03 | Artigo em capitulos separados | CLOSED | docs/article/ com 9 caps + appendices |

**Pre-requisitos:** G02-G08 concluidos (dados experimentais prontos)

---

## G13 — CLI e Biblioteca (UX) [OPEN]

Simplificar o uso do TCF para usuarios finais. A lib via pip e o CLI
devem refletir as praticas descobertas nos experimentos.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G13-T01 | `tcf auto` — modo automatico (melhor config) | OPEN | Detecta e aplica best practices |
| G13-T02 | `tcf encode --mode flat` — supertable join | OPEN | Desnormaliza tudo em 1 tabela |
| G13-T03 | `tcf encode --mode grouped --by col1,col2` | OPEN | GROUP BY pre-encoding |
| G13-T04 | `tcf encode --mode view --where "prod=Caneta"` | OPEN | Filtro/perspectiva antes |
| G13-T05 | `tcf encode --precision smart` — arredondamento inteligente | OPEN | Ver detalhes abaixo |
| G13-T06 | `tcf encode --for-llm` — shortcut: dict+stats+smart | OPEN | Um comando, melhor output |
| G13-T07 | `tcf analyze` — gerar script de verificacao (PoT) | OPEN | Gera Python que parseia TCF |
| G13-T08 | Warnings e advisories no output | OPEN | Alertas de arredondamento/perda |
| G13-T09 | `tcf pipe` — stdin → TCF → stdout (pipe unix) | OPEN | Para composicao com outros tools |

### Arredondamento inteligente (G13-T05) — requer cuidado

**O problema:** valores como `3.141592653589793` gastam muitos tokens.
`3.14` seria suficiente em contexto financeiro (2 casas) ou `3.1416` em cientifico.

**Estrategia proposta:**

```
Nivel 0: raw      3.141592653589793  (sem perda)
Nivel 1: auto-2   3.14              (financeiro, 2 casas)
Nivel 2: auto-4   3.1416            (cientifico, 4 casas significativas)
Nivel 3: smart    analisa dados, escolhe melhor precisao por coluna
```

**Smart precision:**
1. Detectar se coluna e financeira (todos valores tem <= 2 decimais) → arredondar para 2
2. Detectar se coluna e inteira (todos .0) → emitir como inteiro
3. Senao: manter precisao original ou arredondar para N casas significativas
4. Calcular erro maximo introduzido e emitir warning no header:
   ```
   > WARNING: coluna vl arredondada para 2 casas. Erro max: 0.005. Sum error: 0.12 (0.06%)
   ```
5. A LLM recebe o warning e sabe que precisa considerar margem de erro

**Riscos:**
- Arredondamento pode inverter rankings ("quem vendeu mais?" muda com erros de arredondamento)
- Soma de valores arredondados != arredondamento da soma (erro acumulativo)
- Precisa de testes extensivos antes de oferecer como feature

**Prioridade:** Pos-artigo. Para os experimentos usamos raw_float (baseline seguro).
Para a lib publicada, implementar com warnings claros.

---

## G14 — Input Adapters [OPEN]


Adapters para fontes de dados reais. Pos-artigo, foco em usabilidade.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G10-T01 | `tcf.from_sqlite(db_path)` — adapter SQLite | OPEN | FK e tipos via schema |
| G10-T02 | SQLite como storage sintetico | OPEN | Gerador -> SQLite -> views -> CSV |
| G10-T03 | `tcf.from_dataframe(df)` — adapter Pandas | OPEN | Uso interativo |
| G10-T04 | `tcf.from_sqlalchemy(engine)` — adapter SQL generico | OPEN | PostgreSQL, MySQL etc |
| G10-T05 | Auto-detect metadata de FK constraints | OPEN | Nao precisar metadata.json |
| G10-T06 | SQLite como storage sintetico + views | OPEN | Gerador → SQLite → views → CSV |
| G10-T07 | `tcf encode --from sqlite:db.sqlite` CLI | OPEN | Input direto sem CSV intermediario |

**Logica:** Hoje o TCF recebe CSV + metadata.json. No mundo real, dados
vem de SQL (SQLite, PostgreSQL, etc). O metadata.json simula o que um
schema SQL ja tem nativamente (PK, FK, tipos). Com um adapter SQLite:
- `CREATE TABLE vendas (id_pessoa REFERENCES pessoas(id), ...)`
- O encoder le o schema, descobre FKs automaticamente, gera TCF
- Sem necessidade de metadata.json manual

**Prioridade:** Depois de G01-G09 (nao bloqueia o artigo).
O artigo usa CSV + metadata. O adapter e feature da biblioteca.

---

## G15 — Sintaxe TCF v0.2 + Compressao Alternativa [OPEN]

Revisao critica da sintaxe do TCF. A v0.1 tem problemas de design
identificados durante Phase 1+2 que desperdicam tokens e confundem LLMs.

### Problemas da v0.1 (identificados)

1. **IDs sequenciais redundantes** — `id[key]: 1 2 3...30` nao adiciona informacao se a posicao ja e o indice
2. **DICT com `=` nao e padrao** — `1=Ana` nao e CSV, JSON, nem MD
3. **`[sorted]` duplica dados e confunde** — comprovado por F10 (sorted sem impacto) e F4 (gpt-oss 83)
4. **`N:val` e desconhecido** — `3:1` parece IP ou hora; `(3)Ana` ou MD table seria mais familiar
5. **Tabelas de referencia sao lixo no modo flat** — pessoas(30) + produtos(12) ocupam tokens sem utilidade
6. **Header verboso** — 6 linhas de instrucao que poderiam ser 2

### Formatos a testar

| ID | Formato | Descricao | Tamanho (41 vendas) |
|----|---------|-----------|---------------------|
| v0.1 | TCF atual (dict+stats) | 3 tabelas, DICT, sorted | 2113 chars |
| v0.1i | TCF inline+stats | 3 tabelas, nomes, sem sorted | 1781 chars |
| **v0.2a** | **Flat supertable** | 1 tabela, sem IDs, sem ref tables | **1000 chars** |
| v0.2b | Flat + distribuicao (N)val | + linha de distribuicao sorted | 1368 chars |
| v0.2c | Markdown table + STATS | Formato MD familiar | 1267 chars |

### Tickets

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G15-T01 | Implementar encoder v0.2a (flat supertable) | OPEN | JOIN + drop refs + no IDs |
| G15-T02 | Implementar encoder v0.2b (flat + distribuicao) | OPEN | + linha `col~: (3)Ana (2)Bruno` |
| G15-T03 | Implementar encoder v0.2c (MD table + STATS) | OPEN | Formato mais familiar para LLMs |
| G15-T04 | Notacao RLE: `N:val` vs `(N)val` vs MD-style | OPEN | Qual a LLM entende melhor? |
| G15-T05 | Ablacao de header: minimo vs completo | OPEN | 2 linhas vs 6 linhas |
| G15-T06 | Benchmark size: v0.1 vs v0.2a vs v0.2b vs v0.2c | OPEN | Comparar tokens |
| G15-T07 | LLM accuracy: v0.1 vs v0.2 variantes | OPEN | Mesmo protocolo Phase 1 |
| G15-T08 | Decidir formato definitivo com base em dados | OPEN | Pode aposentar v0.1 |
| G15-T09 | Delta encoding para colunas numericas | OPEN | `2.5 +0.2 +0.2 +0.4` |
| G15-T10 | Dict refs global (nao so FK) | OPEN | `@A=Ana; @A @B @A` |

### Proposta v0.2a (flat supertable, ~1000 chars)

```
# TCF v0.2
# (N)val = val repeated N times. Columns are positional.

## compras n=41
# STATS vl: n=41 sum=217.6 min=1 max=12.4 avg=5.31
pessoa: Ana Bruno Ana Carla Diego ...
produto: Caneta Caderno Lapiz Caneta Borracha ...
vl: 2.5 11 1 3.75 2.9 ...
```

Vs v0.1 (2113 chars): **53% menor**, sem IDs, sem DICT, sem [sorted], sem tabelas de referencia.

### Impacto nos testes

Se v0.2a performar significativamente melhor:
- Resultados de Phase 1+2 com v0.1 ficam como **baseline historico**
- Artigo documenta a evolucao: "v0.1 (43%) → v0.2a (??%) — design matters"
- Nao precisa apagar, mas o artigo foca no formato final

Se v0.2a nao melhorar: v0.1 estava certo e a verbosidade nao era o problema.

**Prioridade: ALTA** — este experimento pode mudar o resultado principal do artigo.

---

## G34 — Dados Reais e Representatividade [OPEN]

Garantir que os dados sinteticos representam cenarios reais e que os resultados
sao generalizaveis. Usar datasets canonicos como referencia.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G34-T01 | Catalogar distribuicoes do crm_sales (Zipf, cardinalidade) | OPEN | Comparar com TPC-H |
| G34-T02 | Adicionar tipos de dados: datas, booleanos, strings longas | OPEN | Cobertura de tipos |
| G34-T03 | Benchmark com TPC-H lineitem (dataset canonico SQL) | OPEN | Se publico |
| G34-T04 | Benchmark com WikiTableQuestions (dataset canonico LLM) | OPEN | Table QA standard |
| G34-T05 | Metricas de representatividade: tipos, cardinalidade, distribuicao | OPEN | Perfil estatistico |
| G34-T06 | Argumento formal: "sinteticos cobrem X% dos cenarios reais" | OPEN | Para o artigo |
| G34-T07 | Worst-case analysis: quando TCF NAO funciona | OPEN | Dados unicos, texto livre |
| G34-T08 | Sensitivity analysis: variar parametros e medir estabilidade | OPEN | CI 95%, bootstrap |

**Questoes a responder (para o artigo):**
- Os dados sinteticos representam sistemas reais? (distribuicao, tipos, cardinalidade)
- Qual a cobertura de tipos de dados? (string, int, float, date, bool, null)
- A compressao se mantem com dados mais heterogeneos?
- Em que cenarios o TCF definitivamente NAO funciona?
- Qual o intervalo de confianca dos resultados de compressao?

**Datasets canonicos identificados:**
- **TPC-H** — 8 tabelas (lineitem 6M, orders 1.5M), ratios customer:order 1:10
- **Olist** (Kaggle) — e-commerce brasileiro, 9 tabelas relacional, 100K orders, portugues
- **WikiTableQuestions** — 2108 tabelas, ~20-30 rows, 5-8 cols, benchmark table QA
- **Spider/BIRD** — multi-DB relational, SQL generation benchmark

**Problemas do dataset atual (identificados):**
- Customer:order ratio 1:1.4 (irreal — TPC-H usa 1:10, empresas reais 1:5 a 1:50)
- Sem coluna de data (datas sao ~10% dos dados em sistemas reais)
- Sem booleanos nem nulos
- Distribuicao Zipf nao verificada formalmente (citar Gray et al. 1994)

**Estatistica (referencias):**
- Bootstrap CI: Efron & Tibshirani (1993), 10000 resamples, BCa intervals
- McNemar's test: para comparacoes pareadas de accuracy entre formatos
- Cohen's h: effect size para proporcoes
- Bonferroni: correcao para multiplas comparacoes

**Prioridade:** Depois de G21 (LLM comprehension v0.2). Antes do paper final (G40).

---

## G35 — Selecao de Modelos LLM [OPEN]

Selecao inteligente de modelos por familia, tier de tamanho e capacidade.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G35-T01 | Definir benchmark model set (8 modelos) | OPEN | 2-3 tiers, 1 por familia |
| G35-T02 | Instalar modelos faltantes via pull | OPEN | deepseek-r1, phi4, gemma3 |
| G35-T03 | Testar thinking modes (qwen3, deepseek-r1) | OPEN | Comparar on vs off |
| G35-T04 | Escalar: testar 14B+ (qwen2.5:14b, phi4:14b) | OPEN | Se GPU suporta |

**Ollama API:** Nao existe API publica para buscar modelos no registry.
Usar lista curada de modelos no config do benchmark.

**RTX 3060 12GB — o que cabe (Q4 quantization):**
```
Tier tiny (3-4B):    llama3.2:latest (3.2B), phi3:latest (3.8B)     ~3GB VRAM
Tier small (7-8B):   qwen2.5:7b, llama3.1:8b, mistral:7b,          ~5GB VRAM
                     deepseek-r1:7b, qwen3:8b
Tier medium (9-14B): gemma2:9b, gemma3:12b, phi4:14b,               ~6-8GB VRAM
                     qwen2.5:14b, deepseek-r1:14b
Tier large (20B+):   gpt-oss:latest (20.9B MXFP4)                   ~12GB (limite)
NAO CABE:            llama3.3:70b (36GB), mixtral:8x7b (25GB)
```

**Instalados (11 modelos):** llama3.2, phi3, mistral, deepseek-r1:7b, qwen2.5,
llama3.1:8b, qwen3:8b, gemma2:9b, gpt-oss + 2 vision (excluidos)

**Candidatos a instalar (prioridade para dados tabulares):**
1. phi4:14b — Microsoft, otimizado para math/reasoning (~9GB) `ollama pull phi4`
2. deepseek-r1:14b — CoT reasoning distilado de 671B (~9GB) `ollama pull deepseek-r1:14b`
3. gemma3:12b — Google, bom em instrucoes estruturadas (~8GB) `ollama pull gemma3:12b`
4. qwen2.5-coder:7b — treinado em codigo, bom para parsing (~5GB) `ollama pull qwen2.5-coder:7b`

**Categorias Ollama relevantes:** Reasoning, Math, Code
**Criterio de selecao:** erro dominante e arithmetic (62%), logo priorizar
modelos com forte capacidade de math/reasoning, nao apenas tamanho.

**Nota:** llama3.3:70b e mixtral:8x7b NAO cabem na RTX 3060 12GB.

**Familias com thinking:** qwen3 (toggle), deepseek-r1 (nativo CoT)
**Melhores para dados tabulares:** qwen2.5 e deepseek-r1 (comunidade)

**OpenAI-compatible:** Ollama suporta `/v1/chat/completions` nativamente.
Nao proxy para APIs externas — so modelos locais.

**Prioridade:** Apos melhorar dados sinteticos (G34). Antes de re-rodar G21 expandido.

---

## G36 — Idioma e Forma de Perguntar [OPEN]

LLMs sao sensiveis ao idioma dos dados E ao idioma/forma das perguntas.
Precisamos isolar se os resultados dependem de COMO perguntamos, nao so do formato.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G36-T01 | Testar perguntas em portugues vs ingles | OPEN | Mesmo conteudo, idioma diferente |
| G36-T02 | Testar perguntas simples vs complexas | OPEN | "soma de total?" vs "some todos os valores..." |
| G36-T03 | Testar dados em pt-BR vs en-US | OPEN | Nomes, cidades, produtos |
| G36-T04 | Ablacao: forma de perguntar afeta accuracy? | OPEN | Ortogonal ao formato |
| G36-T05 | Pesquisar papers sobre sensibilidade linguistica em LLMs | OPEN | Multilingual bias |
| G36-T06 | Separadores decimais (ponto vs virgula) | OPEN | 1.23 vs 1,23 |

**Hipoteses:**
- Perguntas em ingles podem performar melhor (mais dados de treinamento)
- Perguntas curtas e diretas podem ser melhores que elaboradas
- Dados com nomes em ingles podem ser mais faceis para modelos
- A forma de perguntar pode afetar mais que o formato dos dados

**Estado atual:** Todas as perguntas sao em portugues. Dados com nomes pt-BR.
Isso pode ser um vies — os modelos foram treinados majoritariamente em ingles.

**Abordagem:** Testar com TOP config (L2 + qwen3), variar APENAS o idioma
e forma da pergunta. Se delta > 10pp, o idioma e uma variavel relevante.

**Papers relevantes (a buscar):**
- Shi et al. (2022) "Language Models are Multilingual Chain-of-Thought Reasoners"
- Lai et al. (2023) "ChatGPT Beyond English" — performance drop em linguas nao-inglesas
- Ahuja et al. (2023) "MEGA: Multilingual Evaluation of Generative AI"

**Prioridade:** Apos Etapa 1. Pode mudar decisoes sobre idioma default do TCF.

---

## G37 — Notacao e Decoracao do Formato [OPEN]

Testar variantes de sintaxe e decoracao para maximizar compreensao por LLMs.
Hipotese: a FORMA de apresentar os dados comprimidos afeta a accuracy
independente do conteudo.

| ID | Titulo | Status | Notas |
|----|--------|--------|-------|
| G37-T01 | Notacao RLE: N*val vs N:val vs (N)val | OPEN | 86 chars cada |
| G37-T02 | Code fence: ```tcf ... ``` vs plain text | OPEN | +overhead, +familiaridade |
| G37-T03 | Header com exemplo: "3*Ana = Ana Ana Ana" | OPEN | 1-shot inline |
| G37-T04 | XML tags: `<column name="pessoa">` | OPEN | Familiar para Claude/GPT |
| G37-T05 | Dict com code fence: ```csv + # dict | OPEN | Mistura CSV + compressao |
| G37-T06 | Sem explicacao (modelo infere sozinho) | OPEN | Baseline: zero instrucao |
| G37-T07 | Com few-shot (2-3 linhas de exemplo antes) | OPEN | Overhead vs accuracy |
| G37-T08 | Markdown table expandido (sem compressao) | OPEN | Controle: familiar + verbose |

**Variantes prototipadas (5 linhas de dados):**

```
A: N*val (current)              86 chars  — compacto, sem explicacao
B: N:val (colon)                86 chars  — alternativa notacional
C: code fence + explicacao     227 chars  — familiar, com overhead
D: 1-shot example              164 chars  — exemplo inline
E: XML tags                    228 chars  — familiar para APIs
F: dict + code fence           171 chars  — CSV-like comprimido
G: MD table (sem compressao)   173 chars  — baseline familiar
```

**Questao central:** o overhead de explicacao (~100 chars extra) se paga
em accuracy? Ou o modelo entende N*val sem precisar de instrucao?

**Abordagem:** testar com top modelo (gemma3:12b ou qwen3:8b),
dados fixos (retail_200), variar APENAS a decoracao/notacao.
Se accuracy mudar > 15pp entre variantes, a decoracao importa.

**Boas praticas pesquisadas (fontes oficiais):**

| Pratica | Evidencia | Fonte |
|---------|-----------|-------|
| Code fences (```csv) ou XML tags | **Forte** | OpenAI, Anthropic, Sui et al. 2024 |
| Headers de coluna presentes | **Forte** | OpenAI, Hegselmann 2023 |
| Explicacao natural do formato antes dos dados | **Moderada-Forte** | Anthropic, Yin et al. 2023 |
| Pipe/virgula como delimitador (nao espaco) | **Moderada** | Hegselmann 2023 |
| Few-shot examples (1-3) | **Forte** | OpenAI, Google, Brown 2020 |
| Uma linha por registro/valor | **Forte** | Todas as fontes |
| Para formatos novos: definir encoding explicitamente | **Moderada** | Yin 2023 |

**Especifico por provider:**
- **OpenAI:** triple backticks + JSON/MD table + few-shot
- **Anthropic/Claude:** XML tags (`<data>...</data>`) como recomendacao primaria
- **Google/Gemini:** JSON + labels (Input:/Output:) + 3-5 few-shot

**Referencia adicional:** Yin et al. (2023) "Did You Read the Instructions?" —
explicar encoding conventions no prompt melhora accuracy em formatos novos.

**Implicacao direta para TCF:** O formato atual envia dados SEM code fence,
SEM exemplo, com explicacao minima. Adicionar ``` + 1-shot example pode
melhorar accuracy significativamente (hipotese a testar).

**Prioridade:** Apos G30 (hiperparametros). Pode ser feito em paralelo com G36.

---

## Pipeline de Execucao

```
G01  [CLOSED]    G02  [CLOSED]    G03 [CLOSED]    G04 [CLOSED]    G05-G15 [OPEN]
G01b [CLOSED]    Comprehension   Ablation        Stats Ablation  Avancados+Paper
                                                        
phase0 (gate) ──> phase1 (formatos) ──> phase2 (ablacao) ──> testes avancados ──> analyze
  7/7 pass         survivors.json       top_configs.json    G04-G08              figuras
                                                                                  artigo
```

**Invocacao completa:**
```bash
python -m experiments.eval discover          # Ver modelos disponiveis
python -m experiments.eval phase0            # Gate encode/decode
python -m experiments.eval phase1 --models auto  # Formato x modelos
python -m experiments.eval phase2            # Variantes TCF
python -m experiments.eval phase3            # Escala
python -m experiments.eval status            # Progresso
```

---

## Infraestrutura (P-series) — Resumo de Status

| ID | Titulo | Status |
|----|--------|--------|
| P01 | Token Count capture | CLOSED |
| P02 | Response Parser | CLOSED |
| P03 | Ground Truth | CLOSED |
| P04 | Encoder Variants | CLOSED |
| P05 | Question Bank | CLOSED |
| P06 | Pipeline em Fases | CLOSED |
| P07 | Analise + Figuras | OPEN |

---

## Status dos Testes (sem LLM)

| Grupo | Arquivo | Testes | Status |
|-------|---------|--------|--------|
| G01   | test_g01_encode_decode.py | 63 | CLOSED |
| G01b  | test_g01_compression.py | 17 | CLOSED |
| -     | test_roundtrip.py (legado) | 7 | CLOSED |
| -     | test_p01_p02_p03.py | 36 | CLOSED |
| -     | test_p04_encoder_variants.py | 28 | CLOSED |
| **Total** | | **151** | **All pass** |

---

## Estimativas de Chamadas LLM

| Fase    | Grupo | Calls    | Descricao                    |
|---------|-------|----------|------------------------------|
| Phase 0 | G01   | 0        | Gate encode/decode           |
| Phase 1 | G02   | ~234     | Formato principal x modelos  |
| Phase 2 | G03   | ~960     | Variantes TCF (ablacao)      |
| Phase 3 | G03   | ~450     | Escala + interacoes          |
| **Total** |     | **~1.644** |                            |

---

## Documentacao

| Arquivo | Funcao | Fonte de... |
|---------|--------|-------------|
| [README.md](../README.md) | Porta de entrada GitHub | Links para tudo |
| [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) | Pilar conceitual | Estrutura, intencoes |
| [docs/EXPERIMENT_DESIGN.md](../docs/EXPERIMENT_DESIGN.md) | Metodologia | Fases, criterios |
| [docs/TESTS.md](../docs/TESTS.md) | Registro de testes | Fixtures, coverage |
| [docs/SOURCE_MAP.md](../docs/SOURCE_MAP.md) | **Mapa de rastreabilidade** | Quem e fonte de que |
| [docs/article/](../docs/article/README.md) | Meta-artigo em capitulos | Resultados, inovacoes |

**Rastreabilidade:** Ver [SOURCE_MAP.md](../docs/SOURCE_MAP.md) para saber
qual arquivo atualizar quando um dado muda.
