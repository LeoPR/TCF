# TCF — Meta-Artigo (Capitulos)

Artigo cientifico completo sobre o **Textual Columnar Format (TCF)**,
organizado por capitulos para facilitar leitura, revisao e derivacao
em formatos academicos (IEEE, ACM, arXiv).

**Versao atual:** v0.2 (encoder com 4 niveis de compressao, dataset retail_sales).
Experimentos anteriores (v0.1) estao em [archive_v01/](archive_v01/) apenas
como registro historico — nao sao usados no paper.

---

## Indice de Inovacoes

| Arquivo | Descricao |
|---------|-----------|
| [00-innovations.md](00-innovations.md) | Inovacoes comprovadas (I1-I7) + pendentes (I8-I13) |

Atualizado conforme resultados sao confirmados. Apenas inovacoes comprovadas
por experimentos sao registradas como definitivas.

---

## Capitulos

| Cap | Arquivo | Titulo | Status |
|-----|---------|--------|--------|
| 1 | [01-introduction.md](01-introduction.md) | Introducao | **v0.2 alinhado** |
| 2 | [02-related-work.md](02-related-work.md) | Trabalhos Relacionados | **Completo** |
| 3 | [03-tcf-format.md](03-tcf-format.md) | TCF: Textual Columnar Format | **v0.2 alinhado** |
| 4 | [04-methodology.md](04-methodology.md) | Metodologia | **v0.2 alinhado** |
| 5 | [05-results-e1-e2.md](05-results-e1-e2.md) | Encode/Decode + Compressao | **Completo** |
| 7 | [07-results.md](07-results.md) | Resultados LLM (Etapas 1+2, diagnostic, stats, scale, transport) | **Completo v0.2** |
| 8 | [08-discussion.md](08-discussion.md) | Discussao | Placeholder |
| 9 | [09-conclusion.md](09-conclusion.md) | Conclusao | Placeholder |

### Apendices

| ID | Arquivo | Titulo | Status |
|----|---------|--------|--------|
| A | [appendices/A-tcf-spec.md](appendices/A-tcf-spec.md) | Especificacao TCF v0.2 | Placeholder |
| B | [appendices/B-prompts.md](appendices/B-prompts.md) | Prompts utilizados | Placeholder |
| C | [appendices/C-full-tables.md](appendices/C-full-tables.md) | Tabelas completas de resultados | Placeholder |
| D | [appendices/D-format-comparison.md](appendices/D-format-comparison.md) | Comparacao lado-a-lado de formatos | Completo |

### Removido

| Cap | Destino | Motivo |
|-----|---------|--------|
| ~~6~~ | [archive_v01/06-results-e3-v01.md](archive_v01/) | Phase 1 v0.1 (dataset 41 vendas) |
| ~~7 antigo~~ | [archive_v01/07-mixed-v01-v02.md](archive_v01/) | Misturava Phase 2 v0.1 com Etapa 1/2 v0.2 |

---

## Findings por experimento (v0.2)

| # | Finding | Experimento | Prioridade |
|---|---------|-------------|-----------|
| F30-F34 | TCF escala, CSV colapsa | Etapa 1 | HIGH |
| F50-F55 | 12 modelos ranking, gemma3 melhor | Etapa 2 | HIGH |
| F60-F63 | Thinking ON + t=0 = 100% L0 | G30 Hyperparams | MEDIUM |
| F70-F73 | TCF+gzip 29% < CSV+gzip | Transport Compression | MEDIUM |
| **F80-F84** | **STATS como shortcut cognitivo** | **3-Layer Diagnostic** | **CRITICAL** |
| F85-F89 | Sweet spot 100-200 rows | Scale Progression | HIGH |
| **F90-F94** | **STATS inflam TODOS os modelos** | **Stats Ablation** | **CRITICAL** |

F80-F84 e F90-F94 sao os findings centrais do paper — juntos mostram
que TCF e uma **estrategia composta** (formato + hints), nao apenas
um formato.

---

## Convencoes

- Findings numerados (F##) para referencia cruzada entre capitulos
- Inovacoes numeradas (I##) para claims do paper
- Conclusoes cientificas separadas de observacoes
- Tickets (../tickets/) sao a fonte primaria — capitulos referenciam
- Numeros vivem em UM arquivo fonte, outros referenciam

## Como usar este meta-artigo

1. Ler capitulos na ordem (1-9) para a historia completa
2. Cada capitulo e auto-contido com suas referencias internas
3. Para submissao: selecionar e condensar capitulos conforme venue
4. Apendices contem dados de suporte (incluir ou omitir)

## Status geral

```
Cap 1 (Intro)        — v0.2 alinhado com novas contribuicoes e RQs
Cap 2 (Related)      — completo, refs atualizadas (2023-2026)
Cap 3 (TCF Format)   — v0.2 alinhado (4 niveis, STATS)
Cap 4 (Methodology)  — v0.2 alinhado (retail_sales, 12 modelos)
Cap 5 (Encode/Comp)  — completo, 12 cenarios x 4 levels
Cap 6 (removido)     — archived (era Phase 1 v0.1)
Cap 7 (Results LLM)  — COMPLETO v0.2 (7 experimentos, 7 grupos de findings)
Cap 8 (Discussion)   — pendente
Cap 9 (Conclusion)   — pendente
```
