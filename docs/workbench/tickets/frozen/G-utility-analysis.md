---
title: Analise de utilidade do TCF — guia de experimentos honestos
type: guide
status: OPEN
priority: CRITICAL
created: 2026-04-10
origin: Questao fundamental — se TCF perder em todas dimensoes, nao ha motivacao para mudar de formato
---

# Analise de Utilidade do TCF — Guia Mestre

## O problema honesto

Se TCF for analisado sob multiplas dimensoes e perder em todas (ou na
maioria), nao ha motivacao cientifica para propor um formato novo.
A pergunta que precisamos responder com evidencia:

> **Existe alguma combinacao de (dimensao × cenario) onde TCF e**
> **objetivamente melhor que todas as alternativas?**

Se a resposta for sim → publicar o paper.
Se a resposta for nao → documentar por que nao, e reposicionar.

## Competidor revelado: TOON (row-oriented) evoluiu

Pesquisa 2026-04-10 revelou que TOON evoluiu significativamente desde
outubro 2024:

- **Papers arxiv:** [2603.03306](https://arxiv.org/abs/2603.03306) (fev 2026),
  [2601.12014](https://arxiv.org/abs/2601.12014) (jan 2026)
- **54% token reduction** vs JSON (benchmarks oficiais)
- **76.4% accuracy** vs JSON 75.0% (mais accuracy + menos tokens)
- **27.7 acc%/1K tokens** vs JSON 16.4 (melhor ratio)
- **Projeto ativo:** [github.com/toon-format/toon](https://github.com/toon-format/toon),
  TypeScript SDK, site oficial, docs
- **LogRocket, Medium, dev.to:** ampla cobertura em blogs de eng

### IMPORTANTE: TOON nao e columnar

TOON e row-oriented (schema declarado uma vez, depois rows).
Sintaxe:
```
users[3]{id,name,email}:
  1,Alice,alice@ex.com
  2,Bob,bob@ex.com
```

TCF continua sendo o **unico formato textual columnar para LLMs**.
TOON ataca o overhead de JSON, mas NAO reorienta dados.

**Consequencias corretas:**
1. TOON e um competidor serio **para o uso JSON → tabular**
2. TCF e unico em **agrupar por coluna** (permite RLE, sort, dict)
3. TCF pode ter vantagens em dados COM REPETICAO que TOON nao explora
4. TCF e TOON podem coexistir em nichos diferentes

## Pontos fracos conhecidos do TOON (oportunidade para TCF)

Da literatura (arxiv 2601.12014, benchmarks independentes):

1. **TOON colapsa em estruturas nao-alinhadas:** 0% de accuracy em
   alguns casos de hierarquias profundas
2. **"Prompt tax":** a instrucao explicativa do TOON consome tokens
   que reduzem a economia em contextos curtos
3. **Sem peer review robusto:** so benchmarks do proprio projeto
4. **Sem compressao textual interna:** TOON reduz overhead JSON mas
   nao tem RLE/dict/sort
5. **Sem hints meta-cognitivos:** nao tem equivalente aos STATS
6. **Performance cai em wide tables** (>100 colunas) — nao testado

**Oportunidades possiveis para TCF:**
- **Escala:** TCF testado ate 5000 rows, TOON benchmarks sao menores
- **STATS shortcut:** TCF tem hints, TOON nao
- **Compressao binaria:** TCF+gzip comprime mais que TOON+gzip? Precisa testar
- **Dados repetitivos:** RLE do TCF pode vencer TOON quando ha alta repeticao

## Dimensoes de avaliacao

Para cada formato (CSV, JSON, JSONL, MD Table, TOON, TCF L0-L3), medir:

### Dimensao 1: Tamanho bruto (bytes raw)
- Sem compressao binaria
- Por escala: 10, 50, 200, 1000, 5000 rows
- Metrica: bytes/row, % vs CSV

### Dimensao 2: Tamanho comprimido (bytes apos gzip/brotli/zstd)
- Apos compressao HTTP real
- Por algoritmo de compressao
- Metrica: ratio final, ganho vs CSV+gzip

### Dimensao 3: Tokens LLM (nao bytes)
- Tokenizacao GPT (tiktoken) e Llama (llama tokenizer)
- Por escala
- Metrica: tokens/row, % vs JSON

### Dimensao 4: Accuracy LLM
- Mesmas perguntas, mesmos modelos
- Por tipo de pergunta (sum, max, argmax, etc)
- Metrica: accuracy %, accuracy por 1K tokens

### Dimensao 5: Latencia encode
- Tempo CPU para converter dict → formato text
- Por escala
- Metrica: ms

### Dimensao 6: Latencia decode
- Tempo CPU para converter text → dict
- Por escala
- Metrica: ms

### Dimensao 7: Memoria encode/decode
- Peak memory durante operacao
- Metrica: MB

### Dimensao 8: Legibilidade humana
- Subjetiva, mas importante para debugging
- Metrica: survey (se possivel) ou heuristica

### Dimensao 9: Cross-language support
- Implementacoes disponiveis por linguagem
- Metrica: #linguagens com biblioteca

### Dimensao 10: Escala minima util
- A partir de quantas linhas o formato "ganha"?
- Metrica: crossover point vs CSV

## Questao: conversao direta vs intermediaria

**Ponto excelente do usuario:** se a fonte e SQL, converter direto para
TCF/TOON pode ser mais eficiente que SQL → CSV → TCF?

**Hipotese H-direct:** encoder direto (SQL → TCF) e >2x mais rapido que
pipeline (SQL → CSV → parse CSV → TCF).

**Motivo:** parse CSV e custoso. Se os dados ja estao tipados na fonte
(SQL, Parquet, DataFrame), ler direto preserva tipos e evita parsing.

Ja registrado parcialmente em **T-G42-input-adapters** — mas nao com
este enfoque de perfomance.

## Matriz de avaliacao final (entregavel)

```
              │ CSV │ JSON │ JSONL │ MD │ TOON │ L0 │ L2 │ L3 │
──────────────┼─────┼──────┼───────┼────┼──────┼────┼────┼────┤
Raw bytes     │ 1.0 │ 2.8  │ 2.8   │... │ 1.2  │... │... │... │
Gzipped       │ 1.0 │ 1.5  │ 1.5   │... │ 1.2  │... │... │... │
LLM tokens    │ 1.0 │ 1.8  │ 1.8   │... │ 0.5  │... │... │... │
Accuracy %    │ 50% │ 60%  │ 63%   │... │ 76%  │ 88%│... │... │
Encode ms/1K  │  5  │  3   │  3    │... │  10  │... │... │... │
Decode ms/1K  │  8  │  5   │  5    │... │  15  │... │... │... │
Peak MB       │ 10  │  8   │  8    │... │  15  │... │... │... │
Legibilidade  │ alta│ alta │ media │... │ alta │alta│alta│baixa│
Cross-lang    │ 100 │ 100  │ 100   │... │  5   │  1 │  1 │  1 │
Escala minima │  1  │  1   │  1    │... │ 10   │ 100│ 100│ 200│
```

Celulas em verde = TCF ganha. Celulas em vermelho = TCF perde.

**Honestidade obrigatoria:** se TCF ganhar so em "Accuracy %" e "Gzipped"
mas perder em tudo o mais, a pergunta e: "esse ganho compensa a complexidade
de adotar um formato novo?"

## Hipoteses testaveis (motivacao do paper)

**H-util-1:** Existe ao menos UMA dimensao onde TCF > todos (incluindo TOON).
**H-util-2:** Existe ao menos UM cenario (uso concreto) onde TCF > TOON
em PELO MENOS 3 dimensoes simultaneamente.
**H-util-3:** A combinacao "dados repetitivos + >200 rows + agregacoes com STATS"
e onde TCF domina claramente.

Se todas as 3 forem refutadas → documentar como "TCF e academicamente
interessante mas TOON e a escolha pratica".
Se pelo menos H-util-3 for confirmada → nicho claro para TCF.

## Tickets derivados (sub-guias)

Este ticket e um **guia mestre**. Os sub-tickets que ele orquestra:

| Sub-ticket | Cobre | Status |
|------------|-------|--------|
| [E-http-protocol](E-http-protocol.md) | Dimensoes 1, 2, 5, 6 (bytes, compress, encode/decode time) | NEW |
| [E-standalone-use-cases](E-standalone-use-cases.md) | Dimensao 10 (escala minima) + casos reais | NEW |
| [P-rle-vs-gzip](P-rle-vs-gzip.md) | Dimensao 2 (gzip faz o trabalho?) | NEW |
| [E-speed-tradeoffs](E-speed-tradeoffs.md) | Dimensoes 5, 6 + LLM config | NEW |
| [P-competing-formats](P-competing-formats.md) | **Expandir** com TOON benchmarks oficiais | UPDATE |
| [M-llm-scope](M-llm-scope.md) | Dimensao 4 (accuracy consolidada) | NEW |
| [T-G42-input-adapters](T-G42-input-adapters.md) | Conversao direta (SQL, Parquet) | UPDATE |
| **E-direct-conversion** (NEW) | H-direct: SQL → TCF vs SQL → CSV → TCF | TODO |
| **E-memory-profiling** (NEW) | Dimensao 7 (memoria) | TODO |
| **E-token-count** (NEW) | Dimensao 3 (tokens LLM reais) | TODO |

## Plano de execucao

### Fase 1: Benchmarks objetivos (sem LLM)
- Tamanhos raw e comprimidos (todos formatos × 6 escalas)
- Latencia encode/decode
- Memoria
- Tokens (tiktoken + llama tokenizer)
- **Tempo:** ~4h de dev, 1h de execucao

### Fase 2: TOON integration real
- Implementar encoder TOON real (hoje temos stub)
- Rodar Etapa 2 com TOON incluido (12 modelos × TOON × 8 questoes = 96 combos)
- **Tempo:** ~3h execucao

### Fase 3: Matriz completa
- Consolidar dimensoes 1-10 em uma tabela unica
- Identificar onde TCF ganha, perde, empata
- Calcular "cenarios dominantes"
- **Tempo:** 1 dia de analise

### Fase 4: Decisao
- Se TCF tem nicho claro → reescrever introducao do paper com narrativa ajustada
- Se nao tem → considerar pivotar (talvez submeter como "study of format space")

## Tarefas

- [ ] Implementar TOON encoder/decoder real
- [ ] Implementar tokenizacao (tiktoken + llama)
- [ ] Implementar profiling de memoria (tracemalloc)
- [ ] Criar E-direct-conversion, E-memory-profiling, E-token-count
- [ ] Rodar Fase 1 (benchmarks objetivos)
- [ ] Rodar Fase 2 (TOON LLM)
- [ ] Consolidar matriz final
- [ ] Decidir narrativa do paper
