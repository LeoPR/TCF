# TCF — Artigo (capitulos)

Artigo cientifico sobre o **Textual Columnar Format (TCF)**, organizado
por capitulos para facilitar leitura, revisao e derivacao em formatos
academicos (IEEE, ACM, arXiv).

**Versao**: rascunho ativo apos consolidacao M-Acomm (abr 2026).
Capitulos pre-naturalness (cap. 5, 7) precisam absorver achados
F-Q29..F-Q38. Material de v0.1 em [../archive/article_v01/](../archive/article_v01/).

---

## Capitulos

| Cap | Arquivo | Titulo | Status |
|-----|---------|--------|--------|
| 1 | [01-introduction.md](01-introduction.md) | Introducao | v0.2; precisa atualizar com Linha A x B |
| 2 | [02-related-work.md](02-related-work.md) | Trabalhos Relacionados | completo + lit-backlog |
| 3 | [03-tcf-format.md](03-tcf-format.md) | TCF: formato | v0.2 alinhado |
| 4 | [04-methodology.md](04-methodology.md) | Metodologia | v0.2; expandir para canonical + naturalidade |
| 5 | [05-results-e1-e2.md](05-results-e1-e2.md) | Encode/Decode + Compressao | completo (precisa adicionar F-Q24-Q28) |
| 7 | [07-results.md](07-results.md) | Resultados LLM | completo pre-naturalness; **REFAZER** com F-Q29-Q38 |
| 8 | [08-discussion.md](08-discussion.md) | Discussao | placeholder |
| 9 | [09-conclusion.md](09-conclusion.md) | Conclusao | placeholder |

### Apendices

| ID | Arquivo | Status |
|----|---------|--------|
| A | [appendices/A-tcf-spec.md](appendices/A-tcf-spec.md) | placeholder |
| B | [appendices/B-prompts.md](appendices/B-prompts.md) | placeholder |
| C | [appendices/C-full-tables.md](appendices/C-full-tables.md) | placeholder — preencher com tabela 2D F-Q29-Q38 |
| D | [appendices/D-format-comparison.md](appendices/D-format-comparison.md) | completo |

### Figuras

[figuras/](figuras/) — vazio. Adicionar quando capitulos consumidores
forem finalizados.

---

## Achados que entram no paper (Cap. 7 a refazer)

Catalogo completo em [../findings/](../findings/). Achados centrais
para o paper estao em [../findings/README.md](../findings/README.md).

| Bloco | Tema | F-Q range |
|-------|------|-----------|
| Origens | Capacidades fundamentais | F-Q1..F-Q12 |
| Linha B sintetica | Refinamento SQL gen | F-Q13..F-Q24 |
| Protocolo + canonical | Adult/TPC-H baseline | F-Q25..F-Q28 |
| Naturalidade N0-N3 | Achado central paper | **F-Q29..F-Q36** |
| Schema scope horizontal | Schema pruning empirico | **F-Q37..F-Q38** |

Os blocos `naturalidade` e `schema-scope` sao o **core** do paper:
36 findings cobrindo tabela 2D paradigma x dataset x familia LLM.

---

## Literatura

- **Para o paper (cap. 2)**: refs essenciais em
  [02-related-work.md](02-related-work.md)
- **Backlog de bancada**: refs auxiliares em
  [../workbench/research-notes/2026-04-25-tabular-formats-literature.md](../workbench/research-notes/2026-04-25-tabular-formats-literature.md)
  — usar quando pertinente, nao incluir todas no paper

---

## Convencoes

- Findings numerados (F-Q##) sao a fonte canonica
- Inovacoes (I##) referenciam um ou mais F-Q
- Numeros vivem em [../findings/](../findings/), capitulos referenciam
- Tickets em [../workbench/tickets/](../workbench/tickets/)

## Status pos-M-Acomm

Cap 7 precisa ser **refeito** para absorver:
- Tabela 2D paradigma x dataset (F-Q29-Q36)
- Schema scope axis (F-Q37-Q38)
- Comparativo Anthropic x OpenAI (F-Q36)

Cap 5 mantem mas adicionar tabela compressao de canonical
(Adult/TPC-H) para ancorar numeros.

Cap 8 (discussao) deve cobrir:
- Schema linking continua aberto (F-Q33-F-Q35)
- Reasoning eh o eixo (F-Q31), nao tamanho
- Schema pruning empiricamente justificado (F-Q38)
- Linha B vence Linha A em multi-tabela
