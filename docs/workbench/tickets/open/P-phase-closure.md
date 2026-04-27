---
title: Fechamento de fases — o que fechar, o que pip-publicar
type: meta
status: OPEN
priority: CRITICAL
created: 2026-04-15
origin: Revisao geral do projeto (ciclo 2026-04-15)
---

# Plano de Fechamento de Fases e Publicacao pip

## Estado atual do projeto

### Fases ja concluidas (fechar tickets abertos relacionados)

| Fase | O que inclui | Status real | Acao |
|------|-------------|-------------|------|
| **Fase 1: Datasets** | Setup datasets, SQLite, readers, writers | DONE | Fechar metas abertas |
| **Fase 2: Encoder v0.2** | CLI, API, L0-L3, roundtrip | DONE | Fechar |
| **Fase 3A: Benchmarks basicos** | Transport compression, scale progression | DONE | Fechar |
| **Fase 3B: Experimentos LLM** | G02/G21 (600 combos), diagnostic, stats ablation | DONE | Fechar |
| **Fase 3C: Canonical data** | adult-census, progressive diagnostic, stats ablation canonical | DONE | Fechar |

### Fases em aberto (work in progress)

| Fase | O que falta | Prioridade |
|------|------------|-----------|
| **Fase 4: Tokenizacao real** | tiktoken em todos experimentos, comparacao com TOON | ALTA |
| **Fase 5: Compressao avancada** | Delta, scale-to-int, bucket, knee algorithm | ALTA |
| **Fase 6: Comparacao TOON** | Encoder TOON real + benchmark no mesmo setup | CRITICA |
| **Fase 7: Paper** | Figuras, analise estatistica, escrita | ALTA |

## Tickets a fechar agora

### Concluidos mas ainda marcados como OPEN/IN_PROGRESS:

| Ticket | Por que fechar | Evidencia |
|--------|--------------|---------|
| `tickets/open/E-stats-ablation.md` | Dois experimentos completos | 128 combos (retail) + 135 (canonical) |
| `tickets/open/30-E-progressive-diagnostic.md` | Benchmark completo 60 combos | Todos os modelos passam |
| `tickets/open/H-diagnostic-3layer-v02.md` | Progressive diagnostic cobre o essencial | Partial — atualizar status |
| `tickets/frozen/E-scale-progression.md` | DONE desde 2026-04-09 | Gemma3:12b 6 escalas |
| `tickets/frozen/H-G30-hiperparametros.md` | DONE desde 2026-04-09 | Temperature/thinking |

### Frozen que podem ser descongelados agora:

| Ticket | Por que descongelar | Prioridade |
|--------|-------------------|-----------|
| `tickets/frozen/M-tokenizer-validation.md` | Tiktoken ja instalado, resultados empiricos prontos | ALTA |
| `tickets/frozen/P-competing-formats.md` | Comparacao TOON e critica | CRITICA |
| `tickets/frozen/H-token-friendly-format.md` | Resultados mostram que notacao atual e otima | Fechar como "N/A" |
| `tickets/frozen/T-figures-analysis.md` | Bloqueante para paper | ALTA |

## Publicacao pip — `pip install tcf`

### O que ja existe

O `pyproject.toml` ja esta configurado:
```toml
[project]
name = "tcf"
version = "0.2.0"
description = "Textual Columnar Format — compact relational data encoding for LLMs"
dependencies = []  # zero dependencias!
requires-python = ">=3.10"
license = { text = "MIT" }
```

API publica atual (estavel):
```python
from tcf import encode_columns, encode_rows, decode, EncodeConfig
```

CLI:
```bash
tcf encode --meta data/metadata.json --data-dir data/ --level 2
tcf decode output.tcf --out-dir restored/
tcf info output.tcf
```

### O que falta para publicar

1. **README.md atualizado** — quickstart, exemplos, API reference
2. **Testes passando** — rodar `pytest tests/` completo
3. **Build funcional** — `hatch build` ou `pip install -e .`
4. **TestPyPI** — testar antes de PyPI real
5. **Tag v0.2.0** — git tag + GitHub release

### Decisao: publicar v0.2.0 agora ou esperar v0.3.0?

**Argumento para publicar v0.2.0 agora:**
- API e estavel, zero dependencias, roundtrip 100%
- pip install defensavel para o paper
- Pode citar "available at pip install tcf" no artigo
- Atrai feedback externo que melhora o projeto

**Argumento para esperar v0.3.0:**
- v0.3.0 tera features importantes (delta, knee, STATS CI)
- Melhor fazer um unico release com a historia completa
- Menos churn de versoes

**Recomendacao:** publicar v0.2.0 no TestPyPI agora, PyPI real quando
o paper for submetido (ou quando v0.3.0 estiver pronto).

### Passos concretos para publicar

```bash
# 1. Verificar build
cd TCF && pip install build
python -m build

# 2. Verificar que instala limpo
pip install dist/tcf-0.2.0-py3-none-any.whl
python -c "from tcf import encode_columns; print('ok')"

# 3. TestPyPI
pip install twine
twine upload --repository testpypi dist/*

# 4. Testar instalacao do TestPyPI
pip install --index-url https://test.pypi.org/simple/ tcf

# 5. PyPI real (quando pronto)
twine upload dist/*
```

## Cronograma sugerido

### Ciclo atual (2026-04-15):
- [x] Tokenizacao empirica (tiktoken) — DONE hoje
- [x] Nota de pesquisa sobre compressao avancada — DONE hoje
- [ ] Fechar tickets concluidos
- [ ] Descongelar M-tokenizer-validation com resultados
- [ ] Rodar `pytest tests/` e corrigir qualquer falha
- [ ] `hatch build` e testar instalacao local

### Proximo ciclo:
- [ ] Implementar STATS CI (full_n + err) — V0.2.1
- [ ] Implementar encoder TOON real para comparacao
- [ ] Re-tokenizar experimentos passados com tiktoken
- [ ] Publicar no TestPyPI

### Dois ciclos:
- [ ] Delta encoding + scale-to-int + knee algorithm — V0.3.0
- [ ] Figuras do paper (T-figures-analysis)
- [ ] PyPI real

## Definicao de "TCF defensavel"

O TCF atual (v0.2.0) ja e defensavel para o paper se:

1. API publica estavel: `encode_columns`, `decode`, `EncodeConfig` — YES
2. Roundtrip 100%: todos os testes passam — YES (precisa verificar)
3. Benchmark de compressao: resultados comprovados — YES
4. Benchmark LLM: resultados comprovados — YES
5. Comparacao com TOON: em tokens reais — PARCIAL (estimado)
6. pip install: funcional — FALTA PUBLICAR

**Conclusao:** v0.2.0 ja e publicavel. Publicar no TestPyPI este ciclo.
