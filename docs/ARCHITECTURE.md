# TCF -- Arquitetura do Projeto e do Artigo

## 1. Visao Geral

**TCF (Textual Columnar Format)** e um formato de codificacao textual compacto,
orientado a colunas, com compressao RLE, projetado para maximizar a capacidade
de LLMs de realizar raciocinio matematico sobre dados tabulares.

### Hipotese Central

TCF e construido sobre **Markdown** — formato no qual LLMs foram massivamente
treinadas. A aposta e que um formato columnar compacto escrito como sublinguagem
de MD (headers `##`, listas, notacao `N:val` para RLE) seja naturalmente
interpretavel por modelos que ja "sabem ler" Markdown.

A compactacao usa tecnicas inspiradas em bancos colunares:
- **RLE** para repeticoes (`N:val`)
- **Orientacao colunar** (todos os valores de um campo numa linha)
- **Associacoes dedutiveis** (indices, FKs, sorted columns) onde a estrutura
  permite que a LLM deduza relacoes sem que sejam explicitas

### Pergunta Central de Pesquisa

> Dados compactados em formato columnar baseado em Markdown (TCF) permitem
> que LLMs realizem raciocinio matematico com a mesma ou melhor precisao
> que formatos expandidos (CSV/JSON), usando menos tokens?

### Objetivo Final

1. **Biblioteca `tcf`** — encoder/decoder distribuivel via `pip install tcf`, simples de usar
2. **Guia de uso** — como orientar pessoas a tirar boas conclusoes dos dados com TCF
3. **Artigo cientifico** — evidencia experimental comparando formatos, com testes cruzados
4. **Pipeline reproduzivel** — rodar com Ollama local E APIs online (OpenAI, Claude, Gemini)
5. **Comprovacao cientifica** — verificar se LLMs realmente entendem TCF, com que grau, e quando

---

## 2. Estrutura do Repositorio

```
TCF/
├── src/tcf/                    Biblioteca distribuivel (pip install -e .)
│   ├── encoder.py              CSV + metadata -> TCF text
│   ├── decoder.py              TCF text -> dict[table -> rows]
│   ├── schema.py               Parser de metadata.json
│   ├── cli.py                  CLI: tcf encode | decode | info
│   └── __init__.py             Exporta encode, decode, EncoderConfig
│
├── experiments/                Pipeline de avaliacao cientifica
│   ├── eval/                   Harness de avaliacao (python -m experiments.eval)
│   │   ├── run_matrix.py       Pipeline em fases com ablacao
│   │   ├── analyze_phase1.py   Analise de resultados Phase 1
│   │   └── llm_eval/           Modulos internos (client, formats, metrics, prompts)
│   └── results/                Outputs (JSONL + manifests, .gitignored)
│
├── tests/                      Testes unitarios (pytest, 151 testes)
│   ├── test_g01_encode_decode.py   Progressivo L0-L6 + variantes + stats
│   ├── test_g01_compression.py     Benchmark sintetico compressao
│   ├── fixtures/               Dados de teste (deterministicos + sinteticos)
│   └── ...
│
├── data/                       Dataset de referencia
├── docs/                       Documentacao (ARCHITECTURE, EXPERIMENT_DESIGN, TESTS, ARTICLE)
├── tickets/                    Tickets individuais de pesquisa (T/P/H series)
├── tickets/README.md                  Roadmap mestre (indice de todos os tickets)
└── README.md                   Guia macro do projeto
```

### Principio de Separacao

| Camada | Proposito | Depende de LLM? |
|--------|-----------|-----------------|
| `src/tcf/` | Biblioteca core (encode/decode) | Nao |
| `tests/` | Testes unitarios deterministicos | Nao |
| `experiments/eval/` | Pipeline de avaliacao | Sim (Ollama) |
| `docs/` | Documentacao | Nao |

---

## 3. Arquitetura de Software

### 3.1 Camada Core (`src/tcf/`)

Biblioteca com **zero dependencias externas**. Pode ser instalada independentemente:

```
pip install -e .
```

**Fluxo do Encoder:**
```
metadata.json ──> load_schema() ──> [TableMeta, ...]
                                         │
CSV files ─────────────────────> rows ──>│
                                         v
                               encode_table(rows, meta, config)
                                         │
                  ┌──────────────────────┤
                  v                      v
           _encode_numeric()      _encode_fk()
           (raw_float|int|bins)   (id_raw|dict|hint|inline)
                  │                      │
                  └──────────┬───────────┘
                             v
                      _rle_encode()  (se sorted=True)
                             │
                             v
                   _stats_lines()  (se include_stats=True)
                             │
                             v
                        TCF text
```

**Variantes do EncoderConfig:**

| Variante       | numeric    | fk_mode  | sorted | Reversivel | Descricao |
|----------------|------------|----------|--------|------------|-----------|
| `tcf_raw`      | raw_float  | id_raw   | nao    | sim        | Baseline minimo |
| `tcf_sorted`   | raw_float  | id_raw   | sim    | sim        | + colunas ordenadas |
| `tcf_dict`     | raw_float  | dict     | sim    | sim        | + dicionario FK |
| `tcf_hint`     | raw_float  | hint     | sim    | sim        | + hint de nomes |
| `tcf_inline`   | raw_float  | inline   | sim    | sim*       | Nomes resolvidos |
| `tcf_int`      | int_scaled | dict     | sim    | sim        | Inteiros escalados |
| `tcf_bins`     | bins_16    | dict     | nao    | nao (lossy)| Quantizado em bins |

*inline: nomes resolvidos, sem recuperacao de IDs originais

**Features opcionais do encoder:**
- `include_stats=True` — emite `# STATS` com n, sum, min, max, avg (numerico) e distinct, mode (categorico)
- `include_sorted=True` — emite colunas `[sorted]` com RLE para distribuicao
- `encode_with_report()` — retorna EncodeReport com telemetria (elapsed_s, compression_ratio)

### 3.2 Clients LLM (multi-provider)

O pipeline suporta multiplos backends para chamadas LLM:

```
LLMClient (interface)
     │
     ├── OllamaClient      Modelos locais (llama, qwen, gemma, phi, etc.)
     ├── OpenAIClient       GPT-4o, GPT-4o-mini via API  (planejado)
     ├── AnthropicClient    Claude Sonnet/Opus via API    (planejado)
     └── GoogleClient       Gemini Pro/Flash via API      (planejado)
```

**Fase atual:** OllamaClient implementado (modelos locais quantizados).
**Proxima fase:** Adicionar clientes API para validar resultados em
modelos de frontier (nao quantizados, maiores, mais capazes).

**Justificativa cientifica:** Modelos locais quantizados podem ter
comportamento diferente de APIs comerciais. Para o artigo ser robusto,
precisamos confirmar os achados com pelo menos 2 classes de modelos:
locais (Ollama) e APIs (OpenAI/Claude/Gemini).

### 3.3 Rigor Cientifico e Metodologia

**Principio:** Nunca afirmar "bom" ou "ruim". Medir com metodologia rigorosa
e excluir hipoteses alternativas por teste e exclusao.

**Modos de interacao LLM x dados (progressao de complexidade):**

```
Nivel 1: Direct         "Qual a soma de vl?" → numero
Nivel 2: CoT            "Pense passo a passo..." → raciocinio + numero
Nivel 3: PoT            "Escreva codigo Python..." → codigo executavel
Nivel 4: PoT+Verify     "Gere um script de analise..." → ferramenta standalone
Nivel 5: Text-to-Insight "O que voce observa nos dados?" → narrativa analitica
```

**Nivel 3 (PoT) e critico:** nosso erro dominante e arithmetic_error (62%).
O modelo ENTENDE o formato mas ERRA a conta. Se ele gerar codigo,
a aritmetica e feita pela maquina, nao pelo modelo.

**Nivel 4 (PoT+Verify):** o modelo gera uma ferramenta que a pessoa executa
nos dados originais. Transforma TCF de "formato para LLM ler" em
"formato para LLM gerar ferramentas de analise".

**Nivel 5 (Insight):** respostas relativas, tendencias, comparacoes.
"Bob vende mais que Alice", "Caneta e o top produto", "novembro cai".
Avaliacao por checklist de insights esperados (nao exact-match).

**Hipotese central:** TCF columnar pode FACILITAR code-gen porque os dados
ja estao em formato array (`vl: 2.5 11 1 ...` → `vl = [2.5, 11, 1, ...]`).
JSONL exige parsing mais complexo para gerar codigo equivalente.

**Protocolo de medicao:**
- temperature=0, seed=42 para reproducibilidade baseline
- Repeticoes 3x para significancia (G08-T03)
- Baseline random/majority para floor de accuracy
- CI 95% para intervalos de confianca

**Posicionamento na literatura:**
- Nenhum trabalho publicado testa formato columnar comprimido para LLMs
- Surveys (Sui et al., 2024) testam CSV/JSON/MD/HTML/NL — todos row-oriented
- RLE como "compressao natural" e conceito original deste trabalho
- A hipotese de que LLMs entendem Markdown implica que TCF (sub-MD) pode ser decifravel

### 3.4 Camada de Avaliacao (`experiments/eval/`)

**Pipeline em fases com ablacao progressiva:**

```
Phase 0 ──> Encode/Decode gate (sem LLM)
                │ 7/7 pass?
                v
Phase 1 ──> Formatos basicos (CSV, JSONL, TCF)
            x N modelos (auto-discovery)
            x 3 camadas diagnosticas
                │ filtra modelos (accuracy >= threshold)
                v
Phase 2 ──> Variantes TCF (3 numeric x 4 fk x 2 sorted = 24)
            x modelos sobreviventes
                │ seleciona top configs
                v
Phase 3 ──> Escala + interacoes
            x top modelos x top configs x dados maiores
                │
                v
Analise ──> Testes estatisticos + figuras + artigo
```

### 3.3 Sistema de Perguntas (3 Camadas Diagnosticas)

```
Layer 0: math_control    Aritmetica pura, sem formato — "some esses valores"
Layer 1: decode_only     Leitura do formato — "liste todos os valores de vl"
Layer 2: compute         Formato + operacao — "qual a soma de vl?"
```

**Niveis de complexidade (planejados):**
- **Basico:** agregacoes simples (sum, avg, count, min, max)
- **Intermediario:** FK-dependentes ("quantas vendas Ana fez?", "top product")
- **Avancado:** multi-step ("quem vendeu mais?", "pessoas que compraram mais X")
- **Decode reverso:** LLM gera CSV a partir de TCF (testar compreensao total)
- **Perguntas progressivas:** sequencia de perguntas que orientam a LLM

### 3.5 Formatos Comparados

| Formato | Orientacao | Familiar LLM? | Compacta? | Descricao |
|---------|-----------|----------------|-----------|-----------|
| CSV | Row | Sim (treinamento) | Moderada | Header + linhas separadas por virgula |
| JSONL | Row | Sim (treinamento) | Nao (chaves repetidas) | Objeto JSON por linha |
| Markdown Table | Row | Sim (treinamento) | Nao (pipes, alinhamento) | Tabela visual com `\|` e `---` |
| TOON | Row | **Nao** (formato novo) | Moderada (header tipado) | CSV-like com metadata header |
| TCF | **Column** | **A verificar** (baseado em MD) | **Sim** (RLE, columnar) | Sublinguagem de MD com compressao |

**Nota critica sobre familiaridade:**
- CSV, JSONL, Markdown Table: LLMs viram bilhoes de exemplos no treinamento
- TOON: formato **novo**, layout similar a CSV mas LLMs nunca viram antes
- TCF: formato **novo**, mas construido sobre sintaxe Markdown (headers, listas)
  A hipotese e que a base MD torna TCF mais decifravel que um formato totalmente alienigena

**Referencia academica principal:** Sui et al. (2024), "Table Meets LLM" — survey
de serialization strategies (HTML, Markdown, CSV, JSON, NL) para LLMs.
TCF seria o primeiro formato columnar comprimido proposto nesse espaco.

### 3.6 Modos de Reducao de Dados

Quando o volume de dados excede o contexto do modelo, ha 3 estrategias:

```
           Dados originais (10K vendas, ~35K tokens)
                    │
      ┌─────────────┼─────────────┐
      v             v             v
  COMPRESSAO    AGRUPAMENTO    PERSPECTIVA
  (RLE, TCF)    (GROUP BY)     (VIEW/filtro)
      │             │             │
  10K valores   900 grupos    Subset focado
  ~35K tokens   ~5.5K tokens  ~2K tokens
      │             │             │
  Preserva:     Preserva:     Preserva:
  - individuais - agregacoes  - detalhes
  - distribuicao- top-N       - do foco
  - tudo        - combinacoes - perspectiva
      │             │             │
  Perde:        Perde:        Perde:
  - nada        - individuais - fora do foco
  (se cabe)     - distribuicao
```

**Trade-off fundamental:**
- **Compressao** (RLE) e lossless mas tem limite (N tokens = N valores)
- **Agrupamento** e destrutivo mas escala por combinacoes (K), nao por volume (N)
- **Perspectiva** e filtro dimensional (WHERE/focus) — reduz N diretamente

**Hybrid (agrupado + STATS):** combina agrupamento com estatisticas globais.
Recupera min/max/avg/sum sem custo significativo. Melhor dos dois mundos
quando o volume nao cabe no contexto.

**Decisao para o usuario:**
1. Cabe no contexto? → RAW (maximo de informacao)
2. Nao cabe? → GROUPED + STATS (perde detalhes, mantem agregacoes)
3. Pergunta especifica? → VIEW primeiro, depois TCF

### 3.7 Dados Sinteticos

**Principio:** um super-sistema de tabelas sinteticas do qual se derivam subsets
menores (como views), permitindo testar hipoteses variadas sem criar dados novos.

**Geradores existentes (`tests/fixtures/synthetic.py`):**

| Gerador | Descricao | Controles |
|---------|-----------|-----------|
| `crm_sales(n, c, p)` | E-commerce com FK Zipf | rows, clientes, produtos |
| `service_logs(n)` | Logs API (5 status codes) | rows |
| `survey_likert(r, q)` | Pesquisa 1-5 | respondentes, perguntas |
| `unique_data(n)` | Tudo unico (worst case) | rows |

**Evolucao planejada:** gerador parametrico unificado que produz datasets
de complexidade arbitraria, com FK chains, tipos mistos, e distribuicoes
configuraveis — permitindo derivar qualquer cenario como view.

### 3.8 CLI e Biblioteca (Visao Futura)

O CLI refletira as praticas descobertas nos experimentos:

```bash
# Modo atual (explicito)
tcf encode --meta meta.json --data-dir data/ --fk-mode dict --stats

# Modos planejados (derivados dos experimentos)
tcf encode --for-llm meta.json data/       # Shortcut: dict+stats+smart
tcf encode --mode flat meta.json data/     # Supertable (join tudo)
tcf encode --mode grouped --by pessoa,produto meta.json data/  # GROUP BY
tcf encode --mode view --where "produto=Caneta" meta.json data/  # Filtro
tcf encode --precision smart meta.json data/  # Arredondamento inteligente
tcf auto meta.json data/                   # Detecta e aplica best config
```

**Arredondamento inteligente (`--precision smart`):**
- Detecta colunas financeiras (2 casas) e inteiras (sem decimal)
- Calcula erro maximo e emite warning no header TCF
- A LLM recebe o aviso e considera margem de erro
- Requer testes extensivos antes de publicar (erros de arredondamento
  podem inverter rankings e acumular em somas)

### 3.9 Scoring e Metricas

```
Resposta LLM
     │
     v
strip_think()          Remove <think>...</think>
     │
     v
extract_number()       Ultimo numero, normaliza virgula pt-BR
     │
     v
score_response()       Compara com ground truth (tolerancia 1%)
     │
     v
classify_error()       7 categorias:
                       correct | list_instead_of_agg | wrong_count |
                       hallucinated | arithmetic_error | refusal | parse_failure
```

---

## 4. Arquitetura do Artigo

### 4.1 Estrutura Proposta

```
1. Introducao
   - Contexto: LLMs precisam raciocinar sobre dados estruturados
   - Problema: formatos expandidos (CSV/JSON) sao token-ineficientes
   - Contribuicao: TCF — formato columnar compacto com RLE

2. Trabalhos Relacionados
   - Formatos tabulares para LLMs (CSV, JSON, Markdown, TOON)
   - Compressao de contexto para LLMs
   - Benchmarks de raciocinio numerico

3. TCF: Textual Columnar Format
   3.1 Design e motivacao (sublinguagem de Markdown)
   3.2 Sintaxe e semantica (RLE, sorted, FK modes)
   3.3 Variantes de encoding (numeric, FK, sort, stats)
   3.4 Complexidade e compressao teorica

4. Metodologia
   4.1 Datasets (referencia + sinteticos)
   4.2 Banco de perguntas (3 camadas + niveis progressivos)
   4.3 Ground truth programatico (nunca hardcoded)
   4.4 Metricas: accuracy, token count, latencia
   4.5 Design experimental em fases (ablacao progressiva)
   4.6 Formatos comparados e seus pressupostos

5. Experimentos e Resultados
   5.1 Benchmark de compressao (TCF vs CSV vs JSONL)
   5.2 Phase 0: Reversibilidade encode/decode (H01)
   5.3 Phase 1: Efeito principal do formato (H02, H03)
   5.4 Phase 2: Ablacao de variantes TCF (H04-H06)
   5.5 Phase 3: Escala + interacoes (H07-H10)
   5.6 Testes avancados: decode reverso, perguntas progressivas
   5.7 Analise Pareto: accuracy x tokens (H09)

6. Discussao
   - Quando TCF ajuda e quando nao
   - RLE: beneficio real vs overhead
   - Compressao vs interpretabilidade
   - Stats como hints gratuitos
   - Limitacoes e ameacas a validade

7. Conclusao e Trabalhos Futuros
   - Guia pratico de uso do TCF
   - Extensoes (streaming, chunking, tipos complexos)

Apendices
   A. Especificacao completa do formato TCF
   B. Tabelas de resultados completas
   C. Prompts e system prompts utilizados
   D. Comparacao detalhada TCF vs TOON
```

### 4.2 Mapeamento Hipoteses -> Secoes

| Hipotese | Secao | Contribuicao |
|----------|-------|--------------|
| H01 | 5.2 | Sanity gate (pre-requisito) |
| H02 | 5.3 | Resultado principal: formato afeta accuracy? |
| H03 | 5.3 | Diagnostico: onde esta o gargalo? |
| H04 | 5.4 | Ablacao: numeric encoding |
| H05 | 5.4 | Ablacao: sort mode |
| H06 | 5.4 | Ablacao: FK representation |
| H07 | 5.5 | Interacao: model size |
| H08 | 5.5 | Interacao: model family |
| H09 | 5.7 | Analise de eficiencia (Pareto) |
| H10 | 5.5 | Escalabilidade |

### 4.3 Figuras Planejadas

1. **Accuracy heatmap**: formato x modelo (Phase 1)
2. **Bar chart 3 camadas**: math_control vs decode vs compute per format
3. **Ablation table**: variantes TCF com deltas (Phase 2)
4. **Pareto scatter**: accuracy vs token count
5. **Scaling curve**: accuracy vs chunk size
6. **Error distribution**: stacked bar por tipo de erro
7. **Compression table**: TCF vs CSV vs JSONL por cenario

---

## 5. Estagios do Artigo (Progressao Experimental)

Cada estagio produz evidencia para uma secao do artigo:

### E1: Encode/Decode funciona? (Pre-requisito)
- Testes unitarios progressivos L0-L6
- Phase 0 gate: 7/7 configs reversiveis
- **Secao do artigo:** 5.2

### E2: Comprime? Quando comprime? (Benchmark)
- Dados sinteticos com 7 cenarios (CRM, logs, survey, unique)
- Medir TCF vs CSV vs JSONL em tamanho bruto
- Medir eficiencia do RLE por cardinalidade
- **Secao do artigo:** 5.1

### E3: LLMs entendem? (Compreensao de formato)
- Phase 1: formatos basicos x modelos
- 3 camadas diagnosticas isolam onde o modelo falha
- Encode "pobre" (sem stats/hints) vs "rico" (com stats)
- **Secao do artigo:** 5.3

### E4: Qual variante TCF e melhor? (Ablacao)
- Phase 2: 24 variantes TCF x modelos sobreviventes
- FK mode e a variavel mais impactante (names vs IDs)
- Numeric encoding afeta precisao aritmetica
- **Secao do artigo:** 5.4

### E5: LLMs deduzem coisas nao explicitas? (Raciocinio)
- Perguntas que exigem calculo nao fornecido (sum, avg, count)
- Comparar encode com stats (hints prontos) vs sem stats
- Se LLM acerta com hints, valida que stats sao uteis
- Se acerta SEM hints, TCF e intrinsecamente interpretavel
- **Secao do artigo:** 5.3 + 6

### E6: LLMs fazem decode? (Compreensao total)
- Mandar TCF comprimido e pedir para gerar CSV original
- Testar se a LLM entende a estrutura completa
- **Secao do artigo:** 5.6

### E7: Perguntas progressivas (Orientacao)
- Sequencia de perguntas que guiam a LLM
- "Quantas linhas tem?" -> "Qual a soma de vl?" -> "Quem comprou mais?"
- Testar se orientacao melhora accuracy tanto em TCF quanto nativos
- Se melhora em ambos, a tecnica e geral; se so em TCF, e especifica
- **Secao do artigo:** 5.6 + 6

### E8: Perguntas complexas (top-N)
- "Quem vendeu mais?" / "Pessoas que compraram mais Abacaxi"
- Exige: leitura + FK resolution + agregacao + ranking
- Possibilidade de dados de suporte (hints com totais por grupo)
- **Secao do artigo:** 5.6

---

## 6. Convencoes e Boas Praticas

### 6.1 Invocacao

Sempre usar modulo Python, nunca path direto:
```bash
python -m tcf encode --meta data/metadata.json --data-dir data/
python -m experiments.eval phase1 --models auto
python -m pytest tests/ -v
```

### 6.2 Resultados

- Todos os resultados em `experiments/results/` (gitignored)
- Formato: JSONL (uma linha JSON por resultado)
- Manifest para idempotencia (pode interromper e retomar)
- Nunca commitar resultados brutos no git

### 6.3 Ground Truth

- NUNCA hardcodar valores esperados
- Sempre derivar de `ground_truth.compute(data_dir)`
- Se o dataset mudar, todo o pipeline se ajusta automaticamente

### 6.4 Documentacao

| Arquivo | Funcao | Conteudo |
|---------|--------|----------|
| README.md | GitHub | O que e, como usar, quick start |
| docs/ARCHITECTURE.md | Pilar conceitual | Estrutura, intencoes, fluxos — NUNCA resultados |
| docs/EXPERIMENT_DESIGN.md | Metodologia | Design das fases, estimativas, criterios |
| docs/TESTS.md | Registro | Testes feitos, por capitulo, fixtures, coverage |
| docs/ARTICLE.md | Indice | Redireciona para docs/article/ (capitulos) |
| docs/article/ | Meta-artigo | Capitulos separados (01-09 + appendices) |
| tickets/README.md | Roadmap | Status de todos os tickets G01-G13 |

**Principio:** Cada documento tem UMA responsabilidade. Resultados experimentais
ficam APENAS nos capitulos do artigo (docs/article/05-07). Arquitetura e intencoes
ficam APENAS aqui. README e macro. TICKETS e operacional.

**Rastreabilidade:** Ver [SOURCE_MAP.md](SOURCE_MAP.md) para saber qual
arquivo e a fonte primaria de cada dado e como propagar mudancas.
