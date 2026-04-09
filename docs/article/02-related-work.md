# TCF -- Trabalhos Relacionados e Posicionamento Cientifico

## 1. Estado da Arte: Formatos Tabulares para LLMs

### 1.1 Surveys e Papers Principais

| Paper | Ano | Contribuicao | Formatos testados |
|-------|-----|-------------|-------------------|
| Sui et al., "Table Meets LLM" | 2024 | Survey de serialization | HTML, Markdown, CSV, JSON, NL |
| Hegselmann et al., "TabLLM" | 2023 | Serialization para classificacao | Key-value templates |
| Singha et al., "Tabular Representation" | 2023 | Impacto de ruido/estrutura | CSV, JSON, MD, HTML |
| Chen, "DATER" | 2023 | Decomposicao de perguntas | - |
| Chen et al., "Program of Thoughts" | 2023 | Gerar codigo ao inves de resposta | - |
| Gao et al., "PAL" | 2023 | Program-Aided Language Models | - |
| Wang et al., "Self-Consistency" | 2023 | Majority voting sobre N respostas | - |
| Jiang et al., "LLMLingua" | 2023 | Compressao de prompt por token pruning | - |

### 1.2 Achados Consolidados

**Sobre formatos:**
- Formato importa, mas **menos que capacidade do modelo** (Sui et al.)
- Markdown e HTML tendem a performar melhor que CSV/JSON (Sui et al.)
- Efeito do formato **diminui com escala do modelo** (Hegselmann et al.)
  - Consistente com nosso F2: gap TCF-JSONL e 15pp em modelos fortes vs 23pp em fracos
- Diferenca de formato tipicamente < 10-15pp no mesmo benchmark
  - Nosso gap Phase 1: 20pp (JSONL-TCF) — dentro da faixa, mas alto
- **Regularidade estrutural** (delimitadores consistentes) melhora accuracy (Singha et al.)

**Sobre tecnicas de prompting:**
- Chain-of-thought (CoT) ajuda mas tem retorno decrescente em raciocinio numerico complexo
- **Program-of-Thought (PoT) e a tecnica mais eficaz** para tarefas aritmeticas sobre tabelas
  - Relevante: nosso erro dominante e arithmetic_error (62%)
- Self-consistency (majority voting) melhora 5-15% em reliability
- Decomposicao de perguntas (DATER) ajuda em tabelas grandes
  - Relevante: nossa proposta de perguntas progressivas (G06)

**Sobre benchmarks:**
- WikiTableQuestions, SQA, TabFact, FeTaQA, HybridQA, BIRD, Spider
- Metricas: exact-match accuracy, execution accuracy (SQL), F1
- Maioria usa temperature=0, greedy decoding
- Poucos reportam token counts junto com accuracy

### 1.3 O que NAO existe (lacuna que o TCF preenche)

| Lacuna | TCF |
|--------|-----|
| Nenhum formato columnar testado para LLMs | TCF e o primeiro |
| Nenhuma compressao (RLE) no input de LLMs | TCF usa RLE nativo |
| Ninguem separa compreensao de formato vs capacidade aritmetica | Nosso 3-layer diagnostic (math_control/decode/compute) |
| Ninguem varia FK representation sistematicamente | Nosso Phase 2 (id_raw/dict/hint/inline) |
| Ninguem reporta Pareto accuracy×tokens | Nosso H09 |
| Ninguem testa modelos locais quantizados vs formato | Nosso setup Ollama |

---

## 2. Posicionamento do Artigo

### 2.1 Contribuicoes Originais

1. **Primeiro formato columnar comprimido para LLMs** — TCF com RLE, sorted columns, FK modes
2. **Metodologia diagnostica 3-layer** — separa math ability, format comprehension, compute
3. **Ablacao sistematica de componentes** — numeric encoding × FK mode × sort mode
4. **Pareto accuracy × token efficiency** — tradeoff nao explorado na literatura
5. **Supertable mode** — desnormalizacao como variante de serialization

### 2.2 Angulo Principal do Paper

O paper NAO deve argumentar que TCF "e melhor que CSV/JSONL em accuracy".
Os dados de Phase 1 mostram que nao e (43% vs 63%).

O angulo forte e:
- **Novo ponto na fronteira Pareto**: TCF e mais compacto (3-6x vs JSONL),
  gera respostas mais rapidas (27% no gpt-oss), e competitivo em modelos capazes (85% vs 100%)
- **A metodologia diagnostica 3-layer** revela *por que* modelos falham —
  contribuicao independente do TCF
- **Compressao natural via RLE** e um conceito inedito para serialization de tabelas
- **A familiaridade com Markdown** pode ser um vetor de melhoria futura
  (training data augmentation, fine-tuning em TCF)

### 2.3 Ancora na Literatura

**Citar como principal referencia:**
> Sui et al. (2024), "Table Meets LLM: Can Large Language Models
> Understand Structured Table Data?" — survey de serialization strategies

**Posicionar TCF como:**
> A primeira entrada columnar na taxonomia de serialization de Sui et al.
> Enquanto todos os formatos testados (CSV, JSON, MD, HTML, NL) sao
> row-oriented, TCF explora a dimensao ortogonal de orientacao de dados.

---

## 3. Implicacoes para Metodologia

### 3.1 O que devemos fazer por rigor

| Pratica | Status | Nota |
|---------|--------|------|
| temperature=0 | IMPLEMENTADO | DEFAULT_OPTIONS |
| Reportar token counts por formato | IMPLEMENTADO | prompt_tokens em cada resultado |
| Repeticoes 3x com CI | PLANEJADO (G08-T03) | Bootstrap CI |
| Baseline random/majority | PLANEJADO (G11-T07) | Floor de accuracy |
| McNemar's test para pares | PLANEJADO (G12) | Formato A vs B no mesmo dataset |
| Bonferroni correction | PLANEJADO (G12) | Multiplas comparacoes |
| Program-of-Thought condition | PLANEJADO (G11-T03) | Alto impacto: resolve 62% arithmetic_error |

### 3.2 PoT como teste critico

Se adicionarmos uma condicao PoT ("escreva codigo Python que calcule"):
- E TCF facilitar geracao de codigo (dados ja colunares → array slicing natural)
- Enquanto JSONL dificultar (precisa parsear JSON)
- **Seria um achado de alto impacto:** TCF pior em direct prompting mas melhor em PoT

### 3.3 Reconhecer o vies de Phase 1

CSV/JSONL recebem dados desnormalizados (pre-JOIN).
TCF recebe dados normalizados (3 tabelas + FK).
Documentar explicitamente. Phase 2 inline corrige.

---

## 4. Referencias para o Paper

## 5. Benchmarks e Datasets de Referencia

### Table QA Benchmarks

| Benchmark | Tabelas | Perguntas | Rows avg | Cols avg | Relacional? |
|-----------|---------|-----------|----------|----------|-------------|
| WikiTableQuestions | 2108 | 22033 | 20-30 | 5-8 | Nao (flat) |
| SQA | 982 | 6066 | 15-25 | 5-7 | Nao (flat) |
| TabFact | 16573 | 118439 | ~14 | ~6 | Nao (flat) |
| Spider | 200 DBs | 10181 SQL | variado | variado | Sim (multi-table) |
| BIRD | 95 DBs | 12751 SQL | ate milhoes | variado | Sim (dirty data) |

Nosso dataset (30+12+41 rows, 3 tabelas com FK) esta entre os benchmarks
flat simples (WikiTQ) e os multi-DB complexos (Spider/BIRD).

### Datasets Reais Candidatos

- **TPC-H**: 8 tabelas, ratio customer:order 1:10, benchmark SQL canonico
- **Olist (Kaggle)**: e-commerce brasileiro, 9 tabelas, 100K orders, portugues
- **UCI Adult**: 48842 rows, 14 cols, classificacao

### Geracao de Dados Sinteticos

Referencia principal: Gray et al. (1994) "Quickly Generating Billion-Record
Synthetic Databases" — descreve distribuicoes Zipf, self-similar, uniform.

Nosso gerador (crm_sales) usa Zipf com s~0.8 para FKs. Ratios atuais
(customer:order 1:1.4) sao irrealisticamente baixos — TPC-H usa 1:10.

### Rigor Estatistico

- Bootstrap CI: Efron & Tibshirani (1993), 10000 resamples, BCa intervals
- McNemar's test: comparacoes pareadas de accuracy
- Cohen's h: effect size para proporcoes
- Bonferroni: correcao para multiplas comparacoes (k formatos)

---

## 6. Referencias para o Paper

```bibtex
@article{sui2024table,
  title={Table Meets LLM: Can Large Language Models Understand Structured Table Data?},
  author={Sui, Yuan and others},
  year={2024}
}

@article{hegselmann2023tabllm,
  title={TabLLM: Few-shot Classification of Tabular Data with Large Language Models},
  author={Hegselmann, Stefan and others},
  year={2023}
}

@article{singha2023tabular,
  title={Tabular Representation, Noisy Operators, and Impacts on Table Structure Understanding},
  author={Singha, Ananya and others},
  year={2023}
}

@article{chen2023program,
  title={Program of Thoughts Prompting},
  author={Chen, Wenhu and others},
  year={2023}
}

@article{gao2023pal,
  title={PAL: Program-Aided Language Models},
  author={Gao, Luyu and others},
  year={2023}
}

@article{wang2023selfconsistency,
  title={Self-Consistency Improves Chain of Thought Reasoning in Language Models},
  author={Wang, Xuezhi and others},
  year={2023}
}

@article{jiang2023llmlingua,
  title={LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models},
  author={Jiang, Huiqiang and others},
  year={2023}
}

@inproceedings{gray1994synthetic,
  title={Quickly Generating Billion-Record Synthetic Databases},
  author={Gray, Jim and others},
  booktitle={SIGMOD},
  year={1994}
}

@book{efron1993bootstrap,
  title={An Introduction to the Bootstrap},
  author={Efron, Bradley and Tibshirani, Robert J.},
  year={1993},
  publisher={Chapman and Hall/CRC}
}

@inproceedings{pasupat2015wikitq,
  title={Compositional Semantic Parsing on Semi-Structured Tables},
  author={Pasupat, Panupong and Liang, Percy},
  booktitle={ACL},
  year={2015}
}

@inproceedings{yu2018spider,
  title={Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Database Semantic Parsing and Text-to-SQL},
  author={Yu, Tao and others},
  booktitle={EMNLP},
  year={2018}
}

@article{yin2023instructions,
  title={Did You Read the Instructions? Rethinking the Effectiveness of Task Definitions in Instruction Learning},
  author={Yin, Fan and others},
  year={2023}
}

@article{brown2020gpt3,
  title={Language Models are Few-Shot Learners},
  author={Brown, Tom and others},
  journal={NeurIPS},
  year={2020}
}
```
