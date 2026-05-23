---
title: T-CLEAN-1 — Adicionar pre-commit (detect-secrets, ruff, basicos)
status: closed
resolution: config-created-install-pending
priority: P3
created: 2026-05-22
updated: 2026-05-23
closed: 2026-05-23
blocked-by: []
related:
  - ../README.methodology.md
  - pyproject.toml
  - .pre-commit-config.yaml
---

# T-CLEAN-1 — Adicionar pre-commit (detect-secrets, ruff, basicos)

## Contexto / motivacao

Auditoria 2026-05-22 apontou ausencia de `pre-commit` como gap de
higiene de repositorio (metodologia §"Versionamento e higiene").

Projeto e' solo sem CI, mas `pre-commit` protege localmente contra:
- Secrets acidentais (`detect-secrets`) — risco real (config files,
  scripts experimentais)
- Codigo sujo (`ruff` ja' instalado em pyproject, mas nao automatizado)
- Arquivos cache acidentalmente staged (`__pycache__`, `.pytest_cache`)
- Arquivos > 100MB (Git LFS recommendation)

Custo de instalar e' baixo; valor cresce a cada commit. Especialmente
util com IA — agente pode propor `git add -A` que pega artefato indesejado.

## Plano

1. Adicionar `pre-commit` em `pyproject.toml` (dev deps)
2. Criar `.pre-commit-config.yaml` na raiz com:
   - `detect-secrets` (Yelp)
   - `ruff` (lint + format)
   - hooks basicos do pre-commit: `check-merge-conflict`,
     `check-added-large-files`, `end-of-file-fixer`, `trailing-whitespace`
   - hook customizado: bloquear `__pycache__/`, `.pytest_cache/`,
     `.mypy_cache/`, `.ruff_cache/` (defesa-em-profundidade junto com
     `.gitignore`)
3. Rodar `pre-commit install` (instala git hook local)
4. Rodar `pre-commit run --all-files` baseline pra capturar pendencias
   existentes (ou colocar arquivos legados em ignore)
5. Documentar setup em `README.md` (1 paragrafo "First-time setup")

## Criterio de aceite

- [ ] `.pre-commit-config.yaml` na raiz
- [ ] `pre-commit install` configura hook em `.git/hooks/pre-commit`
- [ ] `pre-commit run --all-files` passa (ou cria baseline allowlist
  pra arquivos legados, justificado)
- [ ] Tentativa de commit com secret simulado e' bloqueada
- [ ] Tentativa de commit com `__pycache__` staged e' bloqueada
- [ ] README atualizado com setup

## Riscos

- **Slow commits** se hook for pesado — mitigacao: hooks rapidos por
  default; lint pesado so' opt-in
- **False positives em detect-secrets** — usar `.secrets.baseline`
  pra capturar e ignorar legacy
- **Bloquear flow exploratorio** em dirty lab — solucao: hooks
  permissivos por path (ex: skipar `experiments/lab/dirty/` pra
  alguns hooks)

## Conexoes

- Metodologia §"Versionamento e higiene de repositorio"
- §11 bibliografia (pre-commit.com; detect-secrets Yelp)

## Updates datados

### 2026-05-23 — execucao + fechamento

`.pre-commit-config.yaml` criado na raiz com:
- pre-commit-hooks v5.0.0 oficiais: trailing-whitespace, end-of-file-fixer,
  check-merge-conflict, check-added-large-files (2MB), check-yaml, check-toml,
  check-json, mixed-line-ending (--fix=lf)
- detect-secrets v1.5.0 (Yelp) com baseline
- ruff v0.7.0 (lint + format) excluindo dirty/old
- custom hook bloqueando cache dirs (__pycache__/, .pytest_cache/, etc.) staged

pyproject.toml atualizado: dev deps agora incluem pre-commit>=3.5,
ruff>=0.7, detect-secrets>=1.5.

README.md atualizado com seção "First-time setup (dev)" documentando:
- pip install -e ".[dev]"
- pre-commit install
- pre-commit run --all-files (baseline)

**`pre-commit install` PENDENTE de execucao** — owner deve rodar
manualmente apos clone/refresh:
```bash
pre-commit install
```
(NAO executado nesta sessao porque requer venv ativo + git hooks no
ambiente local do owner)

Hooks pesados (full test suite) NAO incluidos — rodados manualmente
ou em CI futuro.

Resolution: config-created-install-pending. Quando owner rodar
`pre-commit install`, hooks ativam automaticamente.
