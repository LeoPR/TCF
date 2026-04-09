# TCF -- Mapa de Fontes (Source of Truth)

Define qual documento e a fonte primaria de cada tipo de informacao.
Quando um dado muda, atualizar APENAS a fonte. Outros referenciam.

## Regra de ouro

**Numeros experimentais vivem em UM UNICO lugar (a fonte).
Todos os outros arquivos referenciam com link, nunca copiam o valor.**

Exemplo correto:
> TCF L0 accuracy: ver [article/07](article/07-results-e4-e8.md) Etapa 2

Exemplo errado:
> TCF L0 accuracy: 49% ← numero copiado, vai ficar obsoleto

---

## Fontes Primarias

### Resultados experimentais

| Dado | Fonte Primaria | Referenciado por |
|------|---------------|-----------------|
| Compression benchmark v0.2 (C1-C6) | [article/05](article/05-results-e1-e2.md) | tickets closed |
| Etapa 1: formato x escala (F30-F34) | [article/07](article/07-results-e4-e8.md) sec 7.3 | tickets closed |
| Etapa 2: modelos x formato (F50-F55) | [article/07](article/07-results-e4-e8.md) sec 7.4 | tickets closed |
| G30 hiperparametros | [article/07](article/07-results-e4-e8.md) (quando fechar) | tickets |
| Dados brutos (JSONL) | `experiments/results/*/manifest.jsonl` | capitulos de resultados |

### Estrutura e conceito

| Dado | Fonte Primaria | Referenciado por |
|------|---------------|-----------------|
| Arquitetura geral | [ARCHITECTURE.md](ARCHITECTURE.md) | README.md |
| Formato TCF (spec + comparacao) | [article/03](article/03-tcf-format.md) | ARCHITECTURE.md |
| Comparacao formatos (lado a lado) | [appendix D](article/appendices/D-format-comparison.md) | article/03 |
| Inovacoes comprovadas | [article/00](article/00-innovations.md) | caps 1, 8, 9 |
| Related work + referencias | [article/02](article/02-related-work.md) | cap 1 |
| Metodologia | [EXPERIMENT_DESIGN.md](EXPERIMENT_DESIGN.md) | article/04 |
| Como rodar testes | [TESTS.md](TESTS.md) | - |

### Codigo

| Dado | Fonte Primaria | Referenciado por |
|------|---------------|-----------------|
| Encoder (niveis 0-3) | `src/tcf/encoder.py` * | ARCHITECTURE, article/03 |
| Decoder | `src/tcf/decoder.py` * | ARCHITECTURE |
| Compressao (RLE, dict, sort) | `src/tcf/compression.py` | article/03 |
| Schema (metadata.json) | `src/tcf/schema.py` | - |
| Perguntas LLM | `experiments/eval/llm_eval/prompts.py` | article/04, appendix B |
| Ground truth | `experiments/eval/llm_eval/ground_truth.py` | article/04 |

\* Sera renomeado para `encoder.py` / `decoder.py` — ver ticket T-cleanup-naming.

### Tickets e roadmap

| Dado | Fonte Primaria | Referenciado por |
|------|---------------|-----------------|
| Roadmap geral | [tickets/README.md](../tickets/README.md) | README.md |
| Tickets individuais | `tickets/open/*.md` e `tickets/closed/*.md` | tickets/README.md |

---

## Fluxo de atualizacao

```
Experimento completa
    │
    ├─> Atualizar FONTE PRIMARIA (article/05 ou 07)
    │     - Numeros, tabelas, findings (F-series)
    │
    ├─> Atualizar ticket (mover open → closed)
    │
    ├─> Se inovacao comprovada: atualizar article/00-innovations.md
    │
    └─> NAO atualizar: ARCHITECTURE, README, EXPERIMENT_DESIGN
          (esses so mudam se a ESTRUTURA muda, nao os numeros)
```

## Hierarquia de documentos

```
README.md                     Porta de entrada (links, sem numeros)
  │
  ├── docs/ARCHITECTURE.md    Estrutura e fluxo (sem numeros de resultado)
  │
  ├── docs/article/           FONTE PRIMARIA de todos os resultados
  │     ├── 00-innovations    Inovacoes comprovadas
  │     ├── 03-tcf-format     Spec do formato + comparacao
  │     ├── 05-results-*      Benchmark compressao
  │     ├── 07-results-*      Etapas 1, 2, G30, etc
  │     └── appendices/D      Comparacao lado a lado
  │
  ├── docs/SOURCE_MAP.md      ESTE ARQUIVO
  │
  ├── tickets/                Roadmap operacional
  │     ├── open/             Tarefas ativas
  │     └── closed/           Tarefas concluidas
  │
  └── experiments/results/    Dados brutos (fonte ultima)
```
