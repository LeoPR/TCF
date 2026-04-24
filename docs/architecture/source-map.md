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
| Achados cientificos (F-Q1..F-Q19+) | [methodology/F-findings.md](../methodology/F-findings.md) | article/07, research-notes |
| Compression benchmark v0.2 (C1-C6) | [article/05](../article/05-results-e1-e2.md) | tickets closed |
| Etapa 1+2, M-series (F-Q1..F-Q19) | [article/07](../article/07-results.md) | F-findings, tickets closed |
| Dados brutos (JSONL) | `experiments/results/*/manifest.jsonl` | F-findings, article/07 |
| Notas de pesquisa (evidencia) | `docs/research-notes/*.md` | F-findings |

### Estrutura e conceito

| Dado | Fonte Primaria | Referenciado por |
|------|---------------|-----------------|
| Arquitetura geral | [ARCHITECTURE.md](ARCHITECTURE.md) | README.md |
| Formato TCF (spec + comparacao) | [article/03](article/03-tcf-format.md) | ARCHITECTURE.md |
| Comparacao formatos (lado a lado) | [appendix D](article/appendices/D-format-comparison.md) | article/03 |
| Inovacoes comprovadas | [article/00](article/00-innovations.md) | caps 1, 8, 9 |
| Related work + referencias | [article/02](article/02-related-work.md) | cap 1 |
| Metodologia (M-series) | [methodology/experimental-design.md](../methodology/experimental-design.md) | article/04 |
| Rigor cientifico LLM | [methodology/llm-research-rigor.md](../methodology/llm-research-rigor.md) | article/04 |
| Como rodar testes | [methodology/tests.md](../methodology/tests.md) | - |

### Codigo

| Dado | Fonte Primaria | Referenciado por |
|------|---------------|-----------------|
| Encoder (niveis 0-3) | `src/tcf/encoder_v02.py` | ARCHITECTURE, article/03 |
| Decoder | `src/tcf/decoder_v02.py` | ARCHITECTURE |
| Compressao (RLE, dict, sort) | `src/tcf/compression.py` | article/03 |
| Schema (metadata.json) | `src/tcf/schema.py` | - |
| Perguntas LLM | `experiments/eval/llm_eval/prompts.py` | article/04, appendix B |
| Ground truth | `experiments/eval/llm_eval/ground_truth.py` | article/04 |

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
    ├─> Registrar achado em F-findings.md (FONTE PRIMARIA)
    │     - Hipotese, resultado, evidencia, manifests referenciados
    │
    ├─> Adicionar research-note se metodologia nova ou alerta
    │
    ├─> Atualizar article/07-results.md (sintese para paper)
    │
    ├─> Atualizar ticket (mover open → closed)
    │
    ├─> Se inovacao comprovada: atualizar article/00-innovations.md
    │
    └─> NAO atualizar: architecture/, README, experimental-design
          (esses so mudam se a ESTRUTURA muda, nao os numeros)
```

## Hierarquia de documentos

```
README.md                          Porta de entrada (links, sem numeros)
  │
  ├── docs/architecture/overview   Estrutura e fluxo (sem numeros de resultado)
  │
  ├── docs/methodology/
  │     ├── F-findings.md          FONTE PRIMARIA de achados cientificos (F-Q1+)
  │     ├── experimental-design.md  Design M-series
  │     └── research-notes/*.md    Evidencias e diarios (referenciam F-findings)
  │
  ├── docs/article/                Sintese para publicacao (referencia F-findings)
  │     ├── 00-innovations         Inovacoes comprovadas (I1-I7+)
  │     ├── 03-tcf-format          Spec do formato + comparacao
  │     ├── 05-results-*           Benchmark compressao
  │     ├── 07-results.md          Resultados LLM M-series
  │     ├── appendices/D           Comparacao lado a lado
  │     └── (archive v0.1 movido para docs/archive/)
  │
  ├── docs/architecture/source-map.md  ESTE ARQUIVO
  │
  ├── tickets/                     Roadmap operacional
  │     ├── open/                  Tarefas ativas
  │     └── closed/                Tarefas concluidas
  │
  └── experiments/results/         Dados brutos (JSONL — fonte ultima)
        └── */manifest.jsonl
```
