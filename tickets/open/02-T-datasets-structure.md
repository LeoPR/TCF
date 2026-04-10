---
title: Estrutura de storage — config, pastas git, disco externo
type: task
status: OPEN
priority: 1
parent: 01-M-datasets-setup
---

# Estrutura de Storage

## Objetivo

Criar a arquitetura de 3 camadas descrita em
[docs/architecture/storage.md](../../docs/architecture/storage.md):

- **Camada A (git):** scripts, metadata, amostras pequenas
- **Camada B (disco):** dados raw, SQLite, derivacoes (em `Z:\tcf-data`)
- **Camada C (archive):** LZMA ultra (futuro, nao bloqueante)

## Estrutura no repositorio (em git)

```
TCF/
├── config/
│   ├── storage.json.example   # template em git
│   └── .gitignore             # ignora storage.json real
│
├── datasets/                  # pequenos, em git
│   ├── README.md              # explica estrutura e aponta para Z:
│   ├── canonical/             # so metadata + amostras, NAO dados
│   │   ├── tpch-sf001/
│   │   │   ├── metadata.json
│   │   │   └── README.md
│   │   └── adult-census/
│   │       ├── metadata.json
│   │       └── README.md
│   ├── samples/               # amostras pequenas (<50KB) em git
│   │   ├── tpch-sf001/
│   │   │   └── .gitkeep
│   │   └── adult-census/
│   │       └── .gitkeep
│   ├── quality-reports/       # markdown pequenos em git
│   │   └── .gitkeep
│   ├── questions/             # JSONs pequenos em git
│   │   └── .gitkeep
│   └── poor-reference/        # legacy (retail_sales)
│       └── README.md
│
├── scripts/
│   ├── _paths.py              # resolve storage paths
│   └── .gitkeep
│
└── data-local/                # fallback se usuario nao tem disco extra
    └── .gitkeep
```

## Estrutura no disco externo (Camada B)

**Nao criada pelo ticket** — criada pelos scripts de download.
Apenas documentada aqui como referencia.

```
Z:\tcf-data\        # ou o que o usuario configurar
├── external\       # raw (download nos ticket 04 e 05)
├── interim\        # SQLite (ticket 06)
├── processed\      # derivacoes (ticket 08)
└── archives\       # LZMA (futuro)
```

## Arquivos a criar

### 1. `config/storage.json.example`

```json
{
  "data_root": "Z:/tcf-data",
  "note": "Copie este arquivo como storage.json e ajuste para seu ambiente.",
  "fallback": "Se nao configurar, usa 'data-local' dentro do projeto"
}
```

### 2. `config/.gitignore`

```gitignore
# Config local com caminhos especificos do usuario
storage.json

# Outros configs futuros com secrets/paths locais
*.local.json
.env
```

### 3. `scripts/_paths.py`

```python
"""Resolve storage paths based on config/storage.json (gitignored)."""
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = PROJECT_ROOT / "config" / "storage.json"
_FALLBACK = PROJECT_ROOT / "data-local"


def data_root() -> Path:
    """Returns the configured data root, or falls back to ./data-local/."""
    if _CONFIG.exists():
        cfg = json.loads(_CONFIG.read_text(encoding="utf-8"))
        return Path(cfg["data_root"])
    return _FALLBACK


def external_dir(name: str) -> Path:
    return data_root() / "external" / name


def interim_db(name: str) -> Path:
    return data_root() / "interim" / f"{name}.db"


def processed_dir(name: str, fmt: str) -> Path:
    return data_root() / "processed" / name / fmt


def archive_path(name: str) -> Path:
    return data_root() / "archives" / f"{name}.tar.xz"


def ensure_dirs():
    """Create standard directories if they dont exist."""
    root = data_root()
    for sub in ("external", "interim", "processed", "archives"):
        (root / sub).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Config file:  {_CONFIG} {'(exists)' if _CONFIG.exists() else '(not found, using fallback)'}")
    print(f"Data root:    {data_root()}")
    print(f"External:     {external_dir('example')}")
    print(f"Interim DB:   {interim_db('example')}")
    print(f"Processed:    {processed_dir('example', 'csv')}")
```

### 4. `datasets/README.md`

```markdown
# Datasets — TCF

Datasets canonicos usados nos experimentos.

## Arquitetura

Esta pasta contem:
- **metadata/** dos datasets (em git, pequeno)
- **samples/** de amostra (<50KB em git)
- **quality-reports/** (markdown em git)
- **questions/** com ground truth (JSON em git)

**Dados reais** ficam fora do git, em `Z:\tcf-data\` (ou onde voce configurar
em `config/storage.json`). Ver `docs/architecture/storage.md`.

## Como configurar

```bash
cp config/storage.json.example config/storage.json
# Editar para apontar para seu disco
python scripts/_paths.py  # verifica config
```

## Datasets disponiveis

- `canonical/tpch-sf001/` — TPC-H Scale Factor 0.01 (padrao industria)
- `canonical/adult-census/` — UCI Adult Income (dados reais demograficos)
- `poor-reference/retail-sales-synthetic/` — legacy sintetico (comparacao com literatura antiga)

Ver `docs/datasets/` para manuais completos de cada um.
```

### 5. `data-local/.gitkeep`

Pasta vazia com `.gitkeep`. Serve de fallback se usuario nao criar `config/storage.json`.

### 6. `.gitignore` (adicionar)

```gitignore
# === Datasets ===
# Dados raw grandes ficam em Z: (ou fallback local)
data-local/**/external/
data-local/**/interim/
data-local/**/processed/
data-local/**/archives/

# Dados gerados por scripts em datasets/ (devem ir para data_root, nao aqui)
datasets/canonical/*/[a-z]*.csv
datasets/canonical/*/[a-z]*.tsv
datasets/canonical/*/[a-z]*.db

# Whitelist: metadata, README, samples (explicitamente mantidos)
!datasets/canonical/*/metadata.json
!datasets/canonical/*/README.md
!datasets/samples/
```

## Tarefas

- [ ] Criar `config/.gitignore` e `config/storage.json.example`
- [ ] Criar `scripts/_paths.py` com resolucao de storage
- [ ] Criar estrutura `datasets/canonical/*/` com `.gitkeep` e READMEs
- [ ] Criar `datasets/README.md`
- [ ] Criar `datasets/samples/` vazio com `.gitkeep`
- [ ] Criar `datasets/quality-reports/` vazio com `.gitkeep`
- [ ] Criar `datasets/questions/` vazio com `.gitkeep`
- [ ] Criar `data-local/` com `.gitkeep`
- [ ] Atualizar `.gitignore` raiz com regras de datasets
- [ ] Testar `python scripts/_paths.py` (mostra config atual)
- [ ] Commit de estrutura (sem dados)

## Criterio de conclusao

- `python scripts/_paths.py` imprime caminhos corretos
- Com `config/storage.json` apontando para Z:, aponta para Z:
- Sem config, cai no fallback `data-local/`
- Estrutura no git e consistente com `docs/architecture/storage.md`
- `.gitignore` evita comitar dados brutos mas permite metadata/samples

## NOTA

Este ticket **nao baixa nenhum dado** — so cria a estrutura. Download
vem nos tickets 04 (TPC-H) e 05 (Adult).
