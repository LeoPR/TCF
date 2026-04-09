# TCF -- Meta-Artigo (Capitulos)

Artigo cientifico completo sobre o Textual Columnar Format.
Cada capitulo e um arquivo separado para facilitar leitura, revisao e derivacao
para diferentes formatos academicos (IEEE, ACM, arXiv, etc).

## Indice

## Inovacoes Teoricas

| Arquivo | Descricao |
|---------|-----------|
| [00-innovations.md](00-innovations.md) | Inovacoes comprovadas (I1-I5) + pendentes (I6-I12) |

Atualizado conforme resultados sao confirmados. Apenas inovacoes comprovadas
por experimentos sao registradas como definitivas.

---

## Capitulos

| Cap | Arquivo | Titulo | Status |
|-----|---------|--------|--------|
| 1 | [01-introduction.md](01-introduction.md) | Introducao | Rascunho |
| 2 | [02-related-work.md](02-related-work.md) | Trabalhos Relacionados | Completo |
| 3 | [03-tcf-format.md](03-tcf-format.md) | TCF: Textual Columnar Format | Rascunho |
| 4 | [04-methodology.md](04-methodology.md) | Metodologia | Rascunho |
| 5 | [05-results-e1-e2.md](05-results-e1-e2.md) | Encode/Decode + Compressao | Completo |
| 6 | [06-results-e3.md](06-results-e3.md) | Phase 1: Compreensao de Formato | Completo |
| 7 | [07-results-e4-e8.md](07-results-e4-e8.md) | Ablacao, Deduction, Avancados | Placeholder |
| 8 | [08-discussion.md](08-discussion.md) | Discussao | Placeholder |
| 9 | [09-conclusion.md](09-conclusion.md) | Conclusao | Placeholder |

### Apendices

| ID | Arquivo | Titulo | Status |
|----|---------|--------|--------|
| A | [appendices/A-tcf-spec.md](appendices/A-tcf-spec.md) | Especificacao TCF | Placeholder |
| B | [appendices/B-prompts.md](appendices/B-prompts.md) | Prompts utilizados | Placeholder |
| C | [appendices/C-full-tables.md](appendices/C-full-tables.md) | Tabelas completas | Placeholder |

## Como usar

Este meta-artigo serve como fonte primaria para derivar artigos em formatos especificos:
1. Ler capitulos na ordem (1-9) para a historia completa
2. Cada capitulo e auto-contido com suas referencias internas
3. Para submissao: selecionar e condensar capitulos conforme limites do venue
4. Apendices contem dados de suporte que podem ser incluidos ou omitidos

## Convencoes

- Resultados experimentais **so** nos capitulos 5-7 (nunca no 1-4)
- Findings numerados (F1, F2, ...) para referencia cruzada
- Conclusoes cientificas (C1, C2, ...) separadas de observacoes
- Hipoteses (H01-H10) mapeadas para secoes especificas
