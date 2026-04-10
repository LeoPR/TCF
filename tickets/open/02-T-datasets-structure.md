---
title: Criar estrutura de pastas para datasets
type: task
status: OPEN
priority: 1
parent: 01-M-datasets-setup
---

# Estrutura de pastas

## Objetivo

Criar a arvore de diretorios onde os datasets canonicos ficarao.

## Estrutura

```
datasets/
├── README.md                    # Indice geral + origens
├── canonical/                   # Datasets consagrados (read-only apos download)
│   ├── tpch-sf001/
│   └── adult-census/
├── sqlite/                      # Mesmas bases em SQLite com tipos
│   ├── tpch-sf001.db
│   └── adult-census.db
├── derivations/                 # Formatos derivados do SQLite
│   ├── tpch-sf001/
│   │   ├── csv/
│   │   ├── jsonl/
│   │   └── markdown/
│   └── adult-census/
│       ├── csv/
│       ├── jsonl/
│       └── markdown/
├── questions/                   # Bancos de perguntas por dataset
│   ├── tpch-sf001.json
│   └── adult-census.json
├── quality-reports/             # Reports de qualidade por dataset
│   ├── tpch-sf001.md
│   └── adult-census.md
└── poor-reference/              # Datasets pobres (para comparacao com literatura)
    └── retail-sales-synthetic/  # Nosso antigo (Ana, Bruno, Caneta)
```

## Tarefas

- [ ] Criar pastas vazias
- [ ] Criar `datasets/README.md` com explicacao da estrutura
- [ ] Adicionar `datasets/canonical/.gitkeep` etc para pastas vazias
- [ ] Atualizar `.gitignore`:
  - `datasets/canonical/**/*.csv` (serao gerados por download)
  - `datasets/sqlite/*.db`
  - `datasets/derivations/**/*`
  - Mas **nao** ignorar `metadata.json`, `README.md`, `quality-report.md`
- [ ] Commit inicial so com estrutura + README

## Criterio de conclusao

- Estrutura existe no git
- `datasets/README.md` explica o proposito e licencas
- `.gitignore` nao persiste dados brutos (CSV, DB)
