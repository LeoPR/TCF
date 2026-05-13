# H06 — Representação de FK e Accuracy em Filtros

**Status:** ABERTO  
**Deps:** P04, P05  
**LLM calls:** ~600

## Hipótese

Accuracy em queries com FK (Q6, Q7, Q10) cresce com a explicitude do encoding:  
`inline_resolved > hint_comment > dict_separate > id_raw`

**H6_0 (nula):** As 4 representações produzem accuracy igual em queries FK-dependentes.

## As 4 Variantes

| Variante | Exemplo | Tokens | FK visível? |
|----------|---------|--------|-------------|
| `id_raw` | `id_pessoa: 1 2 1 3 ...` | mínimo | não |
| `dict_separate` | `## DICT pessoas` + `0=Ana 1=Bruno` + `id_pessoa: 0 1 0 2 ...` | médio | sim (lookup) |
| `hint_comment` | `id_pessoa: 1 2 1 3 ...` + `> pessoa ref pessoas.nome → 1=Ana 2=Bruno` | médio | sim (inline) |
| `inline_resolved` | `pessoa: Ana Bruno Ana Carla ...` (JOIN no encoder) | máximo | sim (direto) |

## Design

```
4 variantes × 3 perguntas (Q6, Q7, Q10) × 10 modelos × 5 runs = 600 calls
```

## Trade-off Esperado

```
Accuracy:  inline_resolved > hint_comment ≥ dict_separate > id_raw
Tokens:    inline_resolved >> hint_comment ≥ dict_separate > id_raw
```

**Recomendação prática:** Ponto de cruzamento onde `dict_separate` ou `hint_comment` atingem accuracy de `inline_resolved` a custo menor → estratégia ótima por tamanho de modelo.

## Observação para bins_16 com FK

Se a coluna `id_produto` for binada (bins_16), o LLM recebe índices sem semântica. Isso é um caso especial a reportar separadamente — "destructive grouping" para FKs.
