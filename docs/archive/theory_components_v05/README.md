---
title: Componentes do projeto TCF
date: 2026-04-23
type: overview
---

# Os 3 componentes do projeto, com TCF ao centro

O projeto é organizado em 3 componentes distintos. **TCF Core** é o formato
puro (compressão textual columnar). Os outros dois são aplicações que usam
TCF como meio, mas têm objetivos próprios.

```
                    ┌─────────────────────┐
                    │   TCF Core          │
                    │   formato +         │
                    │   compressão        │
                    └──────────┬──────────┘
                               │
                   ┌───────────┴───────────┐
                   │                       │
         ┌─────────▼──────────┐  ┌─────────▼──────────┐
         │ TCF-LLM Interface  │  │ TCF-DB Extractor   │
         │ schema/dados/query │  │ DB real → TCF min  │
         │   via LLM          │  │  + pergunta BI     │
         └────────────────────┘  └────────────────────┘
            (pesquisa ativa)         (roadmap)
```

## Tabela de concerns

| Componente | Responsabilidade | Estado | Doc |
|-----------|------------------|--------|-----|
| **1. TCF Core** | Formato textual columnar + compressão L0-L3 + codec reversível | Estável v0.2; roadmap: blocos/streaming | [1-tcf-core.md](1-tcf-core.md) |
| **2. TCF-LLM Interface** | Como usar TCF como veículo para perguntar coisas ao LLM (schema, dados, queries) | Ativo — M-series; hospeda Linhas A/B | [2-tcf-llm-interface.md](2-tcf-llm-interface.md) |
| **3. TCF-DB Extractor** | Ler um DB real, extrair schema mínimo em TCF, combinar com pergunta BI, executar query no próprio DB | Roadmap — pré-design | [3-tcf-db-extractor.md](3-tcf-db-extractor.md) |

## Onde a pesquisa científica vive

As **linhas de pesquisa** (A: LLM como analista direto; B: schema carrier + SQL)
são sub-estrutura do componente #2 (TCF-LLM Interface). Ver
[../research-lines/README.md](../research-lines/README.md).

Os achados canônicos (F-Q1..F-Q23+) em
[../methodology/F-findings.md](../methodology/F-findings.md) são tagueados
por linha `{A}`, `{B}` ou `{shared}` — organizações ortogonais, ambas válidas.

## Leitura por interesse

- **Quero entender o formato TCF:** [1-tcf-core.md](1-tcf-core.md)
- **Quero usar TCF com LLM:** [2-tcf-llm-interface.md](2-tcf-llm-interface.md)
- **Quero aplicar em DB real:** [3-tcf-db-extractor.md](3-tcf-db-extractor.md)
- **Quero ver os achados:** [../FINDINGS_SUMMARY.md](../FINDINGS_SUMMARY.md)
