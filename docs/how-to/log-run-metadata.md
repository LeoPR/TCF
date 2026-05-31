---
title: How to — Logar metadata de run em manifest.jsonl
type: how-to
status: active
tags: [reprodutibilidade, manifest, git-sha, experiment]
created: 2026-05-21
updated: 2026-05-21
---

# Logar metadata de run em manifest.jsonl

Receita pra experimentos novos (`EXP-NNN-tema/run.py`) gravarem
metadata suficiente pra reprodutibilidade — especialmente `git_sha`
do codigo que rodou.

Motivacao: sem `git_sha`, runs identicos com timestamps diferentes em
`manifest.jsonl` sao ambiguos — mesmo codigo? mudou e ratio ficou
identico por sorte? Helper criado em
[`scripts/run_metadata.py`](../../scripts/run_metadata.py) resolve.

## Quando aplicar

- **Sempre** em `EXP-NNN-tema/run.py` novo (clean lab)
- **Opcional** retroativar manifests antigos (geralmente nao vale —
  altera historia; documente que git_sha pre-2026-05-20 e' ausente)

## Uso minimo

```python
import json
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[3]  # ajuste conforme profundidade do EXP
sys.path.insert(0, str(ROOT))

from scripts.run_metadata import get_run_metadata

# ... computa resultados ...

entry = {
    **get_run_metadata(),                # timestamp + git_sha + git_dirty + python + platform
    "experiment_id": "EXP-NNN-tema",
    "metrics": {"total_bytes": 1615, "ratio": 0.5418, ...},
    "outcome": "confirmed",              # FORTE: declare resultado da hipotese
}

manifest_path = THIS / "manifest.jsonl"
with manifest_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")
```

## Campos esperados em cada linha

Vindos do helper (automatico):

| Campo | Tipo | Origem | Critico? |
|---|---|---|---|
| `timestamp` | ISO 8601 UTC | `datetime.now(timezone.utc)` | FORTE |
| `git_sha` | string 40 chars ou `null` | `git rev-parse HEAD` | **FORTE** (sem isso, ambiguidade) |
| `git_dirty` | bool ou `null` | `git status --porcelain` | FORTE (se true, codigo nao versionado) |
| `python` | string | `sys.version.split()[0]` | medio |
| `platform` | string | `platform.system()` + release | medio |

Adicione voce no `entry`:

| Campo | Tipo | Sugestao |
|---|---|---|
| `experiment_id` | string | `"EXP-NNN-tema"` |
| `metrics` | dict | metricas factuais do run |
| `outcome` | `"confirmed" \| "refuted" \| "partial" \| "inconclusive"` | FORTE — combate publication bias (so' positivos registrados) |
| `config_hash` | string | hash do config.json se este variar entre runs |
| `data_sha` | dict | SHA-256 dos datasets de entrada (quando dataset evolui) |

## Outcome — disciplina

Declare explicitamente o resultado da hipotese do experimento:

- `confirmed` — hipotese sustentada pelo run
- `refuted` — hipotese rejeitada (resultado contradiz expectativa)
- `partial` — sustentada em algumas condicoes, falha em outras
- `inconclusive` — dado insuficiente; revisitar

**Por que importa**: o registry de hipoteses
([`experiments/lab/dirty/notas/roadmap-hipoteses.md`](../../experiments/lab/dirty/notas/roadmap-hipoteses.md))
e o campo `outcome` sao a salvaguarda contra **storytelling
post-hoc** (so' positivos registrados). Ver discussao em
[`../algorithms/`](../algorithms/) e
[`../adr/`](../adr/).

## Git dirty == true — o que significa

Se `git_dirty: true`, o run foi com codigo nao-commitado.
Reprodutibilidade fica comprometida — outra pessoa nao consegue
recriar exatamente o `git_sha + diff`.

**Pratica**: antes de rodar EXP clean importante, commitar mudancas.
`git_dirty: true` em manifest e' sinal de "este run e' exploratorio,
nao referencia".

## Conexoes

- Helper: [`scripts/run_metadata.py`](../../scripts/run_metadata.py)
- Metodologia subjacente: [`../../../README.methodology.md`](../../../README.methodology.md) §"Aprofundando Pilar 4 → Manifest.jsonl"
- Roadmap hipoteses: [`../../experiments/lab/dirty/notas/roadmap-hipoteses.md`](../../experiments/lab/dirty/notas/roadmap-hipoteses.md)
