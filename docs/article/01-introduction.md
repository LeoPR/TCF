# 1. Introducao

## 1.1 Contexto

Large Language Models (LLMs) sao cada vez mais usados para raciocinar
sobre dados estruturados — responder perguntas, calcular agregacoes,
identificar padroes. LLMs recebem esses dados como texto, e a forma como
sao **serializados** afeta diretamente a capacidade do modelo de interpreta-los.

Formatos tradicionais (CSV, JSON, Markdown, HTML) sao **row-oriented**:
cada linha representa um registro completo. Isso implica:
- Nomes de colunas repetidos em cada linha (JSON)
- Valores da mesma coluna espalhados pelo texto (CSV)
- Alto overhead de tokens por informacao util

Para um modelo que processa tokens sequencialmente, localizar
"todos os valores de uma coluna" requer ler o documento inteiro.

## 1.2 Problema

### Limitacoes dos formatos atuais

1. **Token-ineficientes:** JSONL repete nomes de campo em cada linha,
   CSV tem alta entropia textual, MD Table adiciona caracteres de
   alinhamento sem informacao.

2. **Nao exploram estrutura columnar:** bancos de dados usam
   armazenamento colunar ha decadas (Parquet, ORC, ClickHouse)
   justamente porque agregacoes sao mais eficientes nessa orientacao.
   Mas nenhum formato **textual** columnar foi proposto para LLMs.

3. **Nenhum formato embute hints meta-cognitivos.** Todos tratam os
   dados como opacos, sem aproveitar que o produtor do formato pode
   pre-computar informacoes uteis (somas, contagens) que o consumidor
   (LLM) nao saberia calcular.

### Questoes de pesquisa

- **RQ1:** Um formato columnar textual comprime mais que row-oriented?
- **RQ2:** LLMs interpretam formato columnar com acuracia similar ou
  superior a formatos familiares?
- **RQ3:** Hints pre-computados (STATS) melhoram accuracy? Quanto?
- **RQ4:** A capacidade aritmetica dos modelos e o gargalo, ou e o formato?
- **RQ5:** Como a accuracy escala com o tamanho do dataset?

## 1.3 Contribuicoes

Propomos o **TCF (Textual Columnar Format)**, um formato de serializacao
textual orientado a colunas com 4 niveis progressivos de compressao
(L0-L3), construido como sublinguagem de Markdown.

### Contribuicoes comprovadas experimentalmente

1. **Primeiro formato columnar textual para LLMs** — literatura 2023-2026
   nao apresenta nenhum competitor columnar (Sui 2024, TabLLM, PoT, PAL).

2. **RLE textual como compressao LLM-friendly** — notacao `N*val`
   legivel por humanos e modelos. Comprime 10-40x em colunas com
   alta repeticao.

3. **STATS como hints meta-cognitivos** — `# STATS col: n=509 sum=...`
   elevam accuracy em 25-62pp (F90-F94). **Primeiro formato a embutir
   meta-cognicao no input.**

4. **Metodologia diagnostica 3-layer** — separa capacidade aritmetica
   (math_control), compreensao de formato (decode_only) e capacidade
   computacional (compute). Revela que modelos "que entendem TCF"
   na verdade **leem STATS** (F81).

5. **Analise de escalabilidade** — caracterizacao sistematica do
   sweet spot de accuracy (~100-200 rows) e do ponto de colapso
   (~1000 rows) para diferentes formatos.

6. **Beneficio de transporte** — TCF+gzip e 29% menor que CSV+gzip
   em 5000 rows (F70-F73). Sort+RLE+dict pre-processa os dados
   de forma que o LZ77 do gzip comprime melhor.

### Descoberta principal

> **TCF nao e apenas um formato — e uma ESTRATEGIA COMPOSTA:**
> **formato columnar compacto + hints meta-cognitivos (STATS)**
> **que compensam limitacoes aritmeticas dos LLMs.**
> **Ambos sao necessarios — sem STATS, accuracy cai 25-62pp.**

Este e um achado original. Nenhum paper anterior caracterizou
formatos LLM como "estrategias compostas" — todos os benchmarks
tratam o formato como uma escolha atomica.

## 1.4 Escopo

**Inclui:**
- Formatos textuais (CSV, JSONL, Markdown, TOON, TCF)
- Dados tabulares estruturados (dataset retail_sales sintetico)
- LLMs abertos (Ollama, 12+ modelos, 0.6B a 20B)
- Tipos classicos (string, int, float, date, boolean, null)

**Nao inclui (limitacoes conhecidas):**
- Dados binarios / base64 (ver [P-data-types](../../tickets/open/P-data-types.md))
- Modelos proprietarios (GPT-4, Claude, Gemini) — escopo Ollama open
- Datasets reais (TPC-H, WikiTableQuestions) — usa sintetico controlavel
- Multi-turn dialogues — escopo single-turn

## 1.5 Organizacao do Artigo

- **Cap 2:** Trabalhos relacionados e posicionamento vs literatura
- **Cap 3:** Design e especificacao do TCF (4 niveis)
- **Cap 4:** Metodologia (dataset, modelos, metricas, design ablativo)
- **Cap 5:** Resultados encode/decode e benchmark de compressao
- **Cap 7:** Resultados LLM (Etapas 1+2, G30, diagnostic, stats ablation, scale, transport)
- **Cap 8:** Discussao (limitacoes, ameacas a validade, trabalhos futuros)
- **Cap 9:** Conclusao

Experimentos anteriores com encoder v0.1 (dataset 41 vendas,
sem niveis de compressao) estao em [archive/article_v01/](../../archive/article_v01/)
como registro historico. O paper usa exclusivamente resultados v0.2.
