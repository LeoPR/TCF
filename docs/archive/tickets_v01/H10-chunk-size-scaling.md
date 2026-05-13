# H10 — Escalabilidade: Accuracy × Tamanho do Chunk

**Status:** ABERTO  
**Deps:** P06  
**LLM calls:** ~1.200

## Hipótese

A accuracy decresce com o número de linhas por chunk, e essa degradação é mais lenta para TCF do que para formatos orientados a linha (CSV, JSONL).

**H10_0 (nula):** A taxa de degradação com chunk size é igual entre formatos.

## Motivação

Resultados baseline já mostram:
- Chunk de 1 linha → ~100% accuracy em todos os formatos
- Chunk de 40 linhas → 25–50% accuracy

**Predição TCF:** A linha `vl: 2.5 11.0 1.0 ...` é uma única linha independente do número de rows. O modelo faz uma única varredura linear. Em formatos orientados a linha, cada row adicional aumenta a distância de atenção entre o início dos dados e a pergunta.

## Design

```
4 chunk sizes (1, 10, 20, 41 linhas)
× 6 formatos
× 2 perguntas (Q1: sum_vl, Q5: count_rows)
× 5 modelos (1 por categoria de tamanho)
× 5 runs
= 1.200 calls
```

## Curvas Esperadas

```
accuracy
  1.0 │ ●── TCF ──────────────────●
      │       \
  0.5 │        ● CSV ──────────● 
      │                  \
  0.0 │         JSONL ─────────────●
      └──────────────────────────────→ rows por chunk
      1       10      20      41
```

**Por que TCF deve degradar menos:** Para `sum_vl`, o modelo olha apenas a linha `vl:` — ela não cresce de forma diferente de outros formatos em extensão (é sempre 1 linha), mas o conteúdo (tokens) cresce igual. O ganho real é estrutural: o modelo não precisa *parsear* cada objeto/linha para extrair a coluna — ela já está separada.

## Análise Estatística

Ajustar curva logística de degradação por formato:  
`accuracy(n) = 1 / (1 + exp(k*(n - n50)))`

Comparar parâmetros `k` (taxa) e `n50` (ponto de 50% accuracy) entre formatos.
