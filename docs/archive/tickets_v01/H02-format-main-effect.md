# H02 — Efeito Principal do Formato na Accuracy

**Status:** ABERTO  
**Tipo:** Experimento Principal  
**Deps:** P01, P02, P04, P05, P06  
**LLM calls:** ~3.000

## Hipótese

A accuracy em perguntas de agregação (Layer 2) difere significativamente entre os 6 formatos.

**H2_0 (nula):** `μ_csv = μ_jsonl = μ_toon = μ_tcf_raw = μ_tcf_sorted = μ_tcf_sorted_dict`

**Contraste principal:** `tcf_sorted_dict` vs `jsonl_expanded` — a afirmação central do paper.

## Variáveis

| Tipo | Variável | Níveis |
|------|----------|--------|
| IV | Formato | 6: csv_expanded, jsonl_expanded, toon, tcf_raw, tcf_sorted, tcf_sorted_dict |
| IV | Modelo | 10 (ver lista em H07) |
| IV | Pergunta | 10 (Q1–Q10, ver P05) |
| DV | Accuracy | binário por call, proporção por condição |
| DV | Token count | prompt_eval_count da API Ollama |

## Design

```
6 formatos × 10 modelos × 10 perguntas × 5 runs = 3.000 calls
```

**Estatística:** ANOVA de medidas repetidas (formato within-subject por modelo).  
Alternativa não-paramétrica: Friedman.  
Correção múltiplas comparações: Bonferroni dentro desta hipótese.

## Controles

- Temperature = 0.0
- System prompt fixo por formato (não tunar durante experimento)
- Dataset fixo (vendas completo, 41 linhas, sem chunking)

## Output esperado

Tabela de accuracy × formato × modelo → figura principal do paper.

```
formato           | Q1(sum) | Q2(avg) | Q5(count) | Q8(top_fk) | média
csv_expanded      |   ?     |   ?     |    ?      |     ?      |  ?
jsonl_expanded    |   ?     |   ?     |    ?      |     ?      |  ?
toon              |   ?     |   ?     |    ?      |     ?      |  ?
tcf_raw           |   ?     |   ?     |    ?      |     ?      |  ?
tcf_sorted        |   ?     |   ?     |    ?      |     ?      |  ?
tcf_sorted_dict   |   ?     |   ?     |    ?      |     ?      |  ?
```
