---
title: Adicionar dependencias opcionais para datasets
type: task
status: OPEN
priority: 2
parent: 01-M-datasets-setup
---

# Dependencias opcionais

## Objetivo

Adicionar deps necessarias para manipular os datasets canonicos, sem
poluir o core do TCF (que continua zero-deps).

## Dependencias

No `pyproject.toml`, adicionar group opcional `datasets`:

```toml
[project.optional-dependencies]
datasets = [
    "duckdb>=1.0",        # TPC-H generation
    "scikit-learn>=1.3",  # fetch_openml (Adult, outros futuros)
    "pandas>=2.0",        # manipulacao
]
```

## Instalacao

Usuario pode escolher:

```bash
pip install -e .              # core (zero deps externas)
pip install -e .[datasets]    # com ferramentas de dataset
```

## Por que opcional

- Core do TCF (encoder/decoder) nao precisa de nenhuma dessas
- Datasets e uma feature de PESQUISA, nao de runtime
- Usuarios que so querem encode/decode nao precisam baixar 500MB de deps

## Tarefas

- [ ] Verificar pyproject.toml atual
- [ ] Adicionar secao `[project.optional-dependencies]` se nao tiver
- [ ] Adicionar group `datasets` com as 3 deps
- [ ] Adicionar group `all` que inclui tudo (conveniencia)
- [ ] Testar `pip install -e .[datasets]` em venv limpo
- [ ] Documentar em `datasets/README.md` como instalar

## Verificacao

- `pip install -e .[datasets]` funciona
- `python -c "import duckdb; import sklearn; import pandas"` funciona
- Testes do core continuam passando sem as deps opcionais
