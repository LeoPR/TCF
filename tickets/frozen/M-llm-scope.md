---
title: Onde LLM ajuda de fato com TCF? Mapa de capacidades
type: methodology
status: OPEN
priority: CRITICAL
created: 2026-04-10
origin: Consolidar "quando TCF+LLM vale a pena" em um mapa operacional
---

# Onde LLM Ajuda de Fato — Mapa de Capacidades

## Problema

Nossos experimentos mostraram:
- **F80:** LLMs nao somam 509 numeros
- **F81:** gemma3 usa STATS como shortcut
- **F90:** TODOS os modelos dependem de STATS para agregacoes
- **F83:** LLMs leem L2 (RLE) melhor que esperado
- **F85:** Sweet spot em 100-200 rows
- **F89:** Colapso a partir de 1000 rows

Isso pinta um quadro confuso. Usuario pergunta: **"Quando posso usar TCF+LLM
e esperar que funcione?"** — nao temos resposta clara.

## Objetivo

Produzir um **mapa de 2 dimensoes** que responda: dado um cenario
(tipo de pergunta × tamanho de dados × modelo disponivel), qual a
probabilidade de sucesso?

```
              │ q1_sum  │ q3_max │ q6_top  │ q_qualit │ q_codegen │
──────────────┼─────────┼────────┼─────────┼──────────┼───────────┤
<100 rows     │   100%  │  100%  │   95%   │    90%   │    ?      │
100-500 rows  │   90%*  │   80%  │   70%   │    80%   │    ?      │
500-1000 rows │   50%*  │   30%  │   20%   │    60%   │    ?      │
>1000 rows    │   30%*  │    5%  │    0%   │    40%   │    ?      │

* com STATS
```

## Dimensoes a caracterizar

### Eixo 1: Tipo de pergunta (granularidade)
1. **Exact lookup** (max, min, first, last) — quase sempre funciona
2. **Exact aggregate** (sum, avg, count) — **depende de STATS**
3. **Filter + aggregate** (sum of X where Y) — mais dificil
4. **Argmax/argmin** (top product, top spender) — medio
5. **Distinct count** — dificil mesmo pequeno
6. **Multi-step** (filter → group → argmax) — muito dificil
7. **Qualitative** (tendencia, intuicao) — **supostamente facil** (E-qualitative)
8. **Code generation** (gerar script) — **pode ser 100%** (E-codegen)

### Eixo 2: Tamanho dos dados
1. **Micro (<50 rows):** tudo cabe, LLMs acertam muito
2. **Pequeno (50-200):** sweet spot do TCF
3. **Medio (200-500):** comeca a degradar
4. **Grande (500-1000):** maior parte falha
5. **Muito grande (>1000):** colapso quase total

### Eixo 3: Modelo disponivel
1. **Minusculo (<2B):** muito limitado, so micro + lookups
2. **Pequeno (2-4B):** micro + pequeno + lookups simples
3. **Medio (7-9B):** pequeno + medio com STATS
4. **Grande (12-14B):** sweet spot — melhor relacao custo/resultado
5. **Muito grande (20B+):** marginal vs grande, nao justifica

### Eixo 4: Hints disponiveis
1. **TCF puro:** sem STATS
2. **TCF + STATS:** hints meta-cognitivos (nossa abordagem)
3. **TCF + code gen:** LLM escreve codigo que executa (E-codegen)

## O que gera este mapa

**Experimentos que contribuem:**
- Etapa 2 (12 modelos × 3 formatos × 8 questoes) — tipo de pergunta
- Scale progression — tamanho de dados
- Stats ablation — impacto dos STATS
- E-qualitative-reasoning — nova dimensao
- E-code-generation — nova dimensao
- E-speed-tradeoffs — modelo × quantizacao

Este ticket NAO roda experimentos novos — e um **consolidador** que
agrega todos os resultados em um mapa acionavel.

## Formato final (entregavel)

### Arquivo: `docs/article/appendices/E-capability-map.md`

Tabela 4D (pergunta × tamanho × modelo × hints) com cores:
- Verde: >80% accuracy esperada
- Amarelo: 50-80%
- Vermelho: <50%

### Decisao tree simplificada

```
Qual seu caso de uso?
├── Dados < 200 linhas
│   ├── Pergunta exata (sum, max, etc) → TCF L0 + STATS, qualquer modelo 7B+
│   ├── Pergunta aproximada → qualquer TCF, modelo 4B+
│   └── Codigo gerado → qualquer TCF, modelo 12B+
├── Dados 200-500 linhas
│   ├── Agregacoes (sum, avg) → PRECISA STATS, modelo 12B+
│   ├── Lookups (max, min) → funciona 70-80% sem STATS
│   └── Qualitative → modelo 4B+ (supostamente)
├── Dados 500-1000 linhas
│   ├── Agregacoes → STATS + modelo 12B+, 50% sucesso
│   ├── Outras → NAO use LLM direto, use codegen (E-codegen)
│   └── Ou: use analise programatica (python direto)
└── Dados > 1000 linhas
    └── NAO use LLM para Q&A direto. Use:
        ├── Codegen (LLM gera script)
        ├── Chunking (quebrar dados)
        └── Ou analise programatica
```

## Quando TCF NAO vale a pena

Ser honesto sobre limites. Casos onde TCF + LLM **nao** e melhor que alternativas:

| Caso | Alternativa melhor | Por que |
|------|-------------------|---------|
| Dados >1000 linhas | pandas + LLM codegen | LLM direto nao funciona |
| Queries SQL complexas | SQL + LLM para gerar query | LLM nao e db |
| Dados binarios | JSON + base64 | TCF nao suporta (P-data-types) |
| Latencia critica (<100ms) | Cache + metricas pre-computadas | LLM e lento |
| Precisao absoluta (financial) | Calculo programatico | LLM erra |

Este reconhecimento **fortalece** o paper — mostra onde TCF realmente agrega.

## Tarefas

- [ ] Aguardar conclusao de E-qualitative, E-codegen, E-speed-tradeoffs
- [ ] Agregar resultados em tabela 4D
- [ ] Gerar arvore de decisao
- [ ] Escrever documento honest "quando usar" e "quando nao usar"
- [ ] Incluir como apendice E do paper
