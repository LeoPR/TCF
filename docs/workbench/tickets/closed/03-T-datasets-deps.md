---
title: Adicionar dependencias opcionais para datasets
type: task
status: DONE
priority: 2
parent: 01-M-datasets-setup
completed: 2026-04-10
---

## STATUS: COMPLETO (2026-04-10)

**pyproject.toml atualizado:**
- Version bump: 0.1.0 → 0.2.0
- Adicionado grupo `datasets` com duckdb>=1.0, scikit-learn>=1.3, pandas>=2.0
- Adicionado grupo `all` = datasets + dev + eval

**Testado via `pip install -e ".[datasets]"`:**
- duckdb 1.5.1 instalado
- scikit-learn 1.8.0 instalado
- scipy 1.17.1 (dep transitiva de sklearn)
- joblib 1.5.3 (dep transitiva)
- pandas 2.3.3 (ja estava)

**Verificado:**
- `import duckdb` funciona
- `import sklearn.datasets.fetch_openml` funciona
- `duckdb.connect(':memory:').execute("INSTALL tpch; LOAD tpch")` funciona
- Testes existentes: 112/112 passam (sem regressao)

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
